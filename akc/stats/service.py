"""
StatsService — delegates to extended store.load_stats().

STATS-01: total_patterns, by_tier, avg_confidence, top_tags (top 10).
STATS-02: recall_hit_rate from confidence_history.jsonl.
STATS-03: recently_promoted (last 5 tier upgrades from history).
"""
from __future__ import annotations
import logging

from akc.patterns.store import JsonlStore

logger = logging.getLogger("akc.stats.service")


class StatsService:
    def __init__(self, store: JsonlStore) -> None:
        self._store = store

    async def get_stats(self) -> dict:
        """
        Compute and return KB statistics.
        Delegates computation to JsonlStore.load_stats() (Phase 3 extended version).
        """
        stats = await self._store.load_stats()
        logger.info(
            "Stats: %d patterns, hit_rate=%.2f, promoted=%d",
            stats.get("total_patterns", 0),
            stats.get("recall_hit_rate", 0.0),
            len(stats.get("recently_promoted", [])),
        )
        return stats
