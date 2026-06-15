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


class HeartbeatRequest(BaseModel):
    """Optional overrides for a manual heartbeat. Omitted fields use env defaults."""
    stale_days: Optional[int] = Field(default=None, ge=0)
    decay_days: Optional[int] = Field(default=None, ge=0)
    decay_delta: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    dry_run: bool = False


@router.post("/steward/heartbeat")
async def steward_heartbeat(
    req: HeartbeatRequest, x_curator_key: Optional[str] = Header(None),
) -> dict:
    """Fire one Steward heartbeat tick now — the autonomous curation pulse.

    Same X-Curator-Key gate as /curate. Optional body overrides let a reviewer
    force action (e.g. {"decay_days": 0}) or preview with {"dry_run": true}.
    """
    expected = os.environ.get("CURATOR_KEY")
    if expected and not hmac.compare_digest(x_curator_key or "", expected):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid or missing curator key", "code": "unauthorized"},
        )
    s = _require_store()
    from akc.patterns import heartbeat as hb
    summary = await s.apply_heartbeat(
        stale_days=req.stale_days if req.stale_days is not None else hb.STALE_DAYS,
        decay_days=req.decay_days if req.decay_days is not None else hb.DECAY_DAYS,
        decay_delta=req.decay_delta if req.decay_delta is not None else hb.DECAY_DELTA,
        dry_run=req.dry_run,
    )
    logger.info(
        "Heartbeat (manual): scanned=%s decayed=%s demoted=%s dry_run=%s",
        summary["scanned"], summary["n_decayed"], summary["n_demoted"], summary["dry_run"],
    )
    return summary


@router.get("/steward/heartbeat")
async def steward_heartbeat_status() -> dict:
    """Last heartbeat run (proof-of-life) + the configured cadence/thresholds."""
    s = _require_store()
    from akc.patterns import heartbeat as hb
    return {
        "last_run": await s.load_last_heartbeat(),
        "config": {
            "interval_seconds": hb.INTERVAL_SECONDS,
            "stale_days": hb.STALE_DAYS,
            "decay_days": hb.DECAY_DAYS,
            "decay_delta": hb.DECAY_DELTA,
        },
    }
