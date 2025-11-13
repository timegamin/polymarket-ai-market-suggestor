from __future__ import annotations

from typing import Iterable, List, Sequence

from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import TypeAdapter

from .config import get_settings
from .schemas import MarketSuggestion, TrendSnapshot

_PROMPT = ChatPromptTemplate.from_template(
    """
You are PolySuggest, an expert analyst for Polymarket prediction markets.
Use the provided trend signals and existing market summaries to recommend new YES/NO markets that do not already exist.

Guidelines:
- Markets must be clearly resolvable with public data (news, official releases, on-chain metrics).
- Provide a short description, YES and NO outcome phrasing, and a credible resolution source.
- Include 3-5 short tags (kebab-case).
- Confidence is from 0 to 1 representing expected edge/interest.
- Reference relevant URLs from the inputs when possible.

Respond in valid JSON array format following the schema:
[
  {{
    "title": "...",
    "description": "...",
    "yes_outcome": "...",
    "no_outcome": "...",
    "resolution_source": "...",
    "confidence": 0.67,
    "rationale": "...",
    "tags": ["tag-one","tag-two"],
    "references": ["https://..."]
  }}
]

Context:
Trends:
{trend_section}

Existing markets (may be empty):
{market_section}

Requested number of ideas: {count}
"""
)


class SuggestionEngine:
    def __init__(self, temperature: float = 0.3) -> None:
        self.settings = get_settings()
        self._llm: ChatOpenAI | None = None
        if self.settings.openai_api_key:
            self._llm = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                model_name=self.settings.model,
                temperature=temperature,
            )

    def _format_trends(self, trends: Sequence[TrendSnapshot]) -> str:
        if not trends:
            return "No recent trend data available."
        lines: List[str] = []
        for item in trends:
            ref = f" ({item.url})" if item.url else ""
            lines.append(f"- [{item.source}] {item.title}{ref} (sentiment={item.sentiment:.2f})")
        return "\n".join(lines)

    def _format_markets(self, markets: Sequence[dict]) -> str:
        if not markets:
            return "No overlapping markets detected."
        return "\n".join(
            f"- {m['question']} (volume={m.get('volume', 0):.2f}, url={m.get('url','n/a')})"
            for m in markets
        )

    def _call_llm(self, messages: List[BaseMessage]) -> str:
        if not self._llm:
            raise RuntimeError("OPENAI_API_KEY not set; cannot call LLM")
        response = self._llm(messages)
        return response.content or "[]"

    def generate(
        self,
        *,
        trends: Sequence[TrendSnapshot],
        markets: Sequence[dict],
        count: int = 3,
    ) -> List[MarketSuggestion]:
        trend_section = self._format_trends(trends)
        market_section = self._format_markets(markets)
        prompt = _PROMPT.format_messages(
            trend_section=trend_section, market_section=market_section, count=count
        )

        raw_output: str
        try:
            raw_output = self._call_llm(prompt)
        except Exception as exc:
            logger.warning("Falling back to heuristic generator: %s", exc)
            return self._fallback(trends, count)

        adapter = TypeAdapter(List[MarketSuggestion])
        try:
            parsed = adapter.validate_json(raw_output)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Parsing error (%s). Falling back to deterministic generator.", exc)
            return self._fallback(trends, count)
        return parsed

    def _fallback(self, trends: Iterable[TrendSnapshot], count: int) -> List[MarketSuggestion]:
        picks = list(trends)[:count]
        results: List[MarketSuggestion] = []
        for idx, trend in enumerate(picks, start=1):
            title = trend.title
            results.append(
                MarketSuggestion(
                    title=f"Will {title[:70]} become a top Polymarket market?",
                    description=f"LLM offline fallback based on trend: {title}",
                    yes_outcome=f"Yes – the scenario '{title}' is confirmed by official sources.",
                    no_outcome=f"No – the scenario '{title}' fails or is not confirmed.",
                    resolution_source="Use reputable news outlets matching the trend reference.",
                    confidence=max(0.1, 0.5 + trend.sentiment / 2),
                    rationale="Generated via deterministic fallback when LLM unavailable.",
                    tags=["ai-generated", trend.source, "fallback"],
                    references=[trend.url] if trend.url else [],
                )
            )
        while len(results) < count:
            results.append(
                MarketSuggestion(
                    title=f"Untitled Opportunity #{len(results)+1}",
                    description="Placeholder suggestion due to limited context.",
                    yes_outcome="Yes – event occurs.",
                    no_outcome="No – event does not occur.",
                    resolution_source="Trusted news source or official dataset.",
                    confidence=0.3,
                    rationale="Fallback filler suggestion.",
                    tags=["placeholder"],
                    references=[],
                )
            )
        return results[:count]


__all__ = ["SuggestionEngine"]


