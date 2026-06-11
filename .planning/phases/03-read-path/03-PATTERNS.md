# Phase 3: Read Path - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 11 new/modified files across 3 sub-packages
**Analogs found:** 3 from Phase 1 (store.py extensions, models.py structure, router setup)

---

## Codebase Analog Assessment

Existing reference points:

| Pattern Need | Source File | Quality |
|---|---|---|
| Router setup | Phase 1 main.py (FastAPI app structure) | structural-fragment |
| Pydantic model pattern | Phase 1 akc/patterns/models.py | reusable-pattern |
| async/await + asyncio.Lock | Phase 1 akc/patterns/store.py | reusable-pattern |
| asyncio.to_thread for sync operations | Phase 1 akc/patterns/store.py | reusable-pattern |

All Phase 3 service patterns (semantic search adapter, stats aggregation, export rendering) are
new to the codebase and sourced from RESEARCH.md + REQUIREMENTS.md.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `akc/recall/models.py` | model | transform | Phase 1 akc/patterns/models.py | reusable-pattern |
| `akc/recall/engine.py` | utility | transform | Phase 1 akc/patterns/engine.py | structural-fragment |
| `akc/recall/search.py` | adapter | HTTP + local-fallback | none (new pattern) | research-only |
| `akc/recall/service.py` | service | orchestration | Phase 1 akc/patterns/store.py | structural-fragment |
| `akc/recall/router.py` | router | request-response | Phase 1 main.py (endpoint pattern) | reusable-pattern |
| `akc/stats/models.py` | model | transform | Phase 1 akc/patterns/models.py | reusable-pattern |
| `akc/stats/service.py` | service | aggregation | Phase 1 akc/patterns/store.py | structural-fragment |
| `akc/stats/router.py` | router | request-response | Phase 1 main.py (endpoint pattern) | reusable-pattern |
| `akc/export/models.py` | model | transform | Phase 1 akc/patterns/models.py | reusable-pattern |
| `akc/export/service.py` | service | rendering | none (new pattern) | research-only |
| `akc/export/router.py` | router | request-response | Phase 1 main.py (endpoint pattern) | reusable-pattern |
| `main.py` (extend) | app-factory | request-response | existing main.py | reusable-pattern |
| `akc/patterns/store.py` (extend) | service | file-I/O + aggregation | existing store.py | reusable-pattern |

---

## Pattern Assignments

### `akc/recall/models.py` (model, transform) — NEW

**Analog:** Phase 1 `akc/patterns/models.py` (Pydantic model structure)

**Pattern** (RCL-01, RCL-02):

```python
from pydantic import BaseModel
from datetime import datetime

class RecallRequest(BaseModel):
    task_context: str
    tags: list[str] | None = None
    top_k: int = 5
    min_tier: str = "production"

class RecallResult(BaseModel):
    id: str
    what_worked: str
    what_failed: str
    confidence: float
    tier: str
    times_applied: int
    tags: list[str]
    last_updated: datetime | None
    relevance_score: float | None = None  # RCL-05: from Memory Service, or None

class RecallResponse(BaseModel):
    patterns: list[RecallResult]
    count: int
```

**Key constraints:**
- `relevance_score: float | None` — set if Memory Service returns score, None on fallback
- `last_updated` must be datetime (not string) for API consistency
- All models inherit from `BaseModel` for automatic validation and JSON serialization

---

### `akc/stats/models.py` (model, transform) — NEW

**Analog:** Phase 1 `akc/patterns/models.py` (Pydantic model structure)

**Pattern** (STATS-01, STATS-02, STATS-03):

```python
from pydantic import BaseModel

class PromotionEvent(BaseModel):
    id: str
    old_tier: str
    new_tier: str
    timestamp: str  # ISO 8601 from confidence_history.jsonl

class StatsResponse(BaseModel):
    total_patterns: int
    by_tier: dict[str, int]  # { "gold": N, "production": N, "experimental": N, "demoted": N }
    avg_confidence: float
    top_tags: list[str]
    recall_hit_rate: float
    recently_promoted: list[PromotionEvent]
```

**Key constraints:**
- `by_tier` must have exactly 4 keys (gold, production, experimental, demoted)
- `avg_confidence` rounded to 2 decimal places
- `top_tags` is list of tag strings (not dict), max 10 entries
- `recently_promoted` max 5 entries, sorted by timestamp descending

---

### `akc/export/models.py` (model, transform) — NEW

**Analog:** Phase 1 `akc/patterns/models.py` (Pydantic model structure)

**Pattern** (EXPORT-01, EXPORT-02):

```python
from pydantic import BaseModel

class ExportRequest(BaseModel):
    # POST /kb/export accepts empty body or optional filters (deferred to v2)
    pass

class ExportResponse(BaseModel):
    # Response is markdown text, not JSON
    # Handled as text/plain Content-Type in router
    pass
```

