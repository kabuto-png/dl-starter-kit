import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, field_validator


class Tier(str, Enum):
    gold = "gold"
    production = "production"
    experimental = "experimental"
    demoted = "demoted"


class Pattern(BaseModel):
    id: str = ""
    context: str
    what_worked: str = ""
    what_failed: str = ""
    tags: list[str] = []
    confidence: float = 0.67
    tier: str = "experimental"
    consecutive_failures: int = 0
    times_applied: int = 0
    last_updated: datetime | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list) -> list:
        return [t.lower() for t in v] if isinstance(v, list) else v

    def model_post_init(self, __context: object) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)


class ConfidenceEvent(BaseModel):
    pattern_id: str
    outcome: str
    old_confidence: float
    new_confidence: float
    old_tier: str
    new_tier: str
    timestamp: datetime | None = None

    def model_post_init(self, __context: object) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
