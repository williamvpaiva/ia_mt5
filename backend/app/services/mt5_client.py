from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..core.config import settings


logger = logging.getLogger("MT5Client")


class MT5Client:
    def __init__(self):
        self.base_url = settings.MT5_BRIDGE_URL.rstrip("/")
        self.timeout = settings.MT5_BRIDGE_TIMEOUT
        logger.info("MT5 client initialized for bridge at %s", self.base_url)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout, base_url=self.base_url) as client:
            try:
                response = await client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                if response.content:
                    return response.json()
                return {}
            except httpx.HTTPStatusError as exc:
                body = exc.response.text if exc.response is not None else ""
                logger.error(
                    "MT5 Bridge HTTP error (%s %s): %s %s",
                    method,
                    endpoint,
                    exc.response.status_code if exc.response is not None else "unknown",
                    body,
                )
                return None
            except httpx.HTTPError as exc:
                logger.error("MT5 Bridge request failed (%s %s): %s", method, endpoint, exc)
                return None

    async def health_check(self) -> bool:
        res = await self._request("GET", "/health")
        return bool(res and res.get("mt5_connected"))

    async def get_status(self) -> Optional[Dict[str, Any]]:
        return await self._request("GET", "/status")

    async def get_account(self) -> Optional[Dict[str, Any]]:
        return await self._request("GET", "/account")

    async def list_symbols(self, prefix: Optional[str] = None, limit: int = 200, visible_only: bool = False) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit, "visible_only": visible_only}
        if prefix:
            params["prefix"] = prefix
        res = await self._request("GET", "/symbols", params=params)
        return res if isinstance(res, list) else []

    async def resolve_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        return await self._request("GET", f"/resolve/{symbol}")

    async def get_rates(self, symbol: str, timeframe: str = "M5", count: int = 100) -> List[Dict[str, Any]]:
        res = await self._request("GET", f"/rates/{symbol}", params={"timeframe": timeframe, "count": count})
        return res if isinstance(res, list) else []

    async def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        return await self._request("GET", f"/tick/{symbol}")

    async def get_history_deals(
        self,
        from_date: datetime,
        to_date: datetime,
        magic: Optional[int] = None,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }
        if magic is not None:
            params["magic"] = magic
        if symbol:
            params["symbol"] = symbol
        res = await self._request("GET", "/history/deals", params=params)
        return res if isinstance(res, list) else []

    async def place_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        sl: float = None,
        tp: float = None,
        magic: int = 0,
        comment: str = "",
        order_type: str = "market",
        price: float = None,
        deviation: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "symbol": symbol,
            "action": action,
            "type": order_type,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "magic": magic,
            "comment": comment,
        }
        if price is not None:
            payload["price"] = price
        if deviation is not None:
            payload["deviation"] = int(deviation)
        return await self._request("POST", "/order", json=payload)

    async def get_positions(self, magic: Optional[int] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if magic is not None:
            params["magic"] = magic
        if symbol:
            params["symbol"] = symbol
        res = await self._request("GET", "/positions", params=params)
        return res if isinstance(res, list) else []

    async def close_position(self, ticket: int) -> bool:
        res = await self._request("DELETE", f"/position/{ticket}")
        return bool(res and res.get("status") == "closed")

    async def modify_position(self, ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> bool:
        payload: Dict[str, Any] = {}
        if sl is not None:
            payload["sl"] = sl
        if tp is not None:
            payload["tp"] = tp
        res = await self._request("PATCH", f"/position/{ticket}", json=payload)
        return bool(res and res.get("status") == "modified")


mt5_client = MT5Client()
