from __future__ import annotations

from datetime import datetime
from typing import Any, List

from .schemas import MarketSuggestion, SuggestionBundle


def bundle_to_markdown(bundle: SuggestionBundle) -> str:
    lines = [
        f"# PolySuggest AI Report — {bundle.topic}",
        "",
        f"Generated at: {bundle.generated_at.isoformat()}",
        f"Keywords: {', '.join(bundle.keywords) if bundle.keywords else 'auto'}",
        "",
        "## Suggestions",
        "",
    ]
    for suggestion in bundle.suggestions:
        lines.extend(
            [
                f"### {suggestion.title}",
                f"- Confidence: {suggestion.confidence:.2f}",
                f"- Resolution Source: {suggestion.resolution_source}",
                f"- Tags: {', '.join(suggestion.tags)}",
                f"- References: {', '.join(str(ref) for ref in suggestion.references) or 'n/a'}",
                "",
                f"**Description:** {suggestion.description}",
                "",
                f"**YES Outcome:** {suggestion.yes_outcome}",
                "",
                f"**NO Outcome:** {suggestion.no_outcome}",
                "",
                f"**Rationale:** {suggestion.rationale}",
                "",
            ]
        )

    lines.extend(["## Trend Signals", ""])
    for trend in bundle.trends:
        url = f" ({trend.url})" if trend.url else ""
        lines.append(f"- **{trend.source}** {trend.title}{url} — sentiment {trend.sentiment:.2f}")

    lines.extend(["", "## Overlapping Polymarket Markets", ""])
    if not bundle.overlapping_markets:
        lines.append("- None found.")
    else:
        for market in bundle.overlapping_markets:
            url = f" ({market.url})" if market.url else ""
            lines.append(
                f"- {market.question}{url} — volume {market.volume:.2f} (closes {market.end_date or 'tbd'})"
            )

    return "\n".join(lines) + "\n"


def bundle_to_summary_row(name: str, raw: dict[str, Any]) -> List[str]:
    bundle = SuggestionBundle.model_validate(raw)
    best: MarketSuggestion | None = max(bundle.suggestions, key=lambda s: s.confidence, default=None)
    return [
        name,
        bundle.topic,
        bundle.generated_at.strftime("%Y-%m-%d %H:%M"),
        best.title if best else "n/a",
        f"{best.confidence:.2f}" if best else "0.00",
        ", ".join(best.tags) if best else "",
    ]


__all__ = ["bundle_to_markdown", "bundle_to_summary_row"]


