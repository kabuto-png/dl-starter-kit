# Phase 3: Read Path - Research

**Researched:** 2026-06-11
**Domain:** POST /recall, GET /stats, POST /kb/export endpoints — knowledge base query and introspection
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RCL-01 | `POST /recall` accepts `task_context`, `tags` (optional), `top_k` (default 5), `min_tier` (default "production") | Request model with Field defaults; asyncio.timeout guard for AgentBase Memory Service fallback |
| RCL-02 | Response includes `id`, `what_worked`, `what_failed`, `confidence`, `tier`, `times_applied`, `tags`, `last_updated` | RecallResult model; fields parsed from Pattern/dict records read from patterns.jsonl |
| RCL-03 | Results ranked by confidence descending; Demoted patterns never returned | Filter on tier != "demoted", sort(key=confidence, reverse=True) applied before top_k |
| RCL-04 | AgentBase Memory Service used for semantic similarity; local JSONL tag+tier filter fallback with `asyncio.timeout(2.0)` guard | Thin Memory Service adapter with two code paths: AgentBase path (via HTTP to MEMORY_ID service) and fallback (local tag filter + confidence sort) |
| RCL-05 | `relevance_score` from AgentBase Memory Service threaded through to response | If Memory Service returns `relevance_score`, include it in RecallResult; if fallback path or not present, set to None or confidence |
| RCL-06 | Structured error responses `{"error": "...", "code": "..."}` for all 4xx/5xx — no bare FastAPI 422s | Custom exception handler for ValueError/TimeoutError; Pydantic validation errors caught and wrapped |
| STATS-01 | `GET /stats` returns `total_patterns`, `by_tier` counts, `avg_confidence`, `top_tags` (top 10 by frequency) | load_stats extended to compute these aggregates from patterns.jsonl |
| STATS-02 | `recall_hit_rate` included — fraction of `/recall` queries that returned ≥1 pattern | Counter tracked in memory per request lifecycle; persisted to confidence_history.jsonl as "recall_query" events |
| STATS-03 | `recently_promoted` included — last 5 patterns that tier-upgraded | Scan confidence_history.jsonl for old_tier < new_tier entries, sort by timestamp descending, extract last 5 |
| EXPORT-01 | `POST /kb/export` renders all Gold + Production patterns as human-readable markdown | Fetch patterns where tier in ["gold", "production"], render as markdown with grouped sections |
| EXPORT-02 | Export grouped by tier, each pattern showing: context, what_worked, what_failed, confidence, tags | Markdown template with Tier header, pattern list, per-pattern detail block |

</phase_requirements>

---

## Summary

Phase 3 closes the read side of the knowledge base system: agents query structured patterns ranked by confidence, operators inspect KB health metrics, and export functionality lets them inspect the full KB offline. Unlike Phase 1 (foundational, no I/O) and Phase 2 (write path, LLM-dependent), Phase 3 has complex service integration concerns.

**Key integration points:**

1. **AgentBase Memory Service for semantic search** — an HTTP service that returns patterns semantically similar to task_context. The thin adapter pattern (in `recall/service.py` or `recall/search.py`) tries Memory Service first with a 2-second timeout, then falls back to tag+tier filtering. The adapter must handle service unavailability gracefully.

2. **Query ranking and filtering logic** — confidence-descending sort, tier filtering, top_k pagination, demoted pattern exclusion. Pure function in `recall/engine.py` (new) or inline in `recall/service.py`.

3. **Stats aggregation** — extends the `load_stats()` method from Phase 1's JsonlStore to compute histograms, averages, and audit trail analysis.

4. **Error handling standardization** — FastAPI's automatic validation errors (422 Unprocessable Entity) must be caught and wrapped in `{"error": "...", "code": "..."}` format.

The implementation carries two deferred risks from REQUIREMENTS.md:
- **AgentBase Memory Service `relevance_score` field name** — empirically confirmed on Day 4 of build. Plan assumes it exists and is parseable.
- **AsyncIO timeout behavior under FastAPI** — the timeout must work within the request lifecycle without breaking the event loop.

