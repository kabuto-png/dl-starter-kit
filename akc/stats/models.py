from __future__ import annotations
from pydantic import BaseModel


class PromotionEvent(BaseModel):
    id: str | None
    old_tier: str
    new_tier: str
    timestamp: str | None  # ISO 8601 string from confidence_history.jsonl


class StatsResponse(BaseModel):
    total_patterns: int
    by_tier: dict[str, int]  # { "gold": N, "production": N, "experimental": N, "demoted": N }
    avg_confidence: float
    top_tags: list[str]       # top 10 by frequency, lowercase, deduped
    recall_hit_rate: float
    recently_promoted: list[PromotionEvent]  # last 5 tier upgrades
    total_queries: int = 0    # PRD §5: cumulative /recall calls (from confidence_history.jsonl)
    total_outcomes_recorded: int = 0  # PRD §5: cumulative /remember confidence_update events
