from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel, HttpUrl

from .config import get_settings


class Market(BaseModel):
  id: str
  question: str
  outcome_type: str
  start_date: Optional[str] = None
  end_date: Optional[str] = None
  volume: Optional[float] = None
  url: Optional[HttpUrl] = None


class PolymarketClient:
  def __init__(self, timeout: int = 15) -> None:
    self.settings = get_settings()
    self.http = httpx.Client(base_url=self.settings.polymarket_api_base, timeout=timeout)

  def fetch_trending_markets(self, limit: int = 20) -> List[Market]:
    logger.debug("Fetching trending markets from Polymarket...")
    resp = self.http.get("/markets/trending", params={"limit": limit})
    resp.raise_for_status()
    data: List[Dict[str, Any]] = resp.json()
    return [Market(**self._map_market_fields(item)) for item in data]

  def fetch_markets_by_keyword(self, keyword: str, limit: int = 20) -> List[Market]:
    logger.debug("Searching markets with keyword=%s", keyword)
    resp = self.http.get("/markets", params={"search": keyword, "limit": limit})
    resp.raise_for_status()
    results: List[Dict[str, Any]] = resp.json().get("data", [])
    return [Market(**self._map_market_fields(item)) for item in results]

  def _map_market_fields(self, raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
      "id": raw.get("id") or raw.get("_id", ""),
      "question": raw.get("question") or raw.get("title") or "Untitled market",
      "outcome_type": raw.get("outcomeType") or raw.get("type") or "binary",
      "start_date": raw.get("startDate") or raw.get("createdAt"),
      "end_date": raw.get("endDate"),
      "volume": float(raw.get("volume24h", raw.get("volume", 0)) or 0),
      "url": raw.get("url") or raw.get("slug"),
    }

  def close(self) -> None:
    self.http.close()


__all__ = ["PolymarketClient", "Market"]

