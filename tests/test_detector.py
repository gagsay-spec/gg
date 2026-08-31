import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.detector import detect_movements, Detection


def test_price_surge_detected():
    token = {"price": 1.0, "price_5m": 0.8, "price_change_percent5m": 25}
    prev = {"data": {"price": 0.8, "price_5m": 0.8}}
    detections = detect_movements(token, prev, {"PRICE_SURGE_5M": 20})
    assert any(d.alert_type == "PRICE_SURGE" for d in detections)


def test_price_no_alert_small_change():
    token = {"price": 1.0, "price_change_percent5m": 5}
    prev = {"data": {"price": 0.95}}
    detections = detect_movements(token, prev, {"PRICE_SURGE_5M": 20})
    assert not any(d.alert_type == "PRICE_SURGE" for d in detections)


def test_volume_explosion_detected():
    token = {"volume": 1000, "volume_5m": 1000}
    prev = {"data": {"volume": 200, "volume_5m": 200}}
    detections = detect_movements(token, prev, {"VOLUME_SPIKE_PERCENT": 300})
    assert any(d.alert_type == "VOLUME_EXPLOSION" for d in detections)


def test_holder_growth_detected():
    token = {"holder_count": 150}
    prev = {"data": {"holder_count": 100}}
    detections = detect_movements(token, prev, {"HOLDER_GROWTH_PERCENT": 15})
    assert any(d.alert_type == "HOLDER_GROWTH" for d in detections)


def test_liquidity_drop_detected():
    token = {"liquidity": 50}
    prev = {"data": {"liquidity": 100}}
    detections = detect_movements(token, prev, {"LIQUIDITY_CHANGE_PERCENT": 30})
    assert any(d.alert_type == "LIQUIDITY_DROP" for d in detections)


if __name__ == "__main__":
    test_price_surge_detected()
    test_price_no_alert_small_change()
    test_volume_explosion_detected()
    test_holder_growth_detected()
    test_liquidity_drop_detected()
    print("All detector tests passed!")
