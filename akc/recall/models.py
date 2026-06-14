from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

_VALID_TIERS = {"gold", "production", "experimental", "demoted"}


class RecallRequest(BaseModel):
    task_context: str = Field(..., min_length=1, max_length=4000)
    tags: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=100)
    min_tier: str = "production"

    @field_validator("min_tier")
    @classmethod
    def validate_min_tier(cls, v: str) -> str:
        if v not in _VALID_TIERS:
            raise ValueError(
                f"min_tier must be one of {sorted(_VALID_TIERS)!r}, got {v!r}"
            )
        return v


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
    total_found: int
    query_ms: int = 0
