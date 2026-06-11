from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class RecallRequest(BaseModel):
    task_context: str
    tags: list[str] | None = None
    top_k: int = 5
    min_tier: str = "production"


class RecallResult(BaseModel):
    id: str
    what_worked: str
    what_failed: str
    confidence: float
    tier: str
    times_applied: int
    tags: list[str]
    last_updated: datetime | None
    relevance_score: float | None = None  # RCL-05: from Memory Service, or None on fallback


class RecallResponse(BaseModel):
    patterns: list[RecallResult]
    count: int
