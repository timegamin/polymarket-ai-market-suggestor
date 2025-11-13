from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class TrendSnapshot(BaseModel):
    source: str
    title: str
    url: Optional[HttpUrl] = None
    sentiment: float = 0.0


class MarketSnapshot(BaseModel):
    id: str
    question: str
    outcome_type: str = "binary"
    url: Optional[HttpUrl] = None
    volume: float = 0.0
    end_date: Optional[str] = None


class MarketSuggestion(BaseModel):
    title: str
    description: str
    yes_outcome: str
    no_outcome: str
    resolution_source: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    tags: List[str] = Field(default_factory=list)
    references: List[HttpUrl] = Field(default_factory=list)


class SuggestionBundle(BaseModel):
    generated_at: datetime
    topic: str
    keywords: List[str]
    suggestions: List[MarketSuggestion]
    trends: List[TrendSnapshot]
    overlapping_markets: List[MarketSnapshot]


