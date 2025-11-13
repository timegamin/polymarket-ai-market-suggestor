from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime
from typing import List, Optional, Sequence

from loguru import logger
from rapidfuzz import fuzz

from .ai import SuggestionEngine
from .polymarket_client import Market, PolymarketClient
from .schemas import MarketSnapshot, MarketSuggestion, SuggestionBundle, TrendSnapshot
from .trend_scanner import TrendItem, TrendScanner


def _dedupe_markets(existing: Sequence[Market], suggestions: List[MarketSuggestion]) -> List[MarketSuggestion]:
    filtered: List[MarketSuggestion] = []
    for suggestion in suggestions:
        similarity = max(
            (
                fuzz.token_sort_ratio(suggestion.title, market.question) / 100.0
                for market in existing
            ),
            default=0.0,
        )
        if similarity < 0.75:
            filtered.append(suggestion)
        else:
            logger.info("Dropping suggestion '%s' due to similarity %.2f", suggestion.title, similarity)
    return filtered


def _convert_trends(trends: Sequence[TrendItem]) -> List[TrendSnapshot]:
    return [
        TrendSnapshot(source=item.source, title=item.title, url=item.url, sentiment=item.sentiment)
        for item in trends
    ]


def _convert_markets(markets: Sequence[Market]) -> List[MarketSnapshot]:
    return [
        MarketSnapshot(
            id=market.id,
            question=market.question,
            outcome_type=market.outcome_type,
            url=market.url,
            volume=market.volume or 0,
            end_date=market.end_date,
        )
        for market in markets
    ]


def run_pipeline(
    *,
    topic: str,
    keywords: Optional[List[str]] = None,
    suggestion_count: int = 3,
    include_trending: bool = True,
    include_crypto: bool = True,
) -> SuggestionBundle:
    with ExitStack() as stack:
        client = PolymarketClient()
        stack.callback(client.close)
        scanner = TrendScanner()
        stack.callback(scanner.close)

        markets: List[Market] = []
        if include_trending:
            try:
                markets.extend(client.fetch_trending_markets(limit=20))
            except Exception as exc:
                logger.warning("Failed to fetch trending markets: %s", exc)
        if keywords:
            for keyword in keywords:
                try:
                    markets.extend(client.fetch_markets_by_keyword(keyword, limit=10))
                except Exception as exc:
                    logger.warning("Failed to fetch markets for %s: %s", keyword, exc)
        # dedupe markets by id
        seen = set()
        unique_markets = []
        for market in markets:
            if market.id in seen:
                continue
            seen.add(market.id)
            unique_markets.append(market)

        trends: List[TrendItem] = []
        try:
            trends.extend(scanner.scan_news(keywords=keywords))
        except Exception as exc:
            logger.warning("News scan failed: %s", exc)
        try:
            trends.extend(scanner.scan_twitter(keywords=keywords, limit=15))
        except Exception as exc:
            logger.warning("Twitter scan failed: %s", exc)
        if include_crypto:
            try:
                trends.extend(scanner.scan_coingecko(limit=10))
            except Exception as exc:
                logger.warning("CoinGecko scan failed: %s", exc)

        if not trends:
            logger.warning("No trends found; injecting placeholder trend for topic='%s'", topic)
            trends.append(
                TrendItem(
                    source="manual",
                    title=f"Discussion surge around {topic}",
                    url=None,
                    sentiment=0.1,
                )
            )

        engine = SuggestionEngine()
        raw_suggestions = engine.generate(
            trends=_convert_trends(trends),
            markets=[market.model_dump() for market in unique_markets],
            count=suggestion_count,
        )
        suggestions = _dedupe_markets(unique_markets, raw_suggestions)

        if not suggestions:
            logger.warning("All suggestions filtered out, using fallback ones.")
            suggestions = engine._fallback(_convert_trends(trends), suggestion_count)  # type: ignore[attr-defined]

        bundle = SuggestionBundle(
            generated_at=datetime.utcnow(),
            topic=topic,
            keywords=keywords or [],
            suggestions=suggestions,
            trends=_convert_trends(trends),
            overlapping_markets=_convert_markets(unique_markets[: suggestion_count * 2]),
        )
        return bundle


__all__ = ["run_pipeline"]


