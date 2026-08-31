import json
import os
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")

def default_state() -> Dict[str, Any]:
    return {
        "last_seen_tokens": {},
        "token_snapshots": {},
        "alerts": {},
        "last_run": None,
        "suppressed_alerts": []
    }

def load_state() -> Dict[str, Any]:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"[STATE] Failed to load state: {e}")
    return default_state()

def save_state(state: Dict[str, Any]):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state["last_run"] = time.time()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_token_snapshot(state: Dict, address: str) -> Optional[Dict]:
    return state.get("token_snapshots", {}).get(address)

def update_token_snapshot(state: Dict, address: str, data: Dict):
    if "token_snapshots" not in state:
        state["token_snapshots"] = {}
    state["token_snapshots"][address] = {
        "data": data,
        "timestamp": time.time()
    }

def is_alert_in_cooldown(state: Dict, address: str, alert_type: str,
                         cooldown_minutes: int = 30) -> bool:
    alerts = state.get("alerts", {})
    key = f"{address}:{alert_type}"
    if key in alerts:
        last_alert = alerts[key].get("timestamp", 0)
        return (time.time() - last_alert) < (cooldown_minutes * 60)
    return False

def record_alert(state: Dict, address: str, alert_type: str, score: float):
    if "alerts" not in state:
        state["alerts"] = {}
    state["alerts"][f"{address}:{alert_type}"] = {
        "timestamp": time.time(),
        "score": score
    }

def cleanup_old_snapshots(state: Dict, max_age_seconds: int = 3600):
    now = time.time()
    snapshots = state.get("token_snapshots", {})
    to_remove = [addr for addr, snap in snapshots.items()
                 if (now - snap.get("timestamp", 0)) > max_age_seconds]
    for addr in to_remove:
        del snapshots[addr]
