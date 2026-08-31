import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Detection:
    def __init__(self, alert_type: str, severity: str, details: Dict):
        self.alert_type = alert_type
        self.severity = severity
        self.details = details

    def __repr__(self):
        return f"Detection({self.alert_type}, {self.severity})"


def detect_movements(token_info: Dict, prev_snapshot: Optional[Dict],
                     config: Dict) -> List[Detection]:
    detections = []

    if prev_snapshot:
        prev = prev_snapshot.get("data", {})

        price_change = _calc_price_change(token_info, prev)
        if price_change is not None:
            if price_change >= config.get("PRICE_SURGE_5M", 20):
                detections.append(Detection(
                    "PRICE_SURGE", "high",
                    {"change_percent": price_change, "timeframe": "5m"}
                ))
            elif price_change <= config.get("PRICE_DROP_5M", -20):
                detections.append(Detection(
                    "PRICE_DROP", "critical",
                    {"change_percent": price_change, "timeframe": "5m"}
                ))

        volume_change = _calc_volume_change(token_info, prev)
        if volume_change is not None and volume_change >= config.get("VOLUME_SPIKE_PERCENT", 300):
            detections.append(Detection(
                "VOLUME_EXPLOSION", "high",
                {"change_percent": volume_change}
            ))

        holder_change = _calc_holder_change(token_info, prev)
        if holder_change is not None and holder_change >= config.get("HOLDER_GROWTH_PERCENT", 15):
            detections.append(Detection(
                "HOLDER_GROWTH", "medium",
                {"change_percent": holder_change}
            ))

        liquidity_change = _calc_liquidity_change(token_info, prev)
        if liquidity_change is not None:
            threshold = config.get("LIQUIDITY_CHANGE_PERCENT", 30)
            if liquidity_change <= -threshold:
                detections.append(Detection(
                    "LIQUIDITY_DROP", "critical",
                    {"change_percent": liquidity_change}
                ))
            elif liquidity_change >= threshold:
                detections.append(Detection(
                    "LIQUIDITY_INCREASE", "medium",
                    {"change_percent": liquidity_change}
                ))

    if _is_new_token(token_info, config):
        detections.append(Detection("NEW_TOKEN", "info", {
            "symbol": token_info.get("symbol", "unknown"),
            "name": token_info.get("name", "unknown")
        }))

    return detections


def detect_smart_money(token_info: Dict, smart_money_trades: List[Dict],
                       token_address: str) -> Optional[Detection]:
    buyers = [t for t in smart_money_trades
              if t.get("base_token", {}).get("address") == token_address
              and t.get("side") == "buy"]

    if len(buyers) >= 3:
        return Detection("SMART_MONEY_BUY", "high", {
            "buyer_count": len(buyers),
            "total_amount": sum(t.get("amount_usd", 0) for t in buyers)
        })
    return None


def _calc_price_change(current: Dict, previous: Dict) -> Optional[float]:
    curr_price = current.get("price") or current.get("price_usd")
    prev_price = previous.get("price") or previous.get("price_usd")
    if curr_price and prev_price and prev_price > 0:
        return ((curr_price - prev_price) / prev_price) * 100
    return None


def _calc_volume_change(current: Dict, previous: Dict) -> Optional[float]:
    curr_vol = current.get("volume_5m") or current.get("volume")
    prev_vol = previous.get("volume_5m") or previous.get("volume")
    if curr_vol and prev_vol and prev_vol > 0:
        return ((curr_vol - prev_vol) / prev_vol) * 100
    return None


def _calc_holder_change(current: Dict, previous: Dict) -> Optional[float]:
    curr_holders = current.get("holder_count")
    prev_holders = previous.get("holder_count")
    if curr_holders and prev_holders and prev_holders > 0:
        return ((curr_holders - prev_holders) / prev_holders) * 100
    return None


def _calc_liquidity_change(current: Dict, previous: Dict) -> Optional[float]:
    curr_liq = current.get("liquidity")
    prev_liq = previous.get("liquidity")
    if curr_liq and prev_liq and prev_liq > 0:
        return ((curr_liq - prev_liq) / prev_liq) * 100
    return None


def _is_new_token(token_info: Dict, config: Dict) -> bool:
    return token_info.get("is_new", False)
