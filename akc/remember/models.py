from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DistillRequest(BaseModel):
    """Request body for POST /remember.

    RMB-01: task_context and outcome are required fields.
    RMB-07: patterns_used IDs trigger confidence feedback on existing patterns.
    """
    task_context: str = Field(..., min_length=1, max_length=4000)  # Required: context of the task
    outcome: str = Field(..., min_length=1, max_length=8000)       # Required: raw outcome text to distill
    what_happened: Optional[str] = Field(None, max_length=8000) # Optional: detailed description of what occurred
    tags: Optional[list[str]] = None                             # Optional: caller-supplied tags for the new pattern
    patterns_used: Optional[list[str]] = Field(None, max_length=50)  # Optional: IDs of patterns that were applied (cap prevents lock-DoS)
    success: Optional[bool] = None                               # Optional: whether the task succeeded

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list) -> list:
        """Normalize caller-supplied tags to lowercase — matches Pattern model's ENG-07 convention."""
        return [t.lower() for t in v] if isinstance(v, list) else v


class DistilledPattern(BaseModel):
    """Structured output extracted by Qwen from raw outcome text.

    RMB-03: Matches the JSON schema Qwen is prompted to produce.
    ENG-07: Tags normalized to lowercase at validation time.
    """
    context: str                   # Brief description of the task scenario
    what_worked: str               # Specific thing that succeeded
    what_failed: str = ""          # Specific thing that failed (empty string if pure success)
    tags: list[str] = []           # Lowercase tags describing this outcome

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list) -> list:
        """Normalize all tags to lowercase — matches Phase 1 ENG-07 pattern."""
        return [t.lower() for t in v] if isinstance(v, list) else v
