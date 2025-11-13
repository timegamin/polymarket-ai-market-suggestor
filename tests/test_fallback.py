from datetime import datetime

from polysuggest.ai import SuggestionEngine
from polysuggest.reporting import bundle_to_markdown
from polysuggest.schemas import MarketSuggestion, SuggestionBundle, TrendSnapshot


def test_fallback_generates_expected_count() -> None:
    engine = SuggestionEngine()
    trends = [
        TrendSnapshot(source="test", title="AI regulators approve new framework", sentiment=0.2),
        TrendSnapshot(source="test", title="Bitcoin halving schedule update", sentiment=0.5),
    ]
    result = engine._fallback(trends, count=3)  # type: ignore[attr-defined]
    assert len(result) == 3
    assert all(isinstance(item, MarketSuggestion) for item in result)


def test_bundle_markdown_generation_roundtrip() -> None:
    suggestions = [
        MarketSuggestion(
            title="Will test event occur?",
            description="desc",
            yes_outcome="yes",
            no_outcome="no",
            resolution_source="source",
            confidence=0.5,
            rationale="rationale",
            tags=["tag"],
            references=[],
        )
    ]
    bundle = SuggestionBundle(
        generated_at=datetime.utcnow(),
        topic="unit-test",
        keywords=["test"],
        suggestions=suggestions,
        trends=[],
        overlapping_markets=[],
    )
    md = bundle_to_markdown(bundle)
    assert "PolySuggest AI Report" in md