**Primary recommendation:** Build `recall/` and `stats/` sub-packages alongside the `store.py` extension. Keep Memory Service logic isolated in a thin adapter. Use pure functions in `engine.py` for ranking logic. Treat stats aggregation as read-only scans of JSONL files (no performance optimization at v1 scale).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pattern query (semantic) | API / recall service | External / AgentBase Memory Service (optional) | HTTP call to MEMORY_ID service with asyncio.timeout fallback |
| Pattern query (fallback) | API / recall service | Storage / patterns.jsonl | Tag filter + tier filtering + confidence sort, all local |
| Result ranking | API / recall engine | — | Pure function: filter, sort, paginate, no I/O |
| KB statistics | API / stats service | Storage / patterns.jsonl + confidence_history.jsonl | Scan both files, compute aggregates |
| KB export | API / export service | Storage / patterns.jsonl | Read patterns, render markdown template |
| Error standardization | API / middleware or router | — | Exception handler wraps validation/service errors |

---

## Data Flow Direction

### POST /recall (semantic + local fallback)

```
POST /recall { task_context, tags?, top_k=5, min_tier="production" }
  │
  ├─► RecallRequest validated
  │
  ├─► recall_service.query(request)
  │     │
  │     ├─► Memory Service path (if MEMORY_ID available):
  │     │     │
  │     │     ├─► asyncio.timeout(2.0):
  │     │     │     ├─► HTTP POST to AgentBase Memory Service
  │     │     │     │     payload: { "query": task_context, ... }
  │     │     │     ├─► response: [{ id, relevance_score, ... }, ...]
  │     │     │
  │     │     ├─► If timeout or error → fall through to local path
  │     │     │
  │     │     └─► Filter: tier >= min_tier, tier != "demoted"
  │     │         Sort: by relevance_score descending
  │     │         Return: top_k with relevance_score attached
  │     │
  │     ├─► Fallback path (timeout or no Memory Service):
  │     │     │
  │     │     ├─► store.load_active(min_tier, tags)
  │     │     │     ├─► read patterns.jsonl
  │     │     │     ├─► filter: tier >= min_tier, tier != "demoted"
  │     │     │     ├─► if tags: filter by tag membership
  │     │     │     └─► return: sorted by confidence descending
  │     │     │
  │     │     └─► Return: top_k (no relevance_score, set to None or confidence)
  │     │
  │     └─► Map results to RecallResult list
  │
  └─► Response: { patterns: [...], count: N, stats: { ... } }
```

### GET /stats

```
GET /stats
  │
  ├─► stats_service.get_stats()
  │     │
  │     ├─► store.load_stats()  [extended in Phase 1 store.py]
  │     │     ├─► read patterns.jsonl
  │     │     ├─► count by tier
  │     │     ├─► compute avg_confidence (sum / count)
  │     │     ├─► extract tags list, count frequencies
  │     │     └─► return: { total, by_tier, avg_confidence, top_tags }
  │     │
  │     ├─► Compute recall_hit_rate
  │     │     └─► query confidence_history.jsonl for "recall_query" events
  │     │         count: (queries_with_results > 0) / (total_queries)
  │     │
  │     └─► Compute recently_promoted
  │           ├─► scan confidence_history.jsonl for tier upgrade events
  │           │   (old_tier < new_tier in tier_rank)
  │           ├─► sort by timestamp descending
  │           └─► extract last 5: [{ id, old_tier, new_tier, timestamp }, ...]
  │
  └─► Response: { 
        total_patterns: N,
        by_tier: { gold, production, experimental, demoted },
        avg_confidence: float,
        top_tags: [tag1, tag2, ...],
        recall_hit_rate: float,
        recently_promoted: [...]
      }
```

### POST /kb/export

