import httpx
import logging
from typing import List, Dict, Optional
import os

logger = logging.getLogger("MT5Client")

class MT5Client:
    def __init__(self):
        self.base_url = os.getenv("MT5_BRIDGE_URL", "http://host.docker.internal:5000")
        logger.info(f"MT5 Client inicializado para o bridge em: {self.base_url}")

    async def _request(self, method: str, endpoint: str, **kwargs):
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.request(method, f"{self.base_url}{endpoint}", **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Erro na requisiA?A?o ao MT5 Bridge ({method} {endpoint}): {e}")
                return None

    async def health_check(self) -> bool:
        res = await self._request("GET", "/health")
        return res.get("mt5_connected", False) if res else False

    async def get_rates(self, symbol: str, timeframe: str = "M5", count: int = 100) -> List[Dict]:
        res = await self._request("GET", f"/rates/{symbol}", params={"timeframe": timeframe, "count": count})
        return res if res else []

    async def get_tick(self, symbol: str) -> Optional[Dict]:
        return await self._request("GET", f"/tick/{symbol}")

    async def place_order(self, symbol: str, action: str, volume: float, sl: float = None, tp: float = None, magic: int = 0, comment: str = "") -> Optional[Dict]:
        payload = {
            "symbol": symbol,
            "action": action, # "buy" or "sell"
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "magic": magic,
            "comment": comment
        }
        return await self._request("POST", "/order", json=payload)

    async def get_positions(self) -> List[Dict]:
        res = await self._request("GET", "/positions")
        return res if res else []

    async def close_position(self, ticket: int) -> bool:
        res = await self._request("DELETE", f"/position/{ticket}")
        return res.get("status") == "closed" if res else False

# InstA?ncia Singleton
mt5_client = MT5Client()
