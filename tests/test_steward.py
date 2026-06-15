"""Regression tests for the Steward control-plane: store.curate_pattern,
store.load_gaps, and the /patterns /curate /gaps endpoints.

No external services or env vars required — exercises the store + router directly.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from akc.patterns.models import Pattern
from akc.patterns.store import JsonlStore
import akc.patterns.router as steward_router


@pytest.fixture
def store(tmp_path):
    return JsonlStore(kb_dir=str(tmp_path))


@pytest.fixture
async def seeded(store):
    await store.insert_pattern(Pattern(id="p-exp", context="exp", what_worked="x",
                                       tags=["aso", "jp"], confidence=0.67, tier="experimental"))
    await store.insert_pattern(Pattern(id="p-gold", context="gold", what_worked="y",
                                       tags=["kr"], confidence=0.95, tier="gold"))
    return store


# ---- store.curate_pattern: tier override clamps confidence into the tier band ----

async def test_curate_promote_clamps_to_gold_floor(seeded):
    up = await seeded.curate_pattern("p-exp", "gold", "consistent wins")
    assert up["tier"] == "gold"
    assert up["confidence"] >= 0.85


async def test_curate_demote_clamps_into_production_band(seeded):
    up = await seeded.curate_pattern("p-gold", "production", "stale")
    assert up["tier"] == "production"
    assert 0.70 <= up["confidence"] < 0.85


async def test_curate_unknown_id_returns_none(seeded):
    assert await seeded.curate_pattern("does-not-exist", "gold") is None


async def test_curate_promotion_surfaces_in_recently_promoted(seeded):
    await seeded.curate_pattern("p-exp", "gold", "promote")
    stats = await seeded.load_stats()
    assert any(r["new_tier"] == "gold" for r in stats["recently_promoted"])


# ---- store.load_gaps: empty recalls aggregate (case-insensitive), hits ignored ----

async def test_gaps_aggregate_empty_recalls_ignore_hits(store):
    await store.record_recall_query(0, "th puzzle keyword", ["aso", "th", "keyword"])
    await store.record_recall_query(0, "TH puzzle keyword", ["aso", "th"])
    await store.record_recall_query(3, "this query had hits", ["x"])
    gaps = await store.load_gaps()
    assert len(gaps) == 1
    assert gaps[0]["count"] == 2
    assert "aso" in gaps[0]["tags"]


# ---- steward router ----

@pytest.fixture
def client(tmp_path):
    # Seed patterns.jsonl directly (sync) so the store's asyncio.Lock binds to the
    # TestClient event loop, not a separate pre-run loop.
    pats = [
        Pattern(id="p-exp", context="exp", what_worked="x", tags=["aso", "jp"], confidence=0.67, tier="experimental"),
        Pattern(id="p-prod", context="prod", what_worked="z", tags=["kr"], confidence=0.78, tier="production"),
    ]
    (tmp_path / "patterns.jsonl").write_text("".join(p.model_dump_json() + "\n" for p in pats))
    steward_router.store = JsonlStore(kb_dir=str(tmp_path))
    app = FastAPI()
    app.include_router(steward_router.router)
    yield TestClient(app)
    steward_router.store = None


def test_list_patterns_all_tiers(client):
    r = client.get("/patterns")
    assert r.status_code == 200 and r.json()["total"] == 2


def test_list_patterns_tier_filter(client):
    assert client.get("/patterns?tier=production").json()["total"] == 1


def test_curate_endpoint_promote(client):
    r = client.post("/curate", json={"pattern_id": "p-prod", "tier": "gold", "reason": "evidence"})
    assert r.status_code == 200 and r.json()["tier"] == "gold" and r.json()["old_tier"] == "production"


def test_curate_endpoint_not_found(client):
    assert client.post("/curate", json={"pattern_id": "missing", "tier": "gold"}).status_code == 404


def test_curate_endpoint_bad_tier(client):
    assert client.post("/curate", json={"pattern_id": "p-exp", "tier": "platinum"}).status_code == 400


def test_gaps_endpoint_ok(client):
    assert client.get("/gaps").status_code == 200


def test_curate_requires_key_when_env_set(client, monkeypatch):
    monkeypatch.setenv("CURATOR_KEY", "s3cret")
    assert client.post("/curate", json={"pattern_id": "p-exp", "tier": "gold"}).status_code == 401
    ok = client.post("/curate", json={"pattern_id": "p-exp", "tier": "gold", "reason": "ok"},
                     headers={"X-Curator-Key": "s3cret"})
    assert ok.status_code == 200
