from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Dict, Iterable, List, Tuple

from .storage import StoredRun


def generate_insights(runs: Iterable[StoredRun]) -> Dict[str, object]:
    runs = list(runs)
    if not runs:
        return {
            "total_runs": 0,
            "unique_topics": 0,
            "avg_confidence": 0.0,
            "top_tags": [],
            "top_topics": [],
            "avg_sentiment": 0.0,
        }

    total_runs = len(runs)
    unique_topics = len({run.topic for run in runs})
    avg_confidence = mean(run.avg_confidence for run in runs)

    tag_counter = Counter()
    topic_counter = Counter()
    sentiments: List[float] = []

    for run in runs:
        topic_counter[run.topic] += 1
        tag_counter.update(run.tags)
        sentiments.extend(trend.sentiment for trend in run.data.trends)

    top_tags: List[Tuple[str, int]] = tag_counter.most_common(5)
    top_topics: List[Tuple[str, int]] = topic_counter.most_common(5)
    avg_sentiment = mean(sentiments) if sentiments else 0.0

    return {
        "total_runs": total_runs,
        "unique_topics": unique_topics,
        "avg_confidence": avg_confidence,
        "top_tags": top_tags,
        "top_topics": top_topics,
        "avg_sentiment": avg_sentiment,
    }


__all__ = ["generate_insights"]


