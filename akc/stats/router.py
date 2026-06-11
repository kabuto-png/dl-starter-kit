"""
GET /stats — KB health and usage statistics.

STATS-01: total_patterns, by_tier, avg_confidence, top_tags.
STATS-02: recall_hit_rate.
STATS-03: recently_promoted.
RCL-06: Structured error responses {"error": "...", "code": "..."}.
"""
from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from akc.stats.models import StatsResponse
from akc.stats.service import StatsService

logger = logging.getLogger("akc.stats.router")

# Injected from main.py after service initialization
stats_service: Optional[StatsService] = None

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """
    GET /stats — retrieve KB statistics.

    STATS-01: Returns total_patterns, by_tier counts, avg_confidence, top_tags (top 10).
    STATS-02: Returns recall_hit_rate.
    STATS-03: Returns recently_promoted (last 5 tier upgrades).
    """
    if stats_service is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Stats service not initialized", "code": "service_unavailable"},
        )
    try:
        data = await stats_service.get_stats()
        return StatsResponse(**data)
    except Exception as exc:
        logger.error("Stats unexpected error: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "code": "internal_error"},
        )