**Key constraints:**
- Export endpoint returns `text/plain` or `text/markdown`, not JSON
- Response is markdown string, not a Pydantic model
- Consider returning `str` directly from service instead of wrapping in model

---

### `akc/recall/engine.py` (utility, transform) — NEW

**Analog:** Phase 1 `akc/patterns/engine.py` (pure functions, tier logic)

**Pattern** (RCL-03):

```python
def filter_and_rank(
    patterns: list[dict],
    min_tier: str = "production",
    tags: list[str] | None = None,
    top_k: int = 5
) -> list[dict]:
    """
    Filter patterns by tier and tags, rank by confidence or relevance_score descending.
    RCL-03: Demoted patterns never returned.
    """
    tier_rank = {"gold": 3, "production": 2, "experimental": 1, "demoted": 0}
    min_rank = tier_rank.get(min_tier, 2)
    
    # Filter step
    filtered = []
    for p in patterns:
        # RCL-03: exclude demoted FIRST
        if p.get("tier") == "demoted":
            continue
        
        # min_tier threshold
        if tier_rank.get(p.get("tier"), 0) < min_rank:
            continue
        
        # tags filter (optional)
        if tags:
            pattern_tags = set(t.lower() for t in p.get("tags", []))
            request_tags = set(t.lower() for t in tags)
            if not pattern_tags.intersection(request_tags):
                continue
        
        filtered.append(p)
    
    # Sort step — prefer relevance_score from Memory Service, fall back to confidence
    if filtered and "relevance_score" in filtered[0]:
        filtered.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    else:
        filtered.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    
    # Paginate
    return filtered[:top_k]
```

**Key constraints:**
- Demoted check MUST happen before min_tier check (demoted is a lock, not a score)
- Tag matching is case-insensitive (both pattern tags and request tags lowercased)
- Tag matching is OR logic — pattern needs ANY of the request tags
- Sort is stable — if relevance_score present on any item, use it; else use confidence
- Pure function — no I/O, no state mutation

---

### `akc/recall/search.py` (adapter, HTTP + local-fallback) — NEW

**Analog:** None (new pattern). Source: RESEARCH.md Key Implementation Constraints (1), RCL-04, RCL-05

**Pattern** (RCL-04, RCL-05 — Memory Service adapter with fallback):

```python
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("akc.recall.search")

async def semantic_search(
    task_context: str,
    patterns: list[dict],
    memory_service_url: Optional[str] = None,
    timeout_sec: float = 2.0
) -> list[dict]:
    """
    Attempt semantic search via AgentBase Memory Service.
    Fallback to local patterns if timeout or unavailable.
    
    RCL-04: asyncio.timeout guard, graceful fallback
    RCL-05: relevance_score threaded through on success
    
    Args:
        task_context: user's task description
        patterns: list of candidate patterns from store (already filtered by min_tier, tags)
        memory_service_url: Optional URL to Memory Service (constructed from MEMORY_ID env var)
        timeout_sec: timeout for Memory Service HTTP call (default 2.0)
    
    Returns:
        list of patterns with relevance_score attached (from Memory Service)
        or original patterns with relevance_score=None (fallback)
    """
    if not memory_service_url:
        logger.debug("Memory Service URL not configured, using local fallback")
        return patterns
    
    try:
        async with asyncio.timeout(timeout_sec):
            # HTTP call to Memory Service
            # Expected URL pattern: https://agentbase.{memory_id}/api/semantic-search
            # Request body: { "query": task_context, "candidates": patterns }
            # Response: { "results": [{ "id": "...", "relevance_score": 0.92 }, ...] }
            
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    memory_service_url,
                    json={
                        "query": task_context,
                        "candidates": [{"id": p.get("id")} for p in patterns],
                        "top_k": len(patterns),
                    },
                    timeout=timeout_sec
                )
                response.raise_for_status()
                result = response.json()
            
            # Thread relevance_score through
            scored_patterns = []
            results_by_id = {r["id"]: r for r in result.get("results", [])}
            
            for pattern in patterns:
                pattern_copy = pattern.copy()
                if pattern["id"] in results_by_id:
                    pattern_copy["relevance_score"] = results_by_id[pattern["id"]].get("relevance_score")
                scored_patterns.append(pattern_copy)
            
            logger.info(f"Memory Service returned {len(scored_patterns)} results")
            return scored_patterns
            
    except asyncio.TimeoutError:
        logger.warning(f"Memory Service timeout ({timeout_sec}s), falling back to confidence-based ranking")
        return patterns
    except Exception as e:
        logger.warning(f"Memory Service error: {type(e).__name__}: {e}, falling back")
        return patterns
```

**Key constraints:**
- Try/except MUST wrap the timeout — do not let TimeoutError escape to caller
- On any error (timeout, HTTP error, parse error), return patterns as-is (fallback)
- relevance_score is optional — set on success, not set on fallback
- Use `httpx.AsyncClient` for async HTTP (not `requests`, which blocks the event loop)
- Log at WARNING level on timeout/error (not ERROR) — fallback is expected and acceptable

