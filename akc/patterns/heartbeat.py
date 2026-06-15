"""Steward heartbeat — the autonomous curation pulse (OpenClaw's SOUL).

A server-side, always-on loop that runs one deterministic "tick" every
INTERVAL_SECONDS. Distinct from per-outcome apply_outcome(): the heartbeat does
TIME-BASED maintenance no event path covers —

  - DECAY: any non-demoted pattern idle longer than decay_days loses a little
    confidence each tick (use-it-or-lose-it) and is re-tiered naturally. An
    unused pattern keeps fading until it is used again (a success resets its
    last_updated clock and bumps confidence via apply_outcome).
  - STALE DEMOTE: an experimental pattern never applied (times_applied == 0) and
    idle longer than stale_days is a dead seed -> demoted.

Decision logic lives in compute_tick() (pure, no I/O, unit-tested). The write
side lives in JsonlStore.apply_heartbeat() so all JSONL/lock invariants stay in
one place.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from akc.patterns.engine import classify_tier

logger = logging.getLogger("akc.patterns.heartbeat")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Conservative defaults: a freshly-seeded KB (timestamps "today") is a NO-OP for
# ~2 weeks, so the live demo data is never altered by the autonomous loop.
# Reviewers see it act by calling POST /steward/heartbeat with smaller overrides.
INTERVAL_SECONDS = _int_env("AKC_HEARTBEAT_INTERVAL", 1800)  # 30 min
STALE_DAYS = _int_env("AKC_HEARTBEAT_STALE_DAYS", 30)
DECAY_DAYS = _int_env("AKC_HEARTBEAT_DECAY_DAYS", 14)
DECAY_DELTA = _float_env("AKC_HEARTBEAT_DECAY_DELTA", 0.02)

MIN_CONFIDENCE = 0.0
DEMOTED_CEIL = 0.499  # top of the demoted band — mirror of store._TIER_BANDS


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def compute_tick(
    patterns: list[dict],
    now: datetime,
    *,
    stale_days: int,
    decay_days: int,
    decay_delta: float,
) -> tuple[dict[str, dict], dict]:
    """Pure decision core for one heartbeat tick — no I/O.

    Returns (changes, summary):
      changes: {pattern_id: {"confidence": float, "tier": str}} to apply.
      summary: counts + affected ids, for logging and the API response.
    """
    changes: dict[str, dict] = {}
    decayed: list[str] = []
    demoted: list[str] = []

    for p in patterns:
        tier = p.get("tier", "experimental")
        if tier == "demoted":
            continue  # already at the floor
        pid = p.get("id")
        if not pid:
            continue
        conf = float(p.get("confidence", 0.0))
        last = _parse_ts(p.get("last_updated"))
        idle_days = (now - last).total_seconds() / 86400.0 if last else float("inf")

        # Dead-seed demotion: experimental, never applied, long idle.
        if (
            tier == "experimental"
            and int(p.get("times_applied", 0)) == 0
            and idle_days > stale_days
        ):
            changes[pid] = {"confidence": round(min(conf, DEMOTED_CEIL), 4), "tier": "demoted"}
            demoted.append(pid)
            continue

        # Decay: idle patterns fade. last_updated is intentionally NOT reset.
        if idle_days > decay_days:
            new_conf = max(MIN_CONFIDENCE, round(conf - decay_delta, 4))
            changes[pid] = {"confidence": new_conf, "tier": classify_tier(new_conf)}
            decayed.append(pid)

    summary = {
        "ran_at": now.isoformat(),
        "scanned": len(patterns),
        "decayed": decayed,
        "demoted": demoted,
        "n_decayed": len(decayed),
        "n_demoted": len(demoted),
        "thresholds": {
            "stale_days": stale_days,
            "decay_days": decay_days,
            "decay_delta": decay_delta,
        },
    }
    return changes, summary


async def run_loop(store) -> None:
    """Background pulse: every INTERVAL_SECONDS apply one tick. Best-effort.

    Guarded by AKC_HEARTBEAT_ENABLED (default on). Single-worker assumption: the
    runtime launches one uvicorn worker, so exactly one loop runs.
    """
    if os.environ.get("AKC_HEARTBEAT_ENABLED", "1").lower() not in ("1", "true", "yes"):
        logger.info("Heartbeat disabled via AKC_HEARTBEAT_ENABLED")
        return
    logger.info(
        "Heartbeat loop started — interval=%ss stale=%sd decay=%sd delta=%s",
        INTERVAL_SECONDS, STALE_DAYS, DECAY_DAYS, DECAY_DELTA,
    )
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        try:
            summary = await store.apply_heartbeat(
                stale_days=STALE_DAYS,
                decay_days=DECAY_DAYS,
                decay_delta=DECAY_DELTA,
                dry_run=False,
            )
            logger.info(
                "Heartbeat tick: scanned=%s decayed=%s demoted=%s",
                summary["scanned"], summary["n_decayed"], summary["n_demoted"],
            )
        except Exception as exc:  # never let the loop die
            logger.warning("Heartbeat tick failed (non-fatal): %s", exc)
