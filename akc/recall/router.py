"""
POST /recall — query the knowledge base for confidence-ranked patterns.

RCL-01: Accepts task_context, tags (optional), top_k (default 5), min_tier (default "production").
RCL-06: All 4xx/5xx responses return {"error": "...", "code": "..."} — no bare FastAPI 422s.
"""
from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from akc.recall.models import RecallRequest, RecallResponse
from akc.recall.service import RecallService

logger = logging.getLogger("akc.recall.router")

# Injected from main.py after service initialization
recall_service: Optional[RecallService] = None

router = APIRouter(tags=["recall"])


@router.post("/recall", response_model=RecallResponse)
async def recall(request: RecallRequest) -> RecallResponse:
    """
    POST /recall — return confidence-ranked patterns from the knowledge base.

    RCL-01: Accepts task_context, tags, top_k, min_tier.
    RCL-02: Returns id, what_worked, what_failed, confidence, tier, times_applied, tags, last_updated, relevance_score.
    RCL-03: Results ranked by confidence descending; demoted patterns never returned.
    RCL-04: Semantic search with fallback to local tag+tier filter.
    RCL-05: relevance_score included when Memory Service responds.
    RCL-06: Structured error responses {"error": "...", "code": "..."}.
    """
    if recall_service is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Recall service not initialized", "code": "service_unavailable"},
        )
    try:
        return await recall_service.query(request)
    except ValueError as exc:
        logger.error("Recall validation error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "code": "recall_error"},
        )
    except Exception as exc:
        logger.error("Recall unexpected error: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "code": "internal_error"},
        )