---

### `akc/recall/service.py` (service, orchestration) — NEW

**Analog:** Phase 1 `akc/patterns/store.py` (async orchestration pattern)

**Pattern** (RCL-01 through RCL-06 orchestration):

```python
import logging
from typing import Optional

from akc.patterns.store import JsonlStore
from akc.recall.models import RecallRequest, RecallResult, RecallResponse
from akc.recall.engine import filter_and_rank
from akc.recall.search import semantic_search

logger = logging.getLogger("akc.recall.service")

class RecallService:
    def __init__(self, store: JsonlStore, memory_service_url: Optional[str] = None):
        self._store = store
        self._memory_service_url = memory_service_url
    
    async def query(self, request: RecallRequest) -> RecallResponse:
        """
        Orchestrate recall: load candidates → semantic search → filter/rank → return.
        
        RCL-01: Accept RecallRequest with task_context, tags, top_k, min_tier
        RCL-02: Return RecallResult with all required fields
        RCL-04: Use Memory Service with fallback
        RCL-05: Include relevance_score if available
        """
        # Load candidates from store (Phase 1 interface)
        candidates = await self._store.load_active(
            min_tier=request.min_tier,
            tags=request.tags
        )
        
        # Semantic search (or fallback to local ranking)
        scored = await semantic_search(
            task_context=request.task_context,
            patterns=candidates,
            memory_service_url=self._memory_service_url,
            timeout_sec=2.0
        )
        
        # Filter and paginate
        ranked = filter_and_rank(
            patterns=scored,
            min_tier=request.min_tier,
            tags=request.tags,
            top_k=request.top_k
        )
        
        # Convert to RecallResult models
        results = [
            RecallResult(
                id=p["id"],
                what_worked=p.get("what_worked", ""),
                what_failed=p.get("what_failed", ""),
                confidence=p.get("confidence", 0),
                tier=p.get("tier", "experimental"),
                times_applied=p.get("times_applied", 0),
                tags=p.get("tags", []),
                last_updated=p.get("last_updated"),
                relevance_score=p.get("relevance_score"),
            )
            for p in ranked
        ]
        
        # Record recall query in history for stats tracking (STATS-02)
        await self._store.record_recall_query(result_count=len(results))
        
        logger.info(f"Recall: {len(candidates)} candidates → {len(results)} results")
        return RecallResponse(patterns=results, count=len(results))
```

**Key constraints:**
- Initialize with both store and optional memory_service_url
- Load candidates using Phase 1's `store.load_active()` (already filtered)
- semantic_search adapter handles both service and fallback
- filter_and_rank applies pagination (top_k)
- Convert raw patterns to RecallResult models (validation + type safety)
- Always call `record_recall_query()` for stats tracking

---

### `akc/recall/router.py` (router, request-response) — NEW

**Analog:** Phase 1 `main.py` (FastAPI endpoint pattern)

**Pattern** (RCL-01, RCL-06 — endpoint + error handling):

```python
import logging
from fastapi import APIRouter, HTTPException

from akc.recall.models import RecallRequest, RecallResponse
from akc.recall.service import RecallService

logger = logging.getLogger("akc.recall.router")

# Initialized in main.py and injected into router
recall_service: RecallService = None

router = APIRouter(prefix="/recall", tags=["recall"])

@router.post("", response_model=RecallResponse)
async def recall(request: RecallRequest) -> RecallResponse:
    """
    POST /recall — query the knowledge base for patterns.
    
    RCL-01: Accept task_context, tags (optional), top_k (default 5), min_tier (default "production")
    RCL-02: Return patterns with all required fields
    RCL-03: Results ranked by confidence descending
    RCL-04: Semantic search with fallback
    RCL-05: Include relevance_score if available
    RCL-06: Structured error responses
    """
    try:
        return await recall_service.query(request)
    except ValueError as e:
        # RCL-06: Wrap ValueError in structured error
        logger.error(f"Recall error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "recall_error"}
        )
    except Exception as e:
        # RCL-06: Unexpected errors also wrapped
        logger.error(f"Recall unexpected error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "code": "internal_error"}
        )
```

**Key constraints:**
- Router depends on `recall_service` injected from main.py
- Use FastAPI's `response_model=RecallResponse` for automatic validation
- RCL-06: Catch exceptions and return `{"error": "...", "code": "..."}` format
- Log all errors at ERROR level (not warning)

---

### `akc/stats/service.py` (service, aggregation) — NEW

**Analog:** Phase 1 `akc/patterns/store.py` (file I/O + aggregation pattern)

**Pattern** (STATS-01, STATS-02, STATS-03 — extend Phase 1 store.load_stats()):

