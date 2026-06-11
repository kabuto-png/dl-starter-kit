"""
POST /kb/export — export Gold and Production patterns as markdown.

EXPORT-01: Returns all Gold + Production patterns.
EXPORT-02: Grouped by tier with full pattern detail block.
Returns: text/plain (markdown string), not JSON.
RCL-06: Structured error {"error": "...", "code": "..."} on failure.
"""
from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from akc.export.service import ExportService

logger = logging.getLogger("akc.export.router")

# Injected from main.py after service initialization
export_service: Optional[ExportService] = None

router = APIRouter(tags=["export"])


@router.post("/kb/export")
async def export_kb() -> PlainTextResponse:
    """
    POST /kb/export — export knowledge base as markdown.

    EXPORT-01: Renders all Gold + Production patterns.
    EXPORT-02: Grouped by tier with context, what_worked, what_failed, confidence, tags per pattern.

    Returns: markdown content as text/plain.
    """
    if export_service is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Export service not initialized", "code": "service_unavailable"},
        )
    try:
        markdown = await export_service.export_markdown()
        return PlainTextResponse(content=markdown, media_type="text/plain")
    except Exception as exc:
        logger.error("Export unexpected error: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "code": "internal_error"},
        )