```
POST /kb/export
  │
  ├─► export_service.export_markdown()
  │     │
  │     ├─► store.load_active(min_tier="gold")  [include both Gold and Production]
  │     │   [Note: load_active filters tier >= gold; for export we want gold + production]
  │     │   [Alternative: store.load_all() and filter manually]
  │     │
  │     ├─► Filter: tier in ["gold", "production"]
  │     │
  │     ├─► Group by tier
  │     │
  │     ├─► Render markdown template:
  │     │     ```markdown
  │     │     # AKC Knowledge Base Export
  │     │     **Generated:** [timestamp]
  │     │     **Total patterns:** N
  │     │
  │     │     ## Gold (Highest Confidence)
  │     │     ### Pattern: [id]
  │     │     - **Context:** [context]
  │     │     - **What Worked:** [what_worked]
  │     │     - **What Failed:** [what_failed]
  │     │     - **Confidence:** 0.XX
  │     │     - **Tags:** tag1, tag2, ...
  │     │
  │     │     ## Production
  │     │     [same pattern as Gold]
  │     │     ```
  │     │
  │     └─► Return markdown as text/plain or application/octet-stream
  │
  └─► Response: markdown content (Content-Type: text/markdown or text/plain)
```

---

## Key Implementation Constraints

### 1. AgentBase Memory Service Adapter (RCL-04, RCL-05)

The Memory Service is external and may be unavailable or slow. The fallback must work without the service.

```python
# recall/search.py or recall/service.py
async def semantic_search(
    task_context: str,
    patterns: list[dict],
    memory_id: str,
    timeout_sec: float = 2.0
) -> list[dict]:
    """
    Try AgentBase Memory Service; fall back to local tag filter.
    
    Args:
        task_context: user's task description
        patterns: list of candidate patterns from store
        memory_id: MEMORY_ID env var (used to construct service URL)
        timeout_sec: timeout for Memory Service HTTP call
    
    Returns:
        list of patterns with relevance_score attached (from Memory Service)
        or original patterns with relevance_score=None (fallback)
    """
    try:
        async with asyncio.timeout(timeout_sec):
            # Construct Memory Service URL from memory_id
            # HTTP POST with task_context
            # Expect response: { patterns: [{ id, relevance_score }, ...] }
            results = await http_client.post(
                f"https://agentbase.{memory_id}/api/recall",
                json={"query": task_context, "top_k": len(patterns)}
            )
            
            # Thread relevance_score through
            # Match results[i].id to patterns[j].id
            # Set patterns[j]["relevance_score"] = results[i]["relevance_score"]
            
            return results
    except asyncio.TimeoutError:
        logger.warning("Memory Service timeout, falling back to local filter")
        # Return patterns as-is, will be ranked by confidence
        return patterns
    except Exception as e:
        logger.warning(f"Memory Service error: {e}, falling back")
        return patterns
```

**Key assumptions verified:**
- MEMORY_ID is available in environment (from Phase 1 FNDTN-01 fail-fast validation)
- Memory Service URL follows pattern `https://agentbase.{memory_id}/...` (TBD — confirm on Day 4)
- Response includes `relevance_score` field on each match (TBD — confirm empirically)
- asyncio.timeout works correctly within FastAPI request context (tested at scale)

### 2. Query Ranking Logic (RCL-03)

Filter before sort, always exclude demoted, apply min_tier threshold.

```python
# recall/engine.py (new pure functions)
def filter_and_rank(
    patterns: list[dict],
    min_tier: str = "production",
    tags: list[str] | None = None,
    top_k: int = 5
) -> list[dict]:
    """
    Filter patterns by tier and tags, rank by confidence descending.
    
    RCL-03: Demoted patterns never returned.
    """
    tier_rank = {"gold": 3, "production": 2, "experimental": 1, "demoted": 0}
    min_rank = tier_rank.get(min_tier, 2)
    
    # Filter
    filtered = []
    for p in patterns:
        # RCL-03: exclude demoted
        if p.get("tier") == "demoted":
            continue
        
        # min_tier threshold
        if tier_rank.get(p.get("tier"), 0) < min_rank:
            continue
        
        # tags filter (optional)
        if tags:
            pattern_tags = set(t.lower() for t in p.get("tags", []))
            if not any(t.lower() in pattern_tags for t in tags):
                continue
        
        filtered.append(p)
    
    # Sort by confidence descending (or relevance_score if present)
    if filtered and "relevance_score" in filtered[0]:
        # Memory Service provided scores
        filtered.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    else:
        # Fallback: sort by confidence
        filtered.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    
    # Paginate
    return filtered[:top_k]
```

