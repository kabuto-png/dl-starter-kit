"""Steward (control-plane) endpoints — consumed by the OpenClaw AKC Steward.

GET  /patterns  — list raw patterns (all tiers) for audit/dedup review.
POST /curate    — manual tier override (promote/demote) with a reason.
GET  /gaps      — empty-recall queries aggregated into coverage gaps.

These are governance verbs, distinct from the data-plane recall/remember path.
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from akc.patterns.store import JsonlStore

logger = logging.getLogger("akc.patterns.router")

# Injected from main.py after store initialization
store: Optional[JsonlStore] = None

router = APIRouter(tags=["steward"])

_VALID_TIERS = {"gold", "production", "experimental", "demoted"}


class CurateRequest(BaseModel):
    pattern_id: str = Field(..., min_length=1)
    tier: str
    reason: str = Field(default="", max_length=500)


def _require_store() -> JsonlStore:
    if store is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Store not initialized", "code": "service_unavailable"},
        )
    return store


@router.get("/patterns")
async def list_patterns(
    tier: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    """List patterns across all tiers (incl. experimental + demoted) for curation review."""
    s = _require_store()
    if tier and tier not in _VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"tier must be one of {sorted(_VALID_TIERS)}", "code": "bad_tier"},
        )
    patterns = await s.load_all(exclude_demoted=False)
    if tier:
        patterns = [p for p in patterns if p.get("tier") == tier]
    if tag:
        tl = tag.lower()
        patterns = [p for p in patterns if tl in [t.lower() for t in p.get("tags", [])]]
    return {"patterns": patterns[:limit], "total": len(patterns)}


@router.post("/curate")
async def curate(req: CurateRequest, x_curator_key: Optional[str] = Header(None)) -> dict:
    """Manually set a pattern's tier (promote/demote). Confidence clamps to tier band.

    Gated by X-Curator-Key only when CURATOR_KEY env is set (open otherwise, for demo).
    """
    expected = os.environ.get("CURATOR_KEY")
    if expected and not hmac.compare_digest(x_curator_key or "", expected):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid or missing curator key", "code": "unauthorized"},
        )
    if req.tier not in _VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"tier must be one of {sorted(_VALID_TIERS)}", "code": "bad_tier"},
        )
    s = _require_store()
    before = {p["id"]: p for p in await s.load_all(exclude_demoted=False)}.get(req.pattern_id)
    updated = await s.curate_pattern(req.pattern_id, req.tier, req.reason)
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "pattern not found", "code": "not_found"},
        )
    logger.info(
        "Curation: %s %s -> %s (%s)",
        req.pattern_id, before.get("tier") if before else "?", req.tier, req.reason or "no reason",
    )
    return {
        "id": updated["id"],
        "old_tier": before.get("tier") if before else None,
        "tier": updated["tier"],
        "confidence": updated["confidence"],
        "reason": req.reason,
    }


@router.get("/gaps")
async def gaps() -> dict:
    """Coverage gaps: queries that returned zero patterns, aggregated by frequency."""
    s = _require_store()
    return {"gaps": await s.load_gaps()}
