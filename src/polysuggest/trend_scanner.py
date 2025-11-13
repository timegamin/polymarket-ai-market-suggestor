from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx
from loguru import logger
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .config import get_settings


_analyzer = SentimentIntensityAnalyzer()


@dataclass
class TrendItem:
  source: str
  title: str
  url: Optional[str]
  sentiment: float


class TrendScanner:
  def __init__(self) -> None:
    self.settings = get_settings()
    self.http = httpx.Client(timeout=20)

  def scan_coingecko(self, limit: int = 10) -> List[TrendItem]:
    logger.info("Fetching crypto trends from CoinGecko")
    try:
      resp = self.http.get("https://api.coingecko.com/api/v3/search/trending")
      resp.raise_for_status()
    except httpx.HTTPError as exc:
      logger.warning("CoinGecko request failed: %s", exc)
      return []
    data = resp.json()
    items: List[TrendItem] = []
    for entry in data.get("coins", [])[:limit]:
      item = entry.get("item", {})
      name = item.get("name")
      if not name:
        continue
      score = item.get("score", 0)
      twitter = item.get("twitter_followers", 0) or 0
      sentiment = min(1.0, 0.2 + 0.1 * score + (twitter / 1_000_000))
      items.append(
        TrendItem(
          source="coingecko",
          title=f"{name} ({item.get('symbol', '').upper()}) momentum rising",
          url=f"https://www.coingecko.com/en/coins/{item.get('id')}",
          sentiment=sentiment,
        )
      )
    return items

  def scan_news(self, keywords: Optional[List[str]] = None, limit: int = 20) -> List[TrendItem]:
    if not self.settings.news_api_key:
      logger.warning("NEWS_API_KEY not set, returning empty news trends")
      return []
    keys = keywords or self.settings.default_trend_keywords
    query = " OR ".join(keys)
    logger.info("Fetching news trends for query=%s", query)
    resp = self.http.get(
      "https://newsapi.org/v2/everything",
      params={"q": query, "pageSize": limit, "sortBy": "publishedAt", "apiKey": self.settings.news_api_key},
    )
    resp.raise_for_status()
    data = resp.json()
    items = []
    for article in data.get("articles", []):
      title = article.get("title") or "Untitled"
      sentiment = _analyzer.polarity_scores(title)["compound"]
      items.append(
        TrendItem(
          source="newsapi",
          title=title,
          url=article.get("url"),
          sentiment=sentiment,
        )
      )
    return items

  def scan_twitter(self, keywords: Optional[List[str]] = None, limit: int = 20) -> List[TrendItem]:
    if not self.settings.twitter_bearer_token:
      logger.warning("TWITTER_BEARER_TOKEN not set, returning empty Twitter trends")
      return []
    keys = keywords or self.settings.default_trend_keywords
    query = " OR ".join(keys)
    logger.info("Fetching Twitter trends for query=%s", query)
    resp = self.http.get(
      "https://api.twitter.com/2/tweets/search/recent",
      params={"query": query, "max_results": min(limit, 100), "tweet.fields": "created_at,lang"},
      headers={"Authorization": f"Bearer {self.settings.twitter_bearer_token}"},
    )
    resp.raise_for_status()
    data = resp.json()
    items = []
    for tweet in data.get("data", []):
      text = tweet.get("text", "")
      if not text:
        continue
      sentiment = _analyzer.polarity_scores(text)["compound"]
      items.append(
        TrendItem(
          source="twitter",
          title=text[:200],
          url=f"https://twitter.com/i/web/status/{tweet.get('id')}",
          sentiment=sentiment,
        )
      )
    return items

  def close(self) -> None:
    self.http.close()


__all__ = ["TrendScanner", "TrendItem"]