```python
import logging

from akc.patterns.store import JsonlStore

logger = logging.getLogger("akc.stats.service")

class StatsService:
    def __init__(self, store: JsonlStore):
        self._store = store
    
    async def get_stats(self) -> dict:
        """
        Compute KB statistics.
        
        STATS-01: total_patterns, by_tier counts, avg_confidence, top_tags
        STATS-02: recall_hit_rate from confidence_history.jsonl
        STATS-03: recently_promoted (last 5 tier upgrades)
        """
        # Use extended Phase 1 store.load_stats() which returns all fields
        stats = await self._store.load_stats()
        
        logger.info(
            f"Stats: {stats['total_patterns']} patterns, "
            f"hit_rate={stats['recall_hit_rate']:.2%}, "
            f"promoted={len(stats['recently_promoted'])}"
        )
        return stats
```

**Key constraints:**
- Delegate to Phase 1's extended `store.load_stats()` (no computation here)
- Return dict with keys: total_patterns, by_tier, avg_confidence, top_tags, recall_hit_rate, recently_promoted
- No caching at MVP scale; GET /stats scans files on each request

---

### `akc/stats/router.py` (router, request-response) — NEW

**Analog:** Phase 1 `main.py` (FastAPI endpoint pattern)

**Pattern** (STATS-01, STATS-02, STATS-03):

```python
import logging
from fastapi import APIRouter

from akc.stats.models import StatsResponse
from akc.stats.service import StatsService

logger = logging.getLogger("akc.stats.router")

# Initialized in main.py
stats_service: StatsService = None

router = APIRouter(tags=["stats"])

@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """
    GET /stats — retrieve KB statistics.
    
    STATS-01: total_patterns, by_tier, avg_confidence, top_tags
    STATS-02: recall_hit_rate
    STATS-03: recently_promoted
    """
    data = await stats_service.get_stats()
    return StatsResponse(**data)
```

**Key constraints:**
- GET endpoint (read-only, no body)
- Return StatsResponse (Pydantic model with validation)
- Service returns dict; router converts to model

---

### `akc/export/service.py` (service, rendering) — NEW

**Analog:** None (markdown rendering is new). Source: RESEARCH.md Key Implementation Constraints (6)

**Pattern** (EXPORT-01, EXPORT-02):

```python
import logging
from datetime import datetime, timezone

from akc.patterns.store import JsonlStore

logger = logging.getLogger("akc.export.service")

class ExportService:
    def __init__(self, store: JsonlStore):
        self._store = store
    
    async def export_markdown(self) -> str:
        """
        Export Gold and Production patterns as markdown.
        
        EXPORT-01: Render all Gold + Production patterns as human-readable markdown
        EXPORT-02: Grouped by tier, each pattern shows context, what_worked, what_failed, confidence, tags
        """
        # Load all patterns (Phase 1 store extension)
        patterns = await self._store.load_all(exclude_demoted=False)
        
        # Filter to Gold and Production tiers
        gold = [p for p in patterns if p.get("tier") == "gold"]
        production = [p for p in patterns if p.get("tier") == "production"]
        
        # Render markdown
        timestamp = datetime.now(timezone.utc).isoformat()
        sections = []
        
        sections.append(f"# AKC Knowledge Base Export")
        sections.append(f"")
        sections.append(f"**Generated:** {timestamp}")
        sections.append(f"**Total patterns:** {len(gold) + len(production)}")
        sections.append(f"")
        
        for tier_name, tier_patterns in [("Gold (Highest Confidence)", gold), ("Production", production)]:
            sections.append(f"## {tier_name}")
            sections.append(f"")
            
            if not tier_patterns:
                sections.append(f"*(no patterns in this tier)*")
                sections.append(f"")
                continue
            
            for p in tier_patterns:
                sections.append(f"### Pattern: {p.get('id')}")
                sections.append(f"")
                sections.append(f"- **Context:** {p.get('context', '')}")
                sections.append(f"- **What Worked:** {p.get('what_worked', '')}")
                sections.append(f"- **What Failed:** {p.get('what_failed', '')}")
                sections.append(f"- **Confidence:** {p.get('confidence', 0):.2f}")
                sections.append(f"- **Tags:** {', '.join(p.get('tags', []))}")
                sections.append(f"")
        
        markdown = "\n".join(sections)
        logger.info(f"Export: {len(gold) + len(production)} patterns, {len(markdown)} bytes")
        return markdown
```

**Key constraints:**
- Filter to `tier in ["gold", "production"]` only (EXPORT-01)
- Render markdown template with tier headers and pattern details
- Include context, what_worked, what_failed, confidence (2 decimal places), tags
- Return raw markdown string (not wrapped in model)

---

### `akc/export/router.py` (router, request-response) — NEW

**Analog:** Phase 1 `main.py` (FastAPI endpoint pattern, but with text/plain response)

**Pattern** (EXPORT-01):

