from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from loguru import logger

from .config import get_settings
from .schemas import MarketSuggestion, SuggestionBundle


@dataclass
class StoredRun:
    run_id: int
    topic: str
    generated_at: datetime
    keywords: List[str]
    top_title: str
    top_confidence: float
    avg_confidence: float
    tags: List[str]
    data: SuggestionBundle

    def to_bundle(self) -> SuggestionBundle:
        return self.data


class BundleStore:
    def __init__(self, base_path: Optional[Path] = None) -> None:
        if base_path is None:
            settings = get_settings()
            base_path = Path(settings.storage_dir)
        if base_path.suffix == ".db":
            self.db_path = base_path
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            base_path.mkdir(parents=True, exist_ok=True)
            self.db_path = base_path / "bundles.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bundles (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic TEXT NOT NULL,
                  generated_at TEXT NOT NULL,
                  keywords TEXT,
                  top_title TEXT,
                  top_confidence REAL,
                  avg_confidence REAL,
                  tags TEXT,
                  payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def persist(self, bundle: SuggestionBundle) -> int:
        suggestions = bundle.suggestions
        if not suggestions:
            raise ValueError("Bundle must contain at least one suggestion.")
        top_suggestion = max(suggestions, key=lambda s: s.confidence)
        avg_confidence = sum(s.confidence for s in suggestions) / len(suggestions)
        tag_set = {tag for suggestion in suggestions for tag in suggestion.tags}
        payload = bundle.model_dump_json()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO bundles (
                  topic, generated_at, keywords, top_title, top_confidence, avg_confidence, tags, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bundle.topic,
                    bundle.generated_at.isoformat(),
                    ",".join(bundle.keywords),
                    top_suggestion.title,
                    top_suggestion.confidence,
                    avg_confidence,
                    ",".join(sorted(tag_set)),
                    payload,
                ),
            )
            conn.commit()
            run_id = int(cursor.lastrowid)
        logger.debug("Persisted bundle id=%s topic=%s", run_id, bundle.topic)
        return run_id

    def history(self, limit: Optional[int] = 50) -> List[StoredRun]:
        query = "SELECT id, topic, generated_at, keywords, top_title, top_confidence, avg_confidence, tags, payload FROM bundles ORDER BY datetime(generated_at) DESC"
        if limit is not None:
            query += " LIMIT ?"
            params: Sequence[object] = (limit,)
        else:
            params = ()
        runs: List[StoredRun] = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                payload = SuggestionBundle.model_validate_json(row[8])
                runs.append(
                    StoredRun(
                        run_id=row[0],
                        topic=row[1],
                        generated_at=datetime.fromisoformat(row[2]),
                        keywords=[kw for kw in (row[3] or "").split(",") if kw],
                        top_title=row[4],
                        top_confidence=row[5],
                        avg_confidence=row[6],
                        tags=[tag for tag in (row[7] or "").split(",") if tag],
                        data=payload,
                    )
                )
        return runs

    def get(self, run_id: int) -> StoredRun:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, topic, generated_at, keywords, top_title, top_confidence, avg_confidence, tags, payload
                FROM bundles WHERE id = ?
                """,
                (run_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise KeyError(f"No bundle found for id={run_id}")
        payload = SuggestionBundle.model_validate_json(row[8])
        return StoredRun(
            run_id=row[0],
            topic=row[1],
            generated_at=datetime.fromisoformat(row[2]),
            keywords=[kw for kw in (row[3] or "").split(",") if kw],
            top_title=row[4],
            top_confidence=row[5],
            avg_confidence=row[6],
            tags=[tag for tag in (row[7] or "").split(",") if tag],
            data=payload,
        )

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM bundles")
            conn.commit()


__all__ = ["BundleStore", "StoredRun"]


