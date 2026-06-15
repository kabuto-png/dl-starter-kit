"""Tests for the Steward heartbeat — pure compute_tick decisions + store apply.

No external services or env vars required.
"""
from datetime import datetime, timedelta, timezone

from akc.patterns.heartbeat import compute_tick
from akc.patterns.models import Pattern
from akc.patterns.store import JsonlStore

NOW = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
FUTURE = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _p(pid, conf, tier, *, times_applied=1, age_days=0.0):
    last = (NOW - timedelta(days=age_days)).isoformat()
    return {
        "id": pid, "context": "c", "what_worked": "w", "tags": ["t"],
        "confidence": conf, "tier": tier, "consecutive_failures": 0,
        "times_applied": times_applied, "last_updated": last,
    }


# ---- compute_tick (pure, no I/O) ----

def test_fresh_patterns_are_noop():
    pats = [_p("a", 0.78, "production", age_days=1), _p("b", 0.9, "gold", age_days=2)]
    changes, summary = compute_tick(pats, NOW, stale_days=30, decay_days=14, decay_delta=0.02)
    assert changes == {}
    assert summary["n_decayed"] == 0 and summary["n_demoted"] == 0


def test_idle_pattern_decays_and_retiers():
    # production 0.71, idle 20d > 14d → 0.69 → experimental
    pats = [_p("a", 0.71, "production", age_days=20)]
    changes, _ = compute_tick(pats, NOW, stale_days=30, decay_days=14, decay_delta=0.02)
    assert changes["a"]["confidence"] == 0.69
    assert changes["a"]["tier"] == "experimental"


def test_dead_seed_demoted():
    # experimental, never applied, idle 40d > 30d → demoted (checked before decay)
    pats = [_p("a", 0.6, "experimental", times_applied=0, age_days=40)]
    changes, summary = compute_tick(pats, NOW, stale_days=30, decay_days=14, decay_delta=0.02)
    assert changes["a"]["tier"] == "demoted"
    assert changes["a"]["confidence"] <= 0.499
    assert summary["n_demoted"] == 1 and summary["n_decayed"] == 0


def test_demoted_untouched():
    pats = [_p("a", 0.3, "demoted", age_days=99)]
    changes, _ = compute_tick(pats, NOW, stale_days=30, decay_days=14, decay_delta=0.02)
    assert changes == {}


def test_gold_decays_after_long_idle():
    # gold 0.86, idle 30d → 0.84 → falls to production (use-it-or-lose-it)
    pats = [_p("a", 0.86, "gold", age_days=30)]
    changes, _ = compute_tick(pats, NOW, stale_days=30, decay_days=14, decay_delta=0.02)
    assert changes["a"]["confidence"] == 0.84
    assert changes["a"]["tier"] == "production"


# ---- store.apply_heartbeat (I/O) ----

async def test_apply_heartbeat_writes_and_logs(tmp_path):
    store = JsonlStore(kb_dir=str(tmp_path))
    await store.insert_pattern(Pattern(id="old", context="c", what_worked="w",
                                       tags=["t"], confidence=0.71, tier="production"))
    summary = await store.apply_heartbeat(stale_days=0, decay_days=0, decay_delta=0.02, now=FUTURE)
    assert summary["n_decayed"] == 1
    last = await store.load_last_heartbeat()
    assert last is not None and last["n_decayed"] == 1


async def test_apply_heartbeat_dry_run_no_write(tmp_path):
    store = JsonlStore(kb_dir=str(tmp_path))
    await store.insert_pattern(Pattern(id="old", context="c", what_worked="w",
                                       tags=["t"], confidence=0.71, tier="production"))
    summary = await store.apply_heartbeat(stale_days=0, decay_days=0, decay_delta=0.02,
                                          dry_run=True, now=FUTURE)
    assert summary["n_decayed"] == 1 and summary["dry_run"] is True
    pats = await store.load_all()
    assert pats[0]["confidence"] == 0.71  # unchanged