```python
import logging
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from akc.export.service import ExportService

logger = logging.getLogger("akc.export.router")

# Initialized in main.py
export_service: ExportService = None

router = APIRouter(tags=["export"])

@router.post("/kb/export")
async def export_kb() -> PlainTextResponse:
    """
    POST /kb/export — export Gold and Production patterns as markdown.
    
    EXPORT-01: Render all Gold + Production patterns
    EXPORT-02: Grouped by tier with full pattern details
    
    Returns: markdown text/plain, not JSON
    """
    markdown = await export_service.export_markdown()
    return PlainTextResponse(content=markdown, media_type="text/plain")
```

**Key constraints:**
- Return `PlainTextResponse` with `media_type="text/plain"` (not JSON)
- Export endpoint returns markdown string directly
- POST endpoint (not GET) per REQUIREMENTS.md EXPORT-01

---

### `main.py` (extend) — app-factory, request-response

**Analog:** existing `main.py` (reuse and extend)

**Pattern** (initialize services, register routers):

```python
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from akc.core.config import settings
from akc.patterns.store import JsonlStore
from akc.recall.service import RecallService
from akc.recall.router import router as recall_router
from akc.stats.service import StatsService
from akc.stats.router import router as stats_router
from akc.export.service import ExportService
from akc.export.router import router as export_router

logger = logging.getLogger("akc")

# Global instances
store = JsonlStore(kb_dir=settings.akc_kb_dir)
recall_service = RecallService(store, memory_service_url=settings.memory_id)
stats_service = StatsService(store)
export_service = ExportService(store)

# Initialize routers with service instances
# (patterns: routers are initialized as modules, services injected here)
recall_router.recall_service = recall_service
stats_router.stats_service = stats_service
export_router.export_service = export_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    stats = await store.load_stats()
    logger.info("AKC starting — KB_DIR: %s, patterns: %d", settings.akc_kb_dir, stats["total_patterns"])
    yield
    # Shutdown
    logger.info("AKC shutting down")

app = FastAPI(lifespan=lifespan)

# Register routers
app.include_router(recall_router, prefix="/recall")
app.include_router(stats_router)
app.include_router(export_router)

@app.get("/health")
async def health():
    stats = await store.load_stats()
    return {"status": "ok", "pattern_count": stats["total_patterns"]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
```

**Key constraints:**
- Initialize all Phase 3 services in main.py
- Inject services into routers (module-level assignment)
- Register routers with `app.include_router()`
- Update lifespan log to use `stats["total_patterns"]` (extended field from Phase 1)

---

### `akc/patterns/store.py` (extend) — add Phase 3 methods

**Analog:** existing Phase 1 `store.py` (extend with new methods)

**Pattern** (STATS-01, STATS-02, STATS-03, RCL-04 fallback):

