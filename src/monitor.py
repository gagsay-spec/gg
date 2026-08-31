import time
import logging
import datetime
from typing import Dict, List

from .config import (GMGN_API_KEY, GMGN_BASE_URL, CHAIN, PRICE_SURGE_5M,
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
    print("GMGN MEME MONITOR")
    print("=" * 50)
    print(f"Chain: {CHAIN}")
    print(f"Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Dry Run: {DRY_RUN}")
    print()

    if not GMGN_API_KEY:
        logger.error("[ERROR] GMGN_API_KEY is not configured.")
        logger.error("Please add it under: GitHub Repository → Settings → Secrets and variables → Actions")
        return

    client = GMGNClient(GMGN_API_KEY, GMGN_BASE_URL, API_TIMEOUT, API_MAX_RETRIES)
    state = load_state()

    new_tokens = []
    trending = []
    signals = []
    smart_money = []

    try:
        logger.info("[INFO] Fetching trending tokens...")
        trending = client.get_trending(CHAIN, "1h", 50)
        logger.info(f"[INFO] Trending: {len(trending)} tokens")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch trending: {e}")

    try:
        logger.info("[INFO] Fetching new tokens...")
        new_tokens = client.get_new_tokens(CHAIN, 50)
        logger.info(f"[INFO] New tokens: {len(new_tokens)}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch new tokens: {e}")

    try:
        logger.info("[INFO] Fetching signals...")
        signals = client.get_signals(CHAIN, 50)
        logger.info(f"[INFO] Signals: {len(signals)}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch signals: {e}")

    try:
        logger.info("[INFO] Fetching smart money...")
        smart_money = client.get_smart_money(CHAIN, 50)
        logger.info(f"[INFO] Smart money trades: {len(smart_money)}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch smart money: {e}")

    candidates = _build_candidate_list(new_tokens, trending, signals, smart_money)
    logger.info(f"[INFO] Candidates: {len(candidates)}")

    alerts = []
    emails_sent = 0

    for token in candidates[:30]:
        address = token.get("address")
        if not address:
            continue

        try:
            prev_snapshot = get_token_snapshot(state, address)
            token_info = client.get_token_info(CHAIN, address) or token

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

            update_token_snapshot(state, address, token_info)

            if score >= MIN_ALERT_SCORE or any(d.severity == "critical" for d in detections):
                if not is_alert_in_cooldown(state, address, "MAIN_ALERT", ALERT_COOLDOWN_MINUTES):
                    alerts.append({
                        "token": token_info,
                        "score": score,
                        "level": level,
                        "detections": detections
                    })

        except Exception as e:
            logger.error(f"[ERROR] Failed to process token {address}: {e}")
            continue

    alerts.sort(key=lambda x: x["score"], reverse=True)

    for alert in alerts[:MAX_EMAILS_PER_RUN]:
        symbol = alert["token"].get("symbol", "unknown")
        score = alert["score"]
        level = alert["level"]
        detections = alert["detections"]

        logger.info(f"[ALERT] ${symbol} Score={score:.0f} Level={level}")

        gmgn_url = f"https://gmgn.ai/{CHAIN}/token/{alert['token'].get('address', '')}"

        success = send_alert({
            "DRY_RUN": DRY_RUN,
            "SMTP_HOST": SMTP_HOST,
            "SMTP_PORT": SMTP_PORT,
            "SMTP_USERNAME": SMTP_USERNAME,
            "SMTP_PASSWORD": SMTP_PASSWORD,
            "ALERT_EMAIL": ALERT_EMAIL,
            "CHAIN": CHAIN
        }, alert["token"], score, level, detections, gmgn_url)

        if success:
            emails_sent += 1
            record_alert(state, alert["token"].get("address", ""), "MAIN_ALERT", score)

    cleanup_old_snapshots(state)
    save_state(state)

    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"New tokens: {len(new_tokens)}")
    print(f"Trending: {len(trending)}")
    print(f"Candidates: {len(candidates)}")
    print(f"Alerts: {len(alerts)}")
    print(f"Emails sent: {emails_sent}")
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
