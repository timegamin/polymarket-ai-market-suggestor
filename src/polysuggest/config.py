from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
  openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
  polymarket_api_base: str = Field(default_factory=lambda: os.getenv("POLYMARKET_API_BASE", "https://gamma-api.polymarket.com"))
  polymarket_api_key: str = Field(default_factory=lambda: os.getenv("POLYMARKET_API_KEY", ""))
  news_api_key: str = Field(default_factory=lambda: os.getenv("NEWS_API_KEY", ""))
  twitter_bearer_token: str = Field(default_factory=lambda: os.getenv("TWITTER_BEARER_TOKEN", ""))
  chroma_persist_path: str = Field(default_factory=lambda: os.getenv("CHROMA_PERSIST_PATH", ".chroma"))
  default_trend_keywords: List[str] = Field(default_factory=lambda: [kw.strip() for kw in os.getenv("DEFAULT_TREND_KEYWORDS", "polymarket, ai, elections, crypto").split(",") if kw.strip()])
  model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
  storage_dir: str = Field(default_factory=lambda: os.getenv("POLYSUGGEST_DATA_DIR", "data"))

  class Config:
    frozen = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
  return Settings()