```python
# Add these methods to existing JsonlStore class in Phase 1

async def load_all(self, exclude_demoted: bool = False) -> list[dict]:
    """
    Load all patterns (unfiltered by tier).
    Used by export and stats aggregation.
    
    Args:
        exclude_demoted: if True, filter out tier="demoted"
    
    Returns:
        list of pattern dicts, sorted by confidence descending
    """
    async with self._lock:
        patterns_dict = await asyncio.to_thread(self._read_patterns_sync)
    
    patterns = list(patterns_dict.values())
    if exclude_demoted:
        patterns = [p for p in patterns if p.get("tier") != "demoted"]
    
    return sorted(patterns, key=lambda x: x.get("confidence", 0), reverse=True)

async def record_recall_query(self, result_count: int) -> None:
    """
    Record a /recall query for stats tracking.
    STATS-02: Track recall_hit_rate (queries with result_count > 0).
    
    Args:
        result_count: number of patterns returned to user
    """
    from datetime import datetime, timezone
    event = {
        "type": "recall_query",
        "result_count": result_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await asyncio.to_thread(self._append_history_sync, event)

async def load_stats(self) -> dict:
    """
    EXTEND existing Phase 1 load_stats() to include all STATS-01/02/03 fields.
    
    Returns:
    {
        "total_patterns": int,
        "by_tier": { "gold": int, "production": int, "experimental": int, "demoted": int },
        "avg_confidence": float,
        "top_tags": [tag1, tag2, ...],  # top 10 by frequency
        "recall_hit_rate": float,        # from confidence_history.jsonl
        "recently_promoted": [{ id, old_tier, new_tier, timestamp }, ...]
    }
    """
    async with self._lock:
        patterns = await asyncio.to_thread(self._read_patterns_sync)
    
    # Basic stats (existing Phase 1)
    total = len(patterns)
    by_tier = {"gold": 0, "production": 0, "experimental": 0, "demoted": 0}
    all_confidences = []
    all_tags = []
    
    for p in patterns.values():
        tier = p.get("tier", "experimental")
        by_tier[tier] = by_tier.get(tier, 0) + 1
        all_confidences.append(p.get("confidence", 0))
        all_tags.extend(p.get("tags", []))
    
    avg_confidence = (
        sum(all_confidences) / len(all_confidences) 
        if all_confidences else 0.0
    )
    
    # Top tags (STATS-01)
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(
        tag_counts.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10]
    top_tags = [tag for tag, count in top_tags]
    
    # Recall hit rate and recently promoted (STATS-02, STATS-03)
    recall_hit_rate, recently_promoted = await asyncio.to_thread(
        self._scan_history_sync
    )
    
    return {
        "total_patterns": total,
        "by_tier": by_tier,
        "avg_confidence": round(avg_confidence, 2),
        "top_tags": top_tags,
        "recall_hit_rate": recall_hit_rate,
        "recently_promoted": recently_promoted,
    }

def _scan_history_sync(self) -> tuple[float, list]:
    """
    Scan confidence_history.jsonl for:
    STATS-02: recall_hit_rate = queries_with_results / total_queries
    STATS-03: recently_promoted = last 5 tier upgrades
    
    Returns:
        (recall_hit_rate: float, recently_promoted: list[dict])
    """
    import json
    from datetime import datetime, timezone
    
    if not self._history_path.exists():
        return 0.0, []
    
    tier_rank = {"gold": 3, "production": 2, "experimental": 1, "demoted": 0}
    
    recall_queries = 0
    recall_hits = 0
    promotions = []
    
    with open(self._history_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            event = json.loads(line)
            event_type = event.get("type")
            
            if event_type == "recall_query":
                # STATS-02: track recall hit rate
                recall_queries += 1
                if event.get("result_count", 0) > 0:
                    recall_hits += 1
            
            elif event_type == "confidence_update":
                # STATS-03: track tier promotions
                old_tier = event.get("old_tier")
                new_tier = event.get("new_tier")
                if old_tier and new_tier:
                    old_rank = tier_rank.get(old_tier, 0)
                    new_rank = tier_rank.get(new_tier, 0)
                    if new_rank > old_rank:  # promotion only
                        promotions.append({
                            "id": event.get("pattern_id"),
                            "old_tier": old_tier,
                            "new_tier": new_tier,
                            "timestamp": event.get("timestamp"),
                        })
    
    hit_rate = recall_hits / recall_queries if recall_queries > 0 else 0.0
    recently_promoted = sorted(
        promotions,
        key=lambda x: x.get("timestamp", ""),
        reverse=True
    )[:5]
    
    return hit_rate, recently_promoted
```

