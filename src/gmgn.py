import time
import uuid
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class GMGNClient:
    def __init__(self, api_key: str, base_url: str = "https://openapi.gmgn.ai",
                 timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "X-APIKEY": api_key,
            "Content-Type": "application/json"
        })
        self._request_count = 0
        self._last_request_time = 0

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

    def _request(self, method: str, path: str, params: dict = None,
                 json_body: dict = None) -> Optional[Dict[str, Any]]:
        self._wait_for_rate_limit()

        timestamp = str(int(time.time()))
        client_id = str(uuid.uuid4())

        if params is None:
            params = {}
        params["timestamp"] = timestamp
        params["client_id"] = client_id

        url = f"{self.base_url}{path}"

        for attempt in range(self.max_retries):
            try:
                self._last_request_time = time.time()
                self._request_count += 1

                if method.upper() == "GET":
                    resp = self.session.get(url, params=params, timeout=self.timeout)
                else:
                    resp = self.session.post(url, params=params, json=json_body, timeout=self.timeout)

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("X-RateLimit-Reset", str(time.time() + 5)))
                    wait = max(retry_after - time.time(), 1)
                    logger.warning(f"[RATE_LIMIT] 429 received, waiting {wait:.1f}s")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()

                if data.get("code") != 0:
                    logger.error(f"[API_ERROR] {data.get('message', 'Unknown error')}")
                    return None

                result = data.get("data")
                if isinstance(result, dict) and result.get("code") == 0:
                    result = result.get("data")
                return result

            except requests.exceptions.Timeout:
                logger.warning(f"[TIMEOUT] Attempt {attempt + 1}/{self.max_retries}")
                time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                logger.error(f"[REQUEST_ERROR] {e}")
                time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"[UNEXPECTED_ERROR] {e}")
                return None

        logger.error(f"[FAILED] All {self.max_retries} attempts failed for {path}")
        return None

    def get_trending(self, chain: str, interval: str = "1h", limit: int = 50) -> List[Dict]:
        data = self._request("GET", "/v1/market/rank", params={
            "chain": chain, "interval": interval, "limit": limit,
            "order_by": "volume", "direction": "desc"
        })
        return data.get("rank", []) if data else []

    def get_new_tokens(self, chain: str, limit: int = 50) -> List[Dict]:
        data = self._request("POST", "/v1/trenches", params={"chain": chain}, json_body={
            "version": "v2",
            "new_creation": {"limit": limit},
            "near_completion": {},
            "completed": {}
        })
        if data and "new_creation" in data:
            return data["new_creation"]
        return []

    def get_token_info(self, chain: str, address: str) -> Optional[Dict]:
        return self._request("GET", "/v1/token/info", params={
            "chain": chain, "address": address
        })

    def get_token_holders(self, chain: str, address: str, limit: int = 20) -> List[Dict]:
        data = self._request("GET", "/v1/market/token_top_holders", params={
            "chain": chain, "address": address, "limit": limit
        })
        return data.get("list", []) if data else []

    def get_token_traders(self, chain: str, address: str, limit: int = 20) -> List[Dict]:
        data = self._request("GET", "/v1/market/token_top_traders", params={
            "chain": chain, "address": address, "limit": limit
        })
        return data.get("list", []) if data else []

    def get_signals(self, chain: str, limit: int = 50) -> List[Dict]:
        data = self._request("POST", "/v1/market/token_signal", json_body={
            "chain": chain, "groups": [{"limit": limit}]
        })
        return data if isinstance(data, list) else []

    def get_smart_money(self, chain: str, limit: int = 50) -> List[Dict]:
        data = self._request("GET", "/v1/user/smartmoney", params={
            "chain": chain, "limit": limit
        })
        return data.get("list", []) if data else []

    def get_hot_searches(self, chain: str, limit: int = 50) -> List[Dict]:
        data = self._request("POST", "/v1/market/hot_searches", json_body={
            "params": [{"chain": chain, "limit": limit}]
        })
        return data.get("tokens", []) if data else []

    def get_kline(self, chain: str, address: str, resolution: str = "1h",
                  limit: int = 24) -> List[Dict]:
        data = self._request("GET", "/v1/market/token_kline", params={
            "chain": chain, "address": address, "resolution": resolution
        })
        return data.get("list", []) if data else []

    @property
    def request_count(self) -> int:
        return self._request_count
