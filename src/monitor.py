import time
import logging
import datetime
from typing import Dict, List

from .config import (GMGN_API_KEY, GMGN_BASE_URL, CHAINS, MAX_TOKEN_AGE_DAYS, PRICE_SURGE_5M,
                     PRICE_DROP_5M, VOLUME_SPIKE_PERCENT, HOLDER_GROWTH_PERCENT,
                     LIQUIDITY_CHANGE_PERCENT, MIN_ALERT_SCORE, ALERT_COOLDOWN_MINUTES,
                     MAX_EMAILS_PER_RUN, SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
                     SMTP_PASSWORD, ALERT_EMAIL, DRY_RUN, API_TIMEOUT, API_MAX_RETRIES)
from .gmgn import GMGNClient
from .state import (load_state, save_state, get_token_snapshot, update_token_snapshot,
                    is_alert_in_cooldown, record_alert, cleanup_old_snapshots)
from .detector import detect_movements, detect_smart_money
from .scorer import calculate_score
from .email_alert import send_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_monitor():
    print("=" * 50)
    print("GMGN MEME MONITOR — MULTI-CHAIN")
    print("=" * 50)
    print(f"Chains: {', '.join(CHAINS)}")
    print(f"Max Token Age: {MAX_TOKEN_AGE_DAYS} days")
    print(f"Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Min Score: {MIN_ALERT_SCORE}")
    print(f"Dry Run: {DRY_RUN}")
    print()

    if not GMGN_API_KEY:
        logger.error("[ERROR] GMGN_API_KEY is not configured.")
        logger.error("Please add it under: GitHub Repository → Settings → Secrets and variables → Actions")
        return

    client = GMGNClient(GMGN_API_KEY, GMGN_BASE_URL, API_TIMEOUT, API_MAX_RETRIES)
    state = load_state()

    total_new = 0
    total_trending = 0
    total_candidates = 0
    total_alerts = 0
    total_emails = 0

    for chain in CHAINS:
        chain = chain.strip()
        if not chain:
            continue

        print(f"\n{'─' * 50}")
        print(f"  CHAIN: {chain.upper()}")
        print(f"{'─' * 50}")

        new_tokens = []
        trending = []
        signals = []
        smart_money = []

        try:
            logger.info(f"[{chain.upper()}] Fetching trending tokens (max {MAX_TOKEN_AGE_DAYS}d old)...")
            max_created = f"{MAX_TOKEN_AGE_DAYS}d"
            trending = client.get_trending(chain, "1h", 50, max_created=max_created)
            trending = [t for t in trending if _is_token_fresh(t, MAX_TOKEN_AGE_DAYS)]
            logger.info(f"[{chain.upper()}] Trending: {len(trending)} tokens")
        except Exception as e:
            logger.error(f"[{chain.upper()}] Failed to fetch trending: {e}")

        try:
            logger.info(f"[{chain.upper()}] Fetching new tokens...")
            new_tokens = client.get_new_tokens(chain, 50)
            logger.info(f"[{chain.upper()}] New tokens: {len(new_tokens)}")
        except Exception as e:
            logger.error(f"[{chain.upper()}] Failed to fetch new tokens: {e}")

        try:
            logger.info(f"[{chain.upper()}] Fetching signals...")
            signals = client.get_signals(chain, 50)
            logger.info(f"[{chain.upper()}] Signals: {len(signals)}")
        except Exception as e:
            logger.error(f"[{chain.upper()}] Failed to fetch signals: {e}")

        try:
            logger.info(f"[{chain.upper()}] Fetching smart money...")
            smart_money = client.get_smart_money(chain, 50)
            logger.info(f"[{chain.upper()}] Smart money trades: {len(smart_money)}")
        except Exception as e:
            logger.error(f"[{chain.upper()}] Failed to fetch smart money: {e}")

        candidates = _build_candidate_list(new_tokens, trending, signals, smart_money)
        logger.info(f"[{chain.upper()}] Candidates: {len(candidates)}")

        chain_alerts = []
        chain_emails = 0

        for token in candidates[:30]:
            address = token.get("address")
            if not address:
                continue

            try:
                prev_snapshot = get_token_snapshot(state, f"{chain}:{address}")
                token_info = client.get_token_info(chain, address) or token

                detections = detect_movements(token_info, prev_snapshot, {
                    "PRICE_SURGE_5M": PRICE_SURGE_5M,
                    "PRICE_DROP_5M": PRICE_DROP_5M,
                    "VOLUME_SPIKE_PERCENT": VOLUME_SPIKE_PERCENT,
                    "HOLDER_GROWTH_PERCENT": HOLDER_GROWTH_PERCENT,
                    "LIQUIDITY_CHANGE_PERCENT": LIQUIDITY_CHANGE_PERCENT
                })

                token_smart_money = [t for t in smart_money
                                     if t.get("base_token", {}).get("address") == address]
                sm_detection = detect_smart_money(token_info, token_smart_money, address)
                if sm_detection:
                    detections.append(sm_detection)

                token_signals = [s for s in signals
                                if isinstance(s, dict) and s.get("token_address") == address]

                score, level, score_details = calculate_score(
                    token_info, detections, token_signals,
                    {"smart_degen_count": token.get("smart_degen_count", 0)}
                )

                update_token_snapshot(state, f"{chain}:{address}", token_info)

                if score >= MIN_ALERT_SCORE or any(d.severity == "critical" for d in detections):
                    if not is_alert_in_cooldown(state, f"{chain}:{address}", "MAIN_ALERT", ALERT_COOLDOWN_MINUTES):
                        chain_alerts.append({
                            "token": token_info,
                            "score": score,
                            "level": level,
                            "detections": detections,
                            "chain": chain
                        })

            except Exception as e:
                logger.error(f"[{chain.upper()}] Failed to process token {address}: {e}")
                continue

        chain_alerts.sort(key=lambda x: x["score"], reverse=True)

        for alert in chain_alerts[:MAX_EMAILS_PER_RUN]:
            symbol = alert["token"].get("symbol", "unknown")
            score = alert["score"]
            level = alert["level"]
            detections = alert["detections"]
            chain = alert["chain"]

            logger.info(f"[ALERT] [{chain.upper()}] ${symbol} Score={score:.0f} Level={level}")

            gmgn_url = f"https://gmgn.ai/{chain}/token/{alert['token'].get('address', '')}"

            success = send_alert({
                "DRY_RUN": DRY_RUN,
                "SMTP_HOST": SMTP_HOST,
                "SMTP_PORT": SMTP_PORT,
                "SMTP_USERNAME": SMTP_USERNAME,
                "SMTP_PASSWORD": SMTP_PASSWORD,
                "ALERT_EMAIL": ALERT_EMAIL,
                "CHAIN": chain
            }, alert["token"], score, level, detections, gmgn_url)

            if success:
                chain_emails += 1
                record_alert(state, f"{chain}:{alert['token'].get('address', '')}", "MAIN_ALERT", score)

        total_new += len(new_tokens)
        total_trending += len(trending)
        total_candidates += len(candidates)
        total_alerts += len(chain_alerts)
        total_emails += chain_emails

        print(f"  [{chain.upper()}] New: {len(new_tokens)} | Trending: {len(trending)} | "
              f"Candidates: {len(candidates)} | Alerts: {len(chain_alerts)} | Emails: {chain_emails}")

    cleanup_old_snapshots(state)
    save_state(state)

    print()
    print("=" * 50)
    print("TOTAL SUMMARY")
    print("=" * 50)
    print(f"Chains: {', '.join(CHAINS)}")
    print(f"New tokens: {total_new}")
    print(f"Trending: {total_trending}")
    print(f"Candidates: {total_candidates}")
    print(f"Alerts: {total_alerts}")
    print(f"Emails sent: {total_emails}")
    print(f"API requests: {client.request_count}")
    print("=" * 50)


def _build_candidate_list(new_tokens: List, trending: List,
                          signals: List, smart_money: List) -> List[Dict]:
    seen = set()
    candidates = []

    for token in trending:
        addr = token.get("address")
        if addr and addr not in seen:
            seen.add(addr)
            candidates.append(token)

    for token in new_tokens:
        addr = token.get("address")
        if addr and addr not in seen:
            token["is_new"] = True
            seen.add(addr)
            candidates.append(token)

    for signal in signals:
        if isinstance(signal, dict):
            addr = signal.get("token_address") or signal.get("address")
            if addr and addr not in seen:
                seen.add(addr)
                candidates.append(signal)

    return candidates


def _is_token_fresh(token: Dict, max_age_days: int) -> bool:
    """Check if token was created within max_age_days."""
    creation_ts = token.get("creation_timestamp") or token.get("open_timestamp")
    if not creation_ts:
        return False
    try:
        creation_ts = int(creation_ts)
    except (ValueError, TypeError):
        return False
    now = int(time.time())
    age_seconds = now - creation_ts
    return age_seconds <= (max_age_days * 86400)
