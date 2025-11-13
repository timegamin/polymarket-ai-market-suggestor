import os
from datetime import datetime
from pathlib import Path

import pytest

from polysuggest import config
from polysuggest.analytics import generate_insights
from polysuggest.schemas import MarketSuggestion, SuggestionBundle, TrendSnapshot
from polysuggest.storage import BundleStore


def build_bundle(topic: str) -> SuggestionBundle:
    suggestions = [
        MarketSuggestion(
            title="Will unit tests pass?",
            description="desc",
            yes_outcome="Yes",
            no_outcome="No",
            resolution_source="CI pipeline",
            confidence=0.8,
            rationale="Testing fallback",
            tags=["tests", "ci"],
            references=[],
        ),
        MarketSuggestion(
            title="Will coverage exceed 70%?",
            description="desc",
            yes_outcome="Yes",
            no_outcome="No",
            resolution_source="Coverage report",
            confidence=0.6,
            rationale="Quality gate",
            tags=["tests"],
            references=[],
        ),
    ]
    trends = [
        TrendSnapshot(source="newsapi", title="Testing best practices", sentiment=0.2),
        TrendSnapshot(source="coingecko", title="CI token surges", sentiment=0.4),
    ]
    return SuggestionBundle(
        generated_at=datetime.utcnow(),
        topic=topic,
        keywords=["tests"],
        suggestions=suggestions,
        trends=trends,
        overlapping_markets=[],
    )


def test_bundle_store_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLYSUGGEST_DATA_DIR", str(tmp_path))
    config.get_settings.cache_clear()

    store = BundleStore()
    run_id = store.persist(build_bundle("unit-test"))
    assert run_id == 1

    history = store.history()
    assert len(history) == 1
    record = history[0]
    assert record.topic == "unit-test"
    assert abs(record.avg_confidence - 0.7) < 1e-6

    fetched = store.get(run_id)
    assert fetched.top_title == "Will unit tests pass?"
    assert fetched.tags == ["ci", "tests"] or fetched.tags == ["tests", "ci"]

    insights = generate_insights(history)
    assert insights["total_runs"] == 1
    assert insights["unique_topics"] == 1
    assert pytest.approx(insights["avg_confidence"], rel=1e-2) == 0.7