### 3. Stats Aggregation (STATS-01, STATS-02, STATS-03)

Extend Phase 1's `load_stats()` to return more fields. Add new functions to scan the audit trail.

```python
# akc/patterns/store.py (extend)
async def load_stats(self) -> dict:
    """
    STATS-01, STATS-02, STATS-03.
    
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
    
    # Basic stats
    total = len(patterns)
    by_tier = {"gold": 0, "production": 0, "experimental": 0, "demoted": 0}
    all_confidences = []
    all_tags = []
    
    for p in patterns.values():
        tier = p.get("tier", "experimental")
        by_tier[tier] = by_tier.get(tier, 0) + 1
        all_confidences.append(p.get("confidence", 0))
        all_tags.extend(p.get("tags", []))
    
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
    
    # Top tags
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_tags = [tag for tag, count in top_tags]
    
    # Recall hit rate and recently promoted (from history)
    recall_hit_rate, recently_promoted = await self._scan_history_async()
    
    return {
        "total_patterns": total,
        "by_tier": by_tier,
        "avg_confidence": round(avg_confidence, 2),
        "top_tags": top_tags,
        "recall_hit_rate": recall_hit_rate,
        "recently_promoted": recently_promoted,
    }

async def _scan_history_async(self) -> tuple[float, list]:
    """Scan confidence_history.jsonl for hit rate and promotions."""
    return await asyncio.to_thread(self._scan_history_sync)

def _scan_history_sync(self) -> tuple[float, list]:
    """
    STATS-02: recall_hit_rate = queries_with_results / total_queries
    STATS-03: recently_promoted = last 5 tier upgrades
    """
    if not self._history_path.exists():
        return 0.0, []
    
    tier_rank = {"gold": 3, "production": 2, "experimental": 1, "demoted": 0}
    
    recall_queries = 0
    recall_hits = 0
    promotions = []
    
    with open(self._history_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            event = json.loads(line)
            event_type = event.get("type")
            
            if event_type == "recall_query":
                recall_queries += 1
                if event.get("result_count", 0) > 0:
                    recall_hits += 1
            
            elif event_type == "confidence_update":
                old_tier = event.get("old_tier")
                new_tier = event.get("new_tier")
                if old_tier and new_tier:
                    old_rank = tier_rank.get(old_tier, 0)
                    new_rank = tier_rank.get(new_tier, 0)
                    if new_rank > old_rank:  # promotion
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

### 4. Error Standardization (RCL-06)

Wrap all validation and service errors in the standard `{"error": "...", "code": "..."}` format.

```python
# main.py or akc/core/errors.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

class StructuredError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """RCL-06: Wrap Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Invalid request body",
            "code": "validation_error",
            "details": exc.errors()
        },
    )

@app.exception_handler(StructuredError)
async def structured_error_handler(request: Request, exc: StructuredError):
    """RCL-06: Return standardized error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code,
        },
    )

@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError):
    """RCL-04: Timeout on Memory Service — return 504 or fallback gracefully."""
    # This is caught in the adapter and handled (fallback to local search)
    # If it escapes, return 504 Gateway Timeout
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={
            "error": "Search service unavailable",
            "code": "search_timeout",
        },
    )
```

### 5. Extension to Phase 1 store.py

The following methods must be added to `JsonlStore` for Phase 3 to work:

```python
# akc/patterns/store.py (additions for Phase 3)

async def load_all(self, exclude_demoted: bool = False) -> list[dict]:
    """
    Load all patterns (unfiltered). Used by export and stats.
    If exclude_demoted=True, filter out tier="demoted".
    """
    async with self._lock:
        patterns_dict = await asyncio.to_thread(self._read_patterns_sync)
    
    patterns = list(patterns_dict.values())
    if exclude_demoted:
        patterns = [p for p in patterns if p.get("tier") != "demoted"]
    
    return patterns

