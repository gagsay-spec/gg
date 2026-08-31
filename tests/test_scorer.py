import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scorer import calculate_score
from src.detector import Detection


def test_high_score_with_multiple_detections():
    token = {"price": 1.0, "price_change_percent5m": 50, "price_change_percent1h": 100}
    detections = [
        Detection("PRICE_SURGE", "high", {"change_percent": 50}),
        Detection("VOLUME_EXPLOSION", "high", {"change_percent": 500}),
        Detection("HOLDER_GROWTH", "medium", {"change_percent": 20})
    ]
    score, level, details = calculate_score(token, detections)
    assert score >= 60
    assert level in ["ATTENTION", "STRONG", "EXTREME"]


def test_low_score_with_no_detections():
    token = {"price": 1.0}
    score, level, details = calculate_score(token, [])
    assert score == 0
    assert level == "NORMAL"


def test_score_levels():
    token = {"price": 1.0, "price_change_percent5m": 100, "price_change_percent1h": 200}
    detections = [
        Detection("PRICE_SURGE", "high", {"change_percent": 100}),
        Detection("VOLUME_EXPLOSION", "high", {"change_percent": 800}),
        Detection("SMART_MONEY_BUY", "high", {"buyer_count": 5}),
        Detection("HOLDER_GROWTH", "medium", {"change_percent": 30}),
        Detection("LIQUIDITY_INCREASE", "medium", {"change_percent": 40})
    ]
    score, level, details = calculate_score(token, detections)
    assert score >= 75
    assert level in ["STRONG", "EXTREME"]


if __name__ == "__main__":
    test_high_score_with_multiple_detections()
    test_low_score_with_no_detections()
    test_score_levels()
    print("All scorer tests passed!")