**Key constraints:**
- `load_stats()` EXTEND existing Phase 1 method (add new fields, don't replace)
- `load_all()` used by export service (unfiltered patterns)
- `record_recall_query()` called by recall service after every query
- `_scan_history_sync()` is sync worker thread function (called via asyncio.to_thread)
- Handle missing history file gracefully (return 0.0, [])
- Event type must match Phase 2 (confirm event schema: "confidence_update", not "tier_change")

---

## Shared Patterns

### Pydantic Models for API Endpoints
**Source:** Phase 1 akc/patterns/models.py
**Apply to:** All `models.py` files in Phase 3
```python
from pydantic import BaseModel
from datetime import datetime

class MyRequest(BaseModel):
    field1: str
    field2: int | None = None

class MyResponse(BaseModel):
    id: str
    timestamp: datetime | None
```

### Router Setup with Service Injection
**Source:** Phase 1 main.py structure
**Apply to:** All `router.py` files
```python
from fastapi import APIRouter

router = APIRouter(prefix="/path", tags=["tag"])

# Service injected from main.py
service = None

@router.post("")
async def endpoint_name(request: RequestModel) -> ResponseModel:
    return await service.method(request)
```

### Async Orchestration + Error Handling
**Source:** Phase 1 akc/patterns/store.py
**Apply to:** All `service.py` files
```python
import logging

logger = logging.getLogger("akc.module")

class MyService:
    def __init__(self, store: JsonlStore):
        self._store = store
    
    async def operation(self):
        # Use asyncio.to_thread for sync I/O
        result = await asyncio.to_thread(self._sync_operation)
        logger.info(f"Operation completed: {result}")
        return result
```

### Timeout Handling for External Services
**Source:** RESEARCH.md Key Implementation Constraints (1)
**Apply to:** `akc/recall/search.py`
```python
import asyncio

async def external_call_with_fallback():
    try:
        async with asyncio.timeout(2.0):
            # HTTP call here
            pass
    except asyncio.TimeoutError:
        logger.warning("Timeout, falling back")
        return fallback_result
    except Exception as e:
        logger.warning(f"Error: {e}, falling back")
        return fallback_result
```

### Datetime — Timezone-Aware Only
**Source:** Phase 1 anti-pattern guide
**Apply to:** All files generating timestamps
```python
from datetime import datetime, timezone

# CORRECT
timestamp = datetime.now(timezone.utc).isoformat()

# WRONG — don't use
datetime.utcnow()
```

---

## Critical Implementation Order

### Execution sequence (dependencies):

1. **Extend Phase 1 store.py** first
   - Add `load_all()`, `record_recall_query()`, extend `load_stats()`, add `_scan_history_sync()`
   - These are used by all Phase 3 services

2. **Build akc/recall/** sub-package (in order)
   - models.py (RecallRequest, RecallResult, RecallResponse)
   - engine.py (filter_and_rank pure function)
   - search.py (semantic_search adapter)
   - service.py (RecallService orchestration)
   - router.py (POST /recall endpoint)

3. **Build akc/stats/** sub-package (in order)
   - models.py (StatsResponse, PromotionEvent)
   - service.py (StatsService)
   - router.py (GET /stats endpoint)

4. **Build akc/export/** sub-package (in order)
   - models.py (minimal, mostly pass-through)
   - service.py (ExportService markdown rendering)
   - router.py (POST /kb/export endpoint)

5. **Update main.py** last
   - Initialize all services
   - Inject into routers
   - Register routers with app

---

## Common Pitfalls

### Pitfall 1: Memory Service Timeout Breaks Request (RCL-04)

**What goes wrong:** asyncio.timeout() raises TimeoutError, request returns 500 instead of using fallback.

**Why it happens:** semantic_search() error not caught; exception propagates to FastAPI.

**How to avoid:** Wrap Memory Service call in try/except with asyncio.timeout inside. Return local patterns on ANY exception.

**Warning signs:** search.py imports http client directly without error handling; no fallback path.

---

### Pitfall 2: Demoted Patterns Returned When Confidence > Threshold (RCL-03)

**What goes wrong:** filter_and_rank() checks confidence before checking tier. Demoted at confidence 0.75 is returned.

**Why it happens:** Tier check runs after confidence threshold check.

**How to avoid:** Check `tier == "demoted"` BEFORE min_tier threshold. Demoted is a lock, not a score.

**Warning signs:** filter_and_rank() doesn't have early `if p.get("tier") == "demoted": continue`.

---

### Pitfall 3: Relevance Score Not Threaded Through (RCL-05)

**What goes wrong:** Memory Service returns relevance_score, but RecallResult is missing it or always None.

**Why it happens:** RecallResult model defined before understanding Memory Service response shape.

**How to avoid:** Define RecallResult with `relevance_score: float | None = None`. Set on Memory Service path; leave None on fallback.

**Warning signs:** RecallResult missing relevance_score field; semantic_search() doesn't return scored patterns.

---

### Pitfall 4: Event Type Mismatch in STATS-03 (STATS-03)

**What goes wrong:** Phase 3 scans history for "confidence_update" events, but Phase 2 records "tier_change". Recently promoted always empty.

**Why it happens:** Event type name inconsistency between Phase 2 (write path) and Phase 3 (read path).

**How to avoid:** Confirm event schema in Phase 2 plan. Use exact field names: `type`, `pattern_id`, `old_tier`, `new_tier`, `timestamp`.

**Warning signs:** Recently promoted list always empty even though promotions should exist.

---

### Pitfall 5: Tag Matching Is OR Not AND (RCL-01)

**What goes wrong:** Request tags=["python", "async"], pattern has ["python"]. Filter excludes it.

**Why it happens:** Implemented as AND (pattern must have ALL request tags) instead of OR.

**How to avoid:** Use `pattern_tags.intersection(request_tags)` — pattern needs ANY of the request tags.

**Warning signs:** filter_and_rank() uses `all(t in pattern_tags for t in request_tags)`.

---

### Pitfall 6: Export Includes Demoted Patterns (EXPORT-01)

**What goes wrong:** POST /kb/export renders all patterns, including demoted ones.

**Why it happens:** Export logic doesn't filter tier like recall does.

**How to avoid:** Explicitly filter `tier in ["gold", "production"]` in export service.

**Warning signs:** export_service.export_markdown() doesn't filter by tier.

---

### Pitfall 7: Stats Scans Entire History on Every Request (STATS-01, STATS-02, STATS-03)

**What goes wrong:** GET /stats takes 5+ seconds because it reads and parses all 100K lines of history on every request.

**Why it happens:** No caching; MVP scale is acceptable, but should be noted.

**How to avoid:** At MVP scale (< 10K patterns, < 100K history entries), this is acceptable. Document this. For v2, add TTL cache (60 seconds).

**Warning signs:** GET /stats latency grows linearly with history file size; no caching logic visible.

---

### Pitfall 8: Router Service Injection Not Initialized (RCL-01, STATS-01, EXPORT-01)

**What goes wrong:** Router tries to use service, but service is None. Endpoint returns 500.

**Why it happens:** main.py doesn't initialize and inject services into routers before registering.

**How to avoid:** In main.py, create service instances, assign to router module attributes, then include_router().

**Warning signs:** router.py has `service = None` and doesn't check if it's initialized.

---

### Pitfall 9: Markdown Export Doesn't Escape Special Characters (EXPORT-02)

**What goes wrong:** Pattern context contains `#` or `**`, markdown rendering breaks.

**Why it happens:** No escaping of special markdown characters in pattern content.

**How to avoid:** For v1 MVP, assume pattern content is plain text. For v2, add escaping if needed.

**Warning signs:** Pattern content with markdown special chars in export test.

---

## Integration Points with Phase 1 & 2

### From Phase 1 (Foundation)

- **Settings** (akc/core/config.py): Uses MEMORY_ID (required), AKC_KB_DIR — no changes
- **JsonlStore** (akc/patterns/store.py): Extends with `load_all()`, `record_recall_query()`, enhanced `load_stats()`, `_scan_history_sync()`
- **Pattern** (akc/patterns/models.py): Reads all fields — no modifications needed

### From Phase 2 (Write Path) — Deferred Risk

- **confidence_history.jsonl event structure**: Phase 3 assumes event fields: `{ type, pattern_id, old_tier, new_tier, result_count, timestamp }`
  - Type values: "recall_query", "confidence_update" (must match Phase 2)
  - **Mitigation:** Confirm event schema in Phase 2 plan before Phase 3 execution

### Dependency Graph

```
main.py
├── Phase 1: store.py (extended)
│   ├── models.py (Pattern)
│   ├── engine.py (apply_outcome)
│   └── config.py (Settings, MEMORY_ID)
│
├── akc/recall/router.py
│   └── akc/recall/service.py (RecallService)
│       ├── Phase 1: store.py (load_active)
│       ├── akc/recall/search.py (semantic_search adapter)
│       │   └── httpx (external HTTP library)
│       └── akc/recall/engine.py (filter_and_rank)
│
├── akc/stats/router.py
│   └── akc/stats/service.py (StatsService)
│       └── Phase 1: store.py (load_stats extended)
│           └── Phase 2: confidence_history.jsonl (deferred)
│
└── akc/export/router.py
    └── akc/export/service.py (ExportService)
        └── Phase 1: store.py (load_all)
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Memory Service endpoint at `https://agentbase.{memory_id}/api/semantic-search` | search.py pattern | URL must be empirically verified on Day 4; if different, adapter needs adjustment |
| A2 | Memory Service response includes `relevance_score` on each match | search.py pattern | Field name confirmed empirically Day 4; if absent or named differently, adapt RecallResult handling |
| A3 | asyncio.timeout() works in FastAPI request context | search.py constraint | Timeout behavior verified; should be safe but confirm with test |
| A4 | Phase 2 records events with type="confidence_update" | _scan_history_sync pattern | If Phase 2 uses "tier_change" or different field names, STATS-03 returns empty list |
| A5 | KB scale remains < 10K patterns, < 100K history entries | Pitfall 7 | Performance optimization deferred to v2 if scale exceeds assumptions |
| A6 | Tag matching is OR logic (pattern needs ANY of request tags) | filter_and_rank pattern | If AND logic is required instead, filter logic needs inversion |
| A7 | Export returns text/plain, not JSON | export/router.py pattern | Assumed from EXPORT-01; if JSON export needed, wrap markdown in object |

---

## Open Questions

1. **What is the exact Memory Service endpoint and response format?**
   - Recommendation: Code to a reasonable pattern (https://agentbase.{memory_id}/api/semantic-search), build behind adapter, confirm on Day 4.

2. **What event types and fields does Phase 2 record in confidence_history.jsonl?**
   - Recommendation: Phase 2 plan must specify exact event schema. Phase 3 assumes "confidence_update" type with `old_tier`, `new_tier` fields.

3. **Should export endpoint accept filters (e.g., /kb/export?tier=gold)?**
   - Recommendation: EXPORT-01 requires "all Gold + Production". Filters deferred to v2.

4. **Should recall_service track additional metrics (e.g., queries per tag)?**
   - Recommendation: MVP tracks only hit_rate. Additional metrics deferred to v2 (OBS-01).

---

## Metadata

**Analog search scope:** Phase 1 patterns and existing codebase in `/home/brewuser/work/clawthon/dl-starter-kit/`

**Files analyzed:** 
- Phase 1: akc/patterns/models.py, akc/patterns/store.py, akc/patterns/engine.py, main.py, akc/core/config.py
- RESEARCH.md (Phase 3 research)
- REQUIREMENTS.md (all v1 requirements)

**Pattern extraction date:** 2026-06-11

**Valid until:** 2026-07-11 (stable API contracts; confirm Memory Service details on Day 4)

**Build order:** Phases execute sequentially (1 → 2 → 3 → 4 → 5); Phase 3 depends on Phase 1 completion

**Current phase:** Phase 3 of 5 (Read Path)
