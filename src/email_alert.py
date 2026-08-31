import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List

logger = logging.getLogger(__name__)


def send_alert(config: Dict, token_info: Dict, score: float, level: str,
               detections: List, gmgn_url: str = None) -> bool:
    if config.get("DRY_RUN"):
        logger.info(f"[DRY RUN] Would send email for {token_info.get('symbol', 'unknown')}")
        _print_dry_run(config, token_info, score, level, detections)
        return True

    if not all([config.get("SMTP_HOST"), config.get("SMTP_USERNAME"),
                config.get("SMTP_PASSWORD"), config.get("ALERT_EMAIL")]):
        logger.error("[EMAIL] SMTP configuration incomplete")
        return False

    try:
        msg = _build_email(config, token_info, score, level, detections, gmgn_url)

        with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"]) as server:
            server.starttls()
            server.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
            server.send_message(msg)

        logger.info(f"[EMAIL] Alert sent for {token_info.get('symbol', 'unknown')}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL] Failed to send: {e}")
        return False


def _build_email(config: Dict, token_info: Dict, score: float, level: str,
                 detections: List, gmgn_url: str = None) -> MIMEMultipart:
    symbol = token_info.get("symbol", "unknown")
    chain = config.get("CHAIN", "sol")

    subject = _build_subject(symbol, score, level, detections)

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = config["SMTP_USERNAME"]
    msg["To"] = config["ALERT_EMAIL"]

    body = _build_body(token_info, score, level, detections, chain, gmgn_url)
    msg.attach(MIMEText(body, "plain"))

    return msg


def _build_subject(symbol: str, score: float, level: str, detections: List) -> str:
    alert_types = [d.alert_type for d in detections]
    primary = alert_types[0] if alert_types else "ALERT"

    icons = {
        "PRICE_SURGE": "📈",
        "PRICE_DROP": "📉",
        "VOLUME_EXPLOSION": "📊",
        "NEW_TOKEN": "🆕",
        "SMART_MONEY_BUY": "🧠",
        "HOLDER_GROWTH": "👥",
        "LIQUIDITY_DROP": "🚨",
        "LIQUIDITY_INCREASE": "💧"
    }

    icon = icons.get(primary, "⚡")
    return f"{icon} MEME ALERT: ${symbol} | Score {score:.0f} | {level}"


def _build_body(token_info: Dict, score: float, level: str,
                detections: List, chain: str, gmgn_url: str = None) -> str:
    symbol = token_info.get("symbol", "unknown")
    name = token_info.get("name", "unknown")
    address = token_info.get("address", "unknown")

    price_data = token_info.get("price", token_info)
    change_5m = price_data.get("price_change_percent5m", "N/A")
    change_1h = price_data.get("price_change_percent1h", "N/A")
    volume = token_info.get("volume", "N/A")
    liquidity = token_info.get("liquidity", "N/A")
    market_cap = token_info.get("market_cap", "N/A")
    holders = token_info.get("holder_count", "N/A")

    reasons = []
    for d in detections:
        icons = {
            "PRICE_SURGE": "📈", "PRICE_DROP": "📉",
            "VOLUME_EXPLOSION": "📊", "NEW_TOKEN": "🆕",
            "SMART_MONEY_BUY": "🧠", "HOLDER_GROWTH": "👥",
            "LIQUIDITY_DROP": "🚨", "LIQUIDITY_INCREASE": "💧"
        }
        icon = icons.get(d.alert_type, "⚡")
        reasons.append(f"{icon} {d.alert_type.replace('_', ' ').title()}")

    vol_str = f"${volume:,.0f}" if isinstance(volume, (int, float)) else str(volume)
    liq_str = f"${liquidity:,.0f}" if isinstance(liquidity, (int, float)) else str(liquidity)
    mc_str = f"${market_cap:,.0f}" if isinstance(market_cap, (int, float)) else str(market_cap)

    body = f"""GMGN MEME COIN ALERT
{'=' * 40}

Token: ${symbol} ({name})
Chain: {chain}
Address: {address}

Movement Score: {score:.0f}/100
Status: {level}

{'─' * 40}

PRICE
  5m Change: {change_5m}%
  1h Change: {change_1h}%

VOLUME
  Current: {vol_str}

LIQUIDITY
  Current: {liq_str}

MARKET CAP
  {mc_str}

HOLDERS
  {holders}

{'─' * 40}

REASONS
{chr(10).join(reasons)}

Detected: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""

    if gmgn_url:
        body += f"\nOpen on GMGN: {gmgn_url}\n"

    body += """
This is an automated monitoring alert.
It is NOT financial advice.
"""
    return body


def _print_dry_run(config: Dict, token_info: Dict, score: float,
                   level: str, detections: List):
    symbol = token_info.get("symbol", "unknown")
    print(f"\n{'=' * 40}")
    print(f"[DRY RUN] Would send email:")
    print(f"  To: {config.get('ALERT_EMAIL', 'not configured')}")
    print(f"  Subject: MEME ALERT: ${symbol} | Score {score:.0f} | {level}")
    print(f"  Detections: {[d.alert_type for d in detections]}")
    print(f"{'=' * 40}\n")
