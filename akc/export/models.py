from __future__ import annotations
from pydantic import BaseModel


class ExportRequest(BaseModel):
    """POST /kb/export body — empty at v1; filters deferred to v2."""
    pass