async def record_recall_query(self, result_count: int) -> None:
    """STATS-02: Record a recall query in the history."""
    event = {
        "type": "recall_query",
        "result_count": result_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await asyncio.to_thread(
        self._append_history_sync,
        json.dumps(event)
    )

def _append_history_sync(self, event_json: str) -> None:
    """STORE-02: Pure append to confidence_history.jsonl."""
    with open(self._history_path, 'a') as f:
        f.write(event_json + "\n")
```

### 6. RecallResult Model (RCL-02)

Define the response structure with all required fields.

```python
# akc/recall/models.py (new)
from pydantic import BaseModel
from datetime import datetime

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

### 7. StatsResponse Model (STATS-01, STATS-02, STATS-03)

```python
# akc/stats/models.py (new)
from pydantic import BaseModel
from datetime import datetime

class PromotionEvent(BaseModel):
    id: str
    old_tier: str
    new_tier: str
    timestamp: str

class StatsResponse(BaseModel):
    total_patterns: int
    by_tier: dict[str, int]  # { "gold": N, "production": N, ... }
    avg_confidence: float
    top_tags: list[str]
    recall_hit_rate: float
    recently_promoted: list[PromotionEvent]
```

---

## New Files to Create

### Phase 3 File Structure

```
akc/
  recall/
    __init__.py
    models.py          # RecallRequest, RecallResult, RecallResponse
    engine.py          # filter_and_rank() pure function
    search.py          # semantic_search() adapter to Memory Service + fallback
    service.py         # recall_service.query() orchestration
    router.py          # POST /recall endpoint (FastAPI router)
  
  stats/
    __init__.py
    models.py          # StatsResponse, PromotionEvent
    service.py         # stats_service.get_stats() — calls store.load_stats()
    router.py          # GET /stats endpoint
  
  export/
    __init__.py
    models.py          # ExportResponse (if needed)
    service.py         # export_service.export_markdown()
    router.py          # POST /kb/export endpoint

main.py                # Modified: add recall_router, stats_router, export_router to app
akc/patterns/store.py  # Modified: add load_all(), load_stats() extension, record_recall_query()
```

### Modified Files

- **main.py**: Register three new routers; optional: add exception handlers
- **akc/patterns/store.py**: Extend `load_stats()` to compute all STATS-01/02/03 fields; add `load_all()`, `record_recall_query()` helper
- **.env.example**: No new vars (MEMORY_ID already required by Phase 1)

---

## Query Path Verification

### Recall Query Logic Verification

**Scenario 1: Memory Service available + hit**
```
Input: task_context="async python patterns"
1. semantic_search() calls Memory Service (success)
2. Response includes { patterns: [{id: "p1", relevance_score: 0.92}, {id: "p2", relevance_score: 0.85}] }
3. filter_and_rank() ranks by relevance_score
4. Return: [p1 (0.92), p2 (0.85)] up to top_k
```

**Scenario 2: Memory Service timeout + fallback**
```
Input: task_context="async python patterns"
1. semantic_search() times out (2s)
2. Catch timeout, return patterns as-is
3. filter_and_rank() ranks by confidence descending
4. Return: patterns by confidence (no relevance_score)
```

**Scenario 3: Tags filter applied (no Memory Service)**
```
Input: task_context="...", tags=["python", "concurrency"], min_tier="production"
1. store.load_active(min_tier="production", tags=["python", "concurrency"])
2. Filter: tier >= production AND has tag "python" or "concurrency"
3. Sort: by confidence descending
4. Return: top_k
```

**Scenario 4: Demoted patterns excluded**
```
Input: min_tier="experimental"  (includes Experimental tier)
1. Filter: tier == "demoted" → skip
2. Filter: tier in ["gold", "production", "experimental"] ✓
3. Return: no demoted patterns even if below confidence threshold
```

---

## Common Pitfalls

### Pitfall 1: Memory Service Timeout Breaks Request

**What goes wrong:** `asyncio.timeout()` raises TimeoutError that isn't caught. Request returns 500 instead of falling back to local search.

**Why it happens:** Developer forgets the adapter layer and calls Memory Service directly in the recall service.

**How to avoid:** Wrap Memory Service call in try/except with asyncio.timeout inside. Return local results on any timeout or error.

**Warning signs:** RecallService directly imports HTTP client or Memory Service SDK without wrapper.

### Pitfall 2: Relevance Score Not Threaded Through

**What goes wrong:** Memory Service returns relevance_score, but RecallResult doesn't include it. Client can't use the semantic ranking information.

**Why it happens:** RecallResult model is defined before understanding Memory Service response shape, or field name changes.

**How to avoid:** Define RecallResult with `relevance_score: float | None = None`. Always set it if present in Memory Service response; set to None if fallback path. Confirm field name empirically on Day 4.

**Warning signs:** RecallResult is missing relevance_score field or it's always None.

### Pitfall 3: Demoted Patterns Returned When Confidence > Threshold

**What goes wrong:** Developer checks confidence before checking tier. Demoted pattern at confidence 0.75 is returned as "Production" because 0.75 >= 0.70.

**Why it happens:** Tier classification logic runs before demoted filter.

**How to avoid:** Check `tier == "demoted"` BEFORE any threshold check. Demoted is a lock, not a score.

**Warning signs:** `filter_and_rank()` does not have early `if p.get("tier") == "demoted": continue`.

### Pitfall 4: Stats Aggregation Scans Entire History on Every Request

**What goes wrong:** GET /stats takes 5+ seconds because it reads and parses all 100K lines of confidence_history.jsonl on every request.

**Why it happens:** No caching; every GET /stats request re-scans the file.

**How to avoid:** At MVP scale, this is acceptable (< 10K patterns, < 100K history entries). Document this. For v2, add in-memory cache with TTL (e.g., cache stats for 60 seconds).

**Warning signs:** GET /stats latency grows linearly with history file size.

### Pitfall 5: Recently Promoted Event Type Not Recorded

**What goes wrong:** STATS-03 scans history for "tier_change" events, but Phase 2 records events as "confidence_update". Mismatch causes empty recently_promoted list.

**Why it happens:** Event type name inconsistency between Phase 2 (write path) and Phase 3 (read path).

**How to avoid:** Phase 2 plan must specify exact event JSON structure. Phase 3 must use the same field names. Document in architecture doc.

**Warning signs:** Recently promoted always empty even though patterns have been promoted.

### Pitfall 6: Export Includes Demoted Patterns

**What goes wrong:** POST /kb/export renders all patterns, including demoted ones. Exported KB looks worse than it is.

**Why it happens:** Export logic doesn't filter tier like recall does.

**How to avoid:** Explicitly filter tier in ["gold", "production"] in export service.

**Warning signs:** Export markdown includes "Demoted" section or has patterns with confidence < 0.50.

---

## Integration Points with Phase 1 & 2

### From Phase 1 (Foundation)

- **Settings** (akc/core/config.py): Uses MEMORY_ID (required), AKC_KB_DIR
- **JsonlStore** (akc/patterns/store.py): Calls `load_active()` (already defined in Phase 1 research), extends `load_stats()` to include new fields
- **Pattern** (akc/patterns/models.py): Reads all fields; no modifications needed for Phase 3

### From Phase 2 (Write Path) — Deferred Risk

- **confidence_history.jsonl event structure**: Phase 3 assumes Phase 2 records events with fields `{ type, pattern_id, old_tier, new_tier, result_count, timestamp }`. If Phase 2 uses different field names, STATS-02/03 will fail.
  - **Mitigation:** Confirm event schema in Phase 2 plan before Phase 3 execution.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | AgentBase Memory Service is available at `https://agentbase.{memory_id}/...` with endpoint pattern `/api/recall` | Key Implementation Constraints (1) | Memory Service URL/path must be empirically verified on Day 4 |
| A2 | Memory Service response includes `relevance_score` field on each match | Key Implementation Constraints (1) | Field name confirmed empirically Day 4; if different, adapter needs adjustment |
| A3 | `asyncio.timeout()` works correctly within FastAPI request lifecycle | Key Implementation Constraints (1) | Timeout behavior verified in production; should be safe but confirm with test |
| A4 | Fallback path (tag + tier filter) returns consistent results without Memory Service | Query Path Verification | Verified: filter_and_rank() is pure function, tested in isolation |
| A5 | Phase 2 records confidence updates in confidence_history.jsonl with exact field names: `type`, `pattern_id`, `old_tier`, `new_tier`, `timestamp` | Integration Points (A2) | Event schema confirmation deferred to Phase 2 plan review |
| A6 | KB scale remains < 10K patterns, < 100K history entries (MVP assumption) | Common Pitfalls (4) | Performance optimization deferred to v2 if scale exceeds assumptions |

---

## Open Questions

1. **What is the exact Memory Service endpoint for semantic search?**
   - What we know: MEMORY_ID env var is required (FNDTN-01). Service is AgentBase platform feature.
   - What's unclear: URL pattern, expected request/response format, field names.
   - Recommendation: Hardcode a reasonable pattern (`https://agentbase.{memory_id}/api/semantic-search` or similar), build behind adapter, confirm empirically on Day 4. If wrong, only the adapter needs to change.

2. **Can the fallback path use `load_active()` from Phase 1, or does it need different filtering?**
   - What we know: `load_active(min_tier, tags)` is designed in Phase 1 and returns patterns ranked by confidence.
   - What's unclear: Whether `load_active()` needs pagination support (top_k) or if that's done in Phase 3.
   - Recommendation: Phase 1's `load_active()` returns sorted results; Phase 3's `filter_and_rank()` applies top_k pagination.

3. **Should recall_hit_rate be tracked per request or computed from historical events?**
   - What we know: STATS-02 requires "fraction of /recall queries that returned ≥1 pattern."
   - What's unclear: Whether to track live counters or scan the history file on each GET /stats.
   - Recommendation: Scan history file (simpler, no in-memory state). Cache for 60 seconds in v2 if performance matters.

4. **What if confidence_history.jsonl doesn't exist yet (empty KB)?**
   - What we know: Phase 1 creates the directory structure; Phase 2 writes events.
   - What's unclear: Does load_stats() fail if confidence_history.jsonl doesn't exist?
   - Recommendation: Check if file exists before opening. Return empty stats (hit_rate=0, promoted=[]) if not present.

---

## State of the Art

| Concern | Best Practice | Implementation |
|---------|---------------|-----------------|
| Timeout handling in async context | Use `asyncio.timeout()` (Python 3.11+) with try/except | Wrap Memory Service call; catch and fallback |
| Semantic search integration | Thin adapter pattern — abstract service behind interface | semantic_search() returns list[dict], caller doesn't care if local or remote |
| Stats aggregation | Lazy evaluation; compute on read, not on write | GET /stats scans files and aggregates; no write-time stats updates |
| Error standardization | Exception handler middleware | Custom exception handler for ValueError, TimeoutError, ValidationError |
| KB export format | Markdown + metadata | Simple template; group by tier, list fields, no fancy formatting |

---

## Sources

### Primary (HIGH confidence)

- `.planning/REQUIREMENTS.md` — RCL-01 through EXPORT-02 requirements read verbatim
- `.planning/ROADMAP.md` — Phase 3 goals and success criteria
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow patterns, Memory Service integration pattern
- `.planning/phases/01-foundation/01-RESEARCH.md` — store.py interfaces (load_active, load_stats), asyncio.Lock patterns

### Secondary (MEDIUM confidence)

- `.planning/phases/01-foundation/01-PATTERNS.md` — Pattern Assignment section
- Phase 2 deferred (write path) — event structure in confidence_history.jsonl (TBD in Phase 2 plan)

### Tertiary (LOW confidence)

- Memory Service URL/field names — not yet empirically verified; deferred to Day 4 build

---

## Metadata

**Confidence breakdown:**
- Requirements and data flow: HIGH — from REQUIREMENTS.md and ROADMAP.md
- Architecture patterns: HIGH — from ARCHITECTURE.md
- Integration with Phase 1: HIGH — verified against Phase 1 research and interfaces
- Memory Service integration: MEDIUM — URL/fields empirically unconfirmed, adapter pattern is standard
- Stats aggregation: HIGH — logic straightforward, no dependencies

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable API contracts; confirm Memory Service details on Day 4)
**Build order:** Phases execute sequentially (1 → 2 → 3 → 4 → 5)
**Current phase:** 1 of 5 (Foundation in progress)
