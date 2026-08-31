import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

WEIGHTS = {
    "price_momentum": 20,
    "volume_explosion": 20,
    "smart_money": 20,
    "holder_growth": 10,
    "liquidity": 10,
    "gmgn_signals": 20
}

LEVELS = [
    (85, "EXTREME"),
    (75, "STRONG"),
    (60, "ATTENTION"),
    (40, "WATCH"),
    (0, "NORMAL")
]


def calculate_score(token_info: Dict, detections: List, gmgn_signals: List = None,
                    smart_money_data: Dict = None) -> Tuple[float, str, Dict]:
    scores = {}
    available_weight = 0

    price_score = _score_price_momentum(token_info, detections)
    if price_score is not None:
        scores["price_momentum"] = price_score
        available_weight += WEIGHTS["price_momentum"]

    volume_score = _score_volume(token_info, detections)
    if volume_score is not None:
        scores["volume_explosion"] = volume_score
        available_weight += WEIGHTS["volume_explosion"]

    sm_score = _score_smart_money(detections, smart_money_data)
    if sm_score is not None:
        scores["smart_money"] = sm_score
        available_weight += WEIGHTS["smart_money"]

    holder_score = _score_holder_growth(detections)
    if holder_score is not None:
        scores["holder_growth"] = holder_score
        available_weight += WEIGHTS["holder_growth"]

    liq_score = _score_liquidity(detections)
    if liq_score is not None:
        scores["liquidity"] = liq_score
        available_weight += WEIGHTS["liquidity"]

    signal_score = _score_gmgn_signals(gmgn_signals)
    if signal_score is not None:
        scores["gmgn_signals"] = signal_score
        available_weight += WEIGHTS["gmgn_signals"]

    if available_weight == 0:
        return 0.0, "NORMAL", scores

    raw_total = sum(scores.values())
    final_score = min(100, max(0, (raw_total / available_weight) * 100))

    level = "NORMAL"
    for threshold, label in LEVELS:
        if final_score >= threshold:
            level = label
            break

    return final_score, level, scores


def _to_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _score_price_momentum(token_info: Dict, detections: List) -> Optional[float]:
    price_data = token_info.get("price", token_info)
    if not isinstance(price_data, dict):
        price_data = token_info
    change_5m = _to_float(price_data.get("price_change_percent5m") or price_data.get("price_5m"))
    change_1h = _to_float(price_data.get("price_change_percent1h") or price_data.get("price_1h"))

    score = 0
    if change_5m is not None:
        if change_5m >= 50:
            score += 10
        elif change_5m >= 20:
            score += 7
        elif change_5m >= 10:
            score += 4

    if change_1h is not None:
        if change_1h >= 100:
            score += 10
        elif change_1h >= 50:
            score += 7
        elif change_1h >= 20:
            score += 4

    for d in detections:
        if d.alert_type == "PRICE_SURGE":
            score = min(20, score + 5)

    return score if score > 0 else None


def _score_volume(token_info: Dict, detections: List) -> Optional[float]:
    for d in detections:
        if d.alert_type == "VOLUME_EXPLOSION":
            pct = d.details.get("change_percent", 0)
            if pct >= 500:
                return 20
            elif pct >= 300:
                return 15
            elif pct >= 200:
                return 10
    return None


def _score_smart_money(detections: List, smart_money_data: Dict = None) -> Optional[float]:
    for d in detections:
        if d.alert_type == "SMART_MONEY_BUY":
            count = d.details.get("buyer_count", 0)
            if count >= 5:
                return 20
            elif count >= 3:
                return 14
    if smart_money_data:
        sm_count = smart_money_data.get("smart_degen_count", 0)
        if sm_count >= 10:
            return 15
        elif sm_count >= 5:
            return 10
    return None


def _score_holder_growth(detections: List) -> Optional[float]:
    for d in detections:
        if d.alert_type == "HOLDER_GROWTH":
            pct = d.details.get("change_percent", 0)
            if pct >= 30:
                return 10
            elif pct >= 15:
                return 7
    return None


def _score_liquidity(detections: List) -> Optional[float]:
    for d in detections:
        if d.alert_type == "LIQUIDITY_INCREASE":
            return 8
        elif d.alert_type == "LIQUIDITY_DROP":
            return 10
    return None


def _score_gmgn_signals(gmgn_signals: List = None) -> Optional[float]:
    if not gmgn_signals:
        return None
    score = 0
    for sig in gmgn_signals:
        sig_type = sig.get("signal_type", "")
        if "smart" in sig_type.lower() or "degen" in sig_type.lower():
            score += 8
        elif "buy" in sig_type.lower():
            score += 5
        elif "large" in sig_type.lower():
            score += 5
    return min(20, score) if score > 0 else None
