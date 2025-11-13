# Polymarket AI Market Suggestor

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.x-1A4C82?style=flat)](https://python.langchain.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT-4o-412991?style=flat&logo=openai)](https://openai.com/)
[![Typer](https://img.shields.io/badge/Typer-CLI-555?style=flat)](https://typer.tiangolo.com/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-green.svg)](LICENSE)

[![Telegram](https://img.shields.io/badge/Telegram-@lorine93s-2CA5E0?style=flat&logo=telegram)](https://t.me/lorine93s)
[![Twitter/X](https://img.shields.io/badge/X-@kakamajo__btc-000000?style=flat&logo=x)](https://twitter.com/kakamajo_btc)

AI-native workflow that transforms real-time trends, news, and existing Polymarket markets into actionable, publish-ready market suggestions. Built for research teams, traders, DAO governance desks, and community curators who want to discover “what market should Polymarket list next?” using a mix of LLM reasoning, sentiment signals, and overlap checks.

SEO keywords: Polymarket AI, AI agent Polymarket, Polymarket AI market prediction, AI market prediction, Polymarket prediction market bot, Polymarket real-time trading bot, Polymarket AI trading bot, Polymarket market analyzer, Polymarket AI market suggestor.



## Why PolySuggest AI?

- **Trend-aware ideation** – Combines live NewsAPI + Twitter sentiment to surface emerging narratives.
- **Crypto momentum feed** – Adds CoinGecko trending tokens as signals for on-chain market discovery.
- **Overlap protection** – Uses Polymarket Gamma API to ensure suggestions are novel and not already live.
- **LLM-powered reasoning** – GPT-4o (or fallback heuristic) produces clear resolution rules, YES/NO framing, and references.
- **Explainable output** – Each idea includes rationale, confidence scoring, and tagged metadata for filtering.
- **Local knowledge base** – SQLite bundle store captures every run for history, analytics, and dashboards.
- **Ready for production** – Typer CLI, structured logging, Markdown/JSON reporting, tests, Docker-friendly dependency set.

> ℹ️ The AI core and workflow are inspired by leading open-source prediction market agents such as [Prediction-Market-AggregationAgent-system](https://github.com/Prithwis-AIAgent/Prediction-Market-AggregationAgent-system) while focusing on generative market ideation instead of trading.


## Architecture Overview

```
TrendScanner (NewsAPI, Twitter API)
        │
        ▼
Sentiment & Keyword signals ────────┐
                                    │
PolymarketClient (Gamma API)        │
        │                           │
        ▼                           │
Existing market snapshots ──────────┘
        │
        ▼
SuggestionEngine (LangChain + GPT-4o)
        │
        ▼
SuggestionBundle (Pydantic)
        │
        ├─ Storage (SQLite) — durable bundle history + analytics
        ├─ CLI (Typer + Rich) — interactive reports
        └─ Reporting utils — JSON / Markdown / history summaries
```

- `trend_scanner.py` — pulls hot news and tweets with VADER sentiment.
- `trend_scanner.py` (crypto) — optional CoinGecko trending feed for DeFi narratives.
- `polymarket_client.py` — fetches trending/current markets via Gamma API.
- `ai.py` — formats context + prompts GPT-4o (falls back if no API key).
- `orchestrator.py` — runs the end-to-end pipeline and deduplicates output.
- `storage.py` — SQLite-backed bundle persistence.
- `analytics.py` — portfolio-wide stats on past runs.
- `reporting.py` — exports Markdown dashboards and history summaries.
- `cli.py` — Typer command group: `suggest` and `summarize`.


## Quick Start

```bash
git clone https://github.com/your-org/polymarket-ai-market-suggestor.git
cd polymarket-ai-market-suggestor
python -m venv .venv && source .venv/bin/activate  # or use uv/pdm
pip install -r requirements.txt
cp ENV.sample .env
# populate .env with OpenAI / NewsAPI / Twitter keys
```

### Generate Suggestions

```bash
polysuggest suggest "AI safety regulation" --keywords "AI,regulation,legislation" --count 4 \
  --markdown reports/ai-safety.md --output reports/ai-safety.json
```

Sample console output:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Title                                         ┃ Confidence ┃ Resolution Source          ┃ Tags          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Will the EU enact the AI Act before Q4 2025?  │ 0.72       │ Official EU Parliament DB  │ ai-policy,... │
│ ...                                           │ ...        │ ...                        │ ...           │
└───────────────────────────────────────────────┴────────────┴────────────────────────────┴───────────────┘
```

Outputs:

- `reports/ai-safety.json` – structured `SuggestionBundle`.
- `reports/ai-safety.md` – Markdown one-pager for sharing.
- SQLite bundle store (default `data/bundles.db`) captures a full copy for analytics.

### Summarize History

```bash
polysuggest summarize reports/
```

Displays a Rich table of prior suggestion runs (topic, timestamp, top pick, confidence).

To use the built-in storage instead:

```bash
polysuggest summarize
```

### Inspect & Analyze

```bash
polysuggest show 3        # Detailed view for run #3
polysuggest insights      # Aggregated stats (top tags, avg confidence, sentiment)
```


## Configuration

Environment variables (copy `ENV.sample`):

| Variable | Description | Example |
| --- | --- | --- |
| `OPENAI_API_KEY` | GPT-4o API key for suggestion engine | `sk-...` |
| `OPENAI_MODEL` | Override model | `gpt-4o-mini` |
| `POLYMARKET_API_BASE` | Gamma API endpoint | `https://gamma-api.polymarket.com` |
| `NEWS_API_KEY` | NewsAPI key (optional) | `news-...` |
| `TWITTER_BEARER_TOKEN` | Twitter v2 bearer token (optional) | `AAAAAAAA...` |
| `DEFAULT_TREND_KEYWORDS` | Fallback keywords | `polymarket, ai, elections` |
| `CHROMA_PERSIST_PATH` | Future use for RAG vector store | `.chroma` |
| `POLYSUGGEST_DATA_DIR` | Directory for SQLite bundle storage | `data` |

No LLM key? The system falls back to a deterministic heuristic generator so pipelines remain testable offline.


## Roadmap

- Integrate Tavily/NewsCatcher for better global news coverage.
- Plug in CrewAI/agent voting for multi-model consensus.
- Streamlit dashboard for live market ideation boards.
- Optional Polymarket CLOB integration to auto-submit community market suggestions.
- RAG knowledge base seeded with past Polymarket markets and governance posts.


## Development & Testing

```bash
pip install -r requirements.txt
pytest
```

To run the CLI inside the repo without installing:

```bash
python -m polysuggest.cli suggest "US election turnout"
```

Logging is powered by Loguru; set `LOGURU_LEVEL=DEBUG` for verbose traces.

Dockerfile coming soon (project is fully dependency-pinned via `requirements.txt` / `pyproject.toml`).

## Need help or collaboration?

- 📧 xsui46941@gmail.com
- 📣 Telegram: [@lorine93s](https://t.me/lorine93s)
- 🐦 X (Twitter): [@kakamajo_btc](https://twitter.com/kakamajo_btc)

Let’s build the next generation of AI-native Polymarket tooling together.
