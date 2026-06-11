# Architecture Patterns

**Domain:** Self-improving knowledge API service (FastAPI + JSONL + LLM distillation)
**Researched:** 2026-06-11
**Reference codebase examined:** `/home/brewuser/akc-service/akc_service/learning_engine.py`, `safety_engine.py`

---

## Recommended Architecture

The feature-first layout in `docs/architecture_v1.md` is correct. The research below fills in the
implementation details that the blueprint leaves unspecified — specifically the six questions asked.

```
main.py
  lifespan() ──► app.state.store   (JsonlStore, singleton)
              ──► app.state.llm    (AsyncOpenAI client, singleton)
              ──► app.state.lock   (asyncio.Lock, singleton — shared by store)

  recall/router  ──► recall/service  ──► patterns/store (read-only path)
  remember/router──► remember/service──► remember/distiller
                                     ──► patterns/store (write path, lock-guarded)
                                     ──► patterns/engine
  stats/router   ──► stats/service   ──► patterns/store (read-only path)
  export/router  ──► export/service  ──► patterns/store (read-only path)

patterns/
  models.py   — Pattern dataclass, Tier enum, Beta confidence model
  store.py    — JSONL read/write, dedup on read, asyncio.Lock for writes
  engine.py   — confidence update (Beta), tier classification, guardrails
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Notes |
|-----------|---------------|-------------------|-------|
| `patterns/store.py` | JSONL I/O — load, append, atomic save | Nobody imports from it except features via `Depends()` | The only file that touches the filesystem |
| `patterns/engine.py` | Confidence math (Beta), tier logic, guardrails | `patterns/models.py` only | Pure functions — no I/O |
| `patterns/models.py` | Pattern dataclass, Tier enum | Imported by all | Stable; changes break everything |
| `core/deps.py` | `get_store()`, `get_llm()` returning `app.state.*` | Called via `Depends()` from routers | Never import directly; always go through Depends |
| `remember/distiller.py` | Qwen call: raw text → Pattern dict | `core/deps.py` for LLM client | Isolated so LLM can be swapped without touching service |
| `remember/service.py` | Orchestrate: distill → store → update confidence | distiller, store, engine | This is the only place the write-path sequence lives |
| `main.py` | App factory, lifespan, router registration | Everything | Thin — no business logic here |

**Hard dependency rule:** Features import from `patterns/` and `core/` only. Features never import from each other. This is not style guidance — it is the boundary that keeps features independently testable.

---

## Data Flow Direction

```
POST /remember (write path):
  Request → router → BackgroundTask enqueued → 202 returned immediately
  BackgroundTask:
    distiller.extract(task_context, what_happened, outcome)
      └── Qwen API → structured Pattern JSON
    store.acquire_lock()                    ← exclusive asyncio.Lock
      store.load_all() → dict[id → Pattern] ← read full file
      engine.update_or_create(pattern)      ← pure function, no I/O
      store.atomic_save(patterns)           ← write tmp → rename
    store.release_lock()
    store.append_history(confidence_entry)  ← lock not needed (append-only)

POST /recall (read path):
  Request → router → service.query()
    store.load_active(min_tier, tags)       ← no lock needed (reads are safe)
    AgentBase Memory Service (semantic similarity, optional)
    rank by confidence → return top_k
```

Read path is lock-free. Lock is held only during the write cycle in `/remember`. Because
FastAPI runs a single asyncio event loop per worker process and BackgroundTask runs in the
same event loop, one `asyncio.Lock` is sufficient for single-container deployment.

---

## Question 1: Confidence Scoring Under Concurrent Updates

**Pattern: asyncio.Lock wrapping read-modify-write in store.py**

The reference codebase (`learning_engine.py:update_confidence`) uses:
```python
patterns = load_all_patterns()        # read
pattern["confidence"] = new_value     # modify
save_all_patterns(patterns)           # atomic tmp-rename write
```

This is a **read-modify-write race**. Two concurrent `/remember` calls can both read the same
state, both compute updates, and the second write silently discards the first update. The tmp-rename
trick makes individual writes atomic but does not make the read-modify-write sequence atomic.

**Fix: single asyncio.Lock on the store, acquired before load, released after save.**

```python
# patterns/store.py
class JsonlStore:
    def __init__(self, kb_dir: Path):
        self._patterns_path = kb_dir / "patterns.jsonl"
        self._history_path = kb_dir / "confidence_history.jsonl"
        self._write_lock = asyncio.Lock()   # created once in __init__

    async def update_pattern(self, pattern_id: str, outcome: str) -> None:
        async with self._write_lock:             # exclusive
            patterns = self._load_all_sync()     # read inside lock
            engine.apply_outcome(patterns, pattern_id, outcome)  # mutate
            self._atomic_save_sync(patterns)     # write inside lock
        # history append is outside lock — append() is O(1) and safe
        self._append_history_sync(...)
```

The lock lives on the store instance, which is a singleton on `app.state`. All requests
share one store → one lock → safe serialization of writes. No external infrastructure needed.

**Confidence level: HIGH** — asyncio.Lock is the standard solution for single-process asyncio
concurrent mutation. Verified against FastAPI dependency injection patterns and asyncio docs.

---

## Question 2: JSONL Deduplication — Last-Write-Wins vs Versioning

**Pattern for patterns.jsonl: last-write-wins with read-time deduplication**

JSONL append-only means you can have multiple records with the same `id`. The deduplication
strategy determines which one wins on read.

**Use last-write-wins (not versioning) for the confidence store:**

```python
def _load_all_sync(self) -> dict[str, dict]:
    """Returns dict keyed by id — later entries overwrite earlier ones."""
    patterns: dict[str, dict] = {}
    with open(self._patterns_path, "r") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                patterns[obj["id"]] = obj   # last entry wins
    return patterns
```

Why last-write-wins over versioning:
- Versioning requires reading the full version history on every query — O(n·versions) read
- For a confidence score that is updated frequently, versioning adds complexity with no benefit
  (the PRD already has `confidence_history.jsonl` as the separate audit trail)
- Last-write-wins + append-only gives you: simple reads, crash-safe appends, and the audit
  trail is in `confidence_history.jsonl` where each entry records old/new values

**Use explicit versioning only for pattern content changes** (what_worked, what_failed text),
not for confidence updates. The reference codebase's `version_pattern()` is the right model
for that — snapshot-on-content-change, not on every confidence tick.

**File compaction:** At MVP scale (< 10K patterns, < 100K history entries), never compact.
The atomic-save path for patterns.jsonl already rewrites the file on every write, so it
stays compact automatically. `confidence_history.jsonl` is append-only forever — it is the
audit trail and should not be compacted.

**Confidence level: HIGH** — deduplication strategy follows standard append-only log patterns.

---

## Question 3: Background Distillation — BackgroundTask vs queue vs asyncio.create_task

**Use FastAPI BackgroundTask for MVP. Know its failure mode. Mitigate with a wrapper.**

BackgroundTask is correct for AKC's `/remember` because:
- The Qwen call is the only work — no retries needed at hackathon scale
- No persistence required — if the container restarts mid-distillation, the caller gets a 202
  and nothing was promised
- No external broker infra (Redis, RabbitMQ) needed
- Matches the 202 Accepted / fire-and-forget contract in the PRD

**The critical failure mode to mitigate:** BackgroundTask exceptions are silently swallowed.
A Qwen API error (network timeout, malformed response) fails without any log entry unless
you explicitly catch it.

```python
# remember/service.py
async def _distill_and_store(request: RememberRequest, store: JsonlStore, llm: AsyncOpenAI):
    try:
        pattern = await distiller.extract(request, llm)
        await store.update_pattern(pattern, request.outcome)
    except Exception as exc:
        # BackgroundTask eats exceptions — log explicitly or you'll never know
        logger.error("distillation_failed", pattern_id=pattern.id, error=str(exc))
        # Do NOT re-raise — caller already got 202, nothing to do
```

**Do not use asyncio.create_task for this.** `create_task` requires a running event loop
reference and has no integration with FastAPI's request lifecycle. BackgroundTask is
bound to the request and runs after response is sent — exactly what 202 semantics require.

**Do not use Celery/ARQ for MVP.** Adding a broker adds container complexity and a second
service. The hackathon constraint is single-container deployment on port 8080. Keep it simple.

**Post-hackathon upgrade path:** If distillation failure rate matters, replace BackgroundTask
with a small in-process asyncio queue (bounded `asyncio.Queue`) with a background worker
started in lifespan. That gives you retry, backpressure, and no external dependencies.

**Confidence level: HIGH** — BackgroundTask behavior verified against FastAPI docs and
community issue #2505 (exception swallowing confirmed).

---

## Question 4: FastAPI Lifespan for Shared State (Store, LLM Client)

**Use the lifespan asynccontextmanager pattern. Attach singletons to app.state.**

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from akc.patterns.store import JsonlStore
from akc.core.config import Settings
from openai import AsyncOpenAI

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    store = JsonlStore(kb_dir=settings.kb_dir)
    llm = AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
    app.state.store = store
    app.state.llm = llm
    yield
    # shutdown: close async clients
    await llm.close()

app = FastAPI(lifespan=lifespan)
```

```python
# core/deps.py
from fastapi import Request
from akc.patterns.store import JsonlStore
from openai import AsyncOpenAI

def get_store(request: Request) -> JsonlStore:
    return request.app.state.store

def get_llm(request: Request) -> AsyncOpenAI:
    return request.app.state.llm
```

**Why app.state over module-level globals:** The lifespan guarantees store and llm are
initialized before any request is handled. Module-level globals initialize at import time —
they fire before Settings() is validated, breaking test setups where env vars are not set.

**Why Depends() over direct import of app.state:** Features that use `Depends(get_store)`
can be tested with `app.dependency_overrides[get_store] = lambda: mock_store`. Direct
`app.state` access in feature code removes this swap point.

**One startup failure mode to avoid:** If `Settings()` raises (missing required env var), the
lifespan raises before yield and FastAPI refuses to start — correct behavior. Do not catch
Settings exceptions in lifespan; let them surface.

**Confidence level: HIGH** — verified against official FastAPI lifespan docs at
fastapi.tiangolo.com/advanced/events/ and confirmed against the singleton/DI patterns in the
FastAPI community.

---

## Question 5: patterns/ Domain Interface — Keeping Features Independent

**The interface contract is three methods on JsonlStore. Keep it stable.**

```python
# patterns/store.py  — the stable interface
class JsonlStore:
    def load_active(self, min_tier: Tier, tags: list[str]) -> list[Pattern]: ...
    async def update_pattern(self, pattern_id: str, outcome: str, new_pattern: Pattern | None) -> None: ...
    def load_stats(self) -> StoreStats: ...
```

Features import the store interface, never the file format. This means:
- `recall/service.py` calls `store.load_active(...)` — it does not open JSONL files
- `stats/service.py` calls `store.load_stats()` — it does not count lines
- `remember/service.py` calls `store.update_pattern(...)` — it does not manage the lock

`patterns/engine.py` is **not** part of the public interface. It is an internal dependency
of `store.py`. Features do not import from `engine.py` directly. This keeps the Beta confidence
model replaceable without touching feature code.

```
patterns/
  models.py    ← features import Pattern, Tier, StoreStats
  store.py     ← features import JsonlStore (via Depends)
  engine.py    ← private to store.py only
```

**No cross-feature imports, ever.** If `stats/service.py` needs data that `recall/service.py`
already computes, the answer is not importing from `recall/`. The answer is adding a method to
`patterns/store.py`. That is the expansion point.

**Confidence level: HIGH** — this boundary pattern is directly validated by the architecture
doc and the feature-first layout. The reference codebase violates it (direct file access in
every engine) — the new codebase should not repeat that.

---

## Question 6: Concurrent JSONL Writes Under Docker

**Single container, single asyncio event loop: asyncio.Lock is sufficient. No fcntl needed.**

The deployment target is a single Docker container on port 8080 (confirmed by PRD and AgentBase
platform docs). Uvicorn defaults to a single worker process unless `--workers N` is specified.
The Dockerfile should not use `--workers` unless explicitly needed for scaling (not relevant at
hackathon scale).

Under single-process, single-event-loop conditions:
- `asyncio.Lock` is sufficient for serializing write access to JSONL files
- `fcntl.flock` provides no additional safety — it guards against separate OS processes, not
  coroutines in the same event loop
- The atomic tmp-rename pattern (`write to .tmp → os.replace(.tmp, target)`) makes individual
  writes crash-safe regardless of locking

**Safe write pattern for patterns.jsonl:**
```python
async def _atomic_save(self, patterns: dict[str, Pattern]) -> None:
    # Caller must hold self._write_lock
    tmp = self._patterns_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for pattern in patterns.values():
            f.write(pattern.model_dump_json() + "\n")
    os.replace(tmp, self._patterns_path)   # atomic on POSIX (ext4, overlayfs)
```

**Safe append pattern for confidence_history.jsonl:**
```python
def _append_history(self, entry: dict) -> None:
    # No lock needed — append is the only operation on this file
    with open(self._history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
```

**If multi-worker is ever added:** Switch `asyncio.Lock` to `filelock.FileLock` (the `filelock`
library has async support as of 3.x). Do not use `fcntl` directly — it is not portable to
Windows-based Docker hosts and is not available in all container environments.

**Docker volume note:** The `kb/` directory is mounted as a volume in Docker. The overlayfs
and ext4 filesystems used by Docker on Linux both support atomic `os.replace()`. Windows-mode
Docker (NTFS/WSL2) may have edge cases — avoid testing writes on Windows Docker Desktop in
production scenarios.

**Confidence level: HIGH for single-worker; MEDIUM for multi-worker** — asyncio.Lock behavior
is documented in Python stdlib. The multi-worker recommendation comes from filelock docs
(py-filelock.readthedocs.io) and Docker community forum discussions on file locking.

---

## Build Order Implications

The component dependency graph determines what must exist before each phase can be tested end-to-end:

```
Phase 1 (foundation): models.py → config.py → store.py (read-only) → /health
Phase 2 (core loop):  engine.py → store.py (write) → distiller.py → /remember + /recall
Phase 3 (ops):        stats/service.py → /stats
                      export/service.py → /kb/export
Phase 4 (platform):   deps.py (lifespan) → Docker → deploy to AgentBase
Phase 5 (integration):skill/SKILL.md → full loop test
```

`patterns/models.py` must be written first — everything depends on the Pattern dataclass shape.
`patterns/engine.py` must be written before `remember/service.py` — confidence math is a
precondition of the write path.
`core/deps.py` (lifespan) can be written last but should be wired in before any integration
test — running without it means using module-level globals which creates hidden state in tests.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Read-Modify-Write Without a Lock
**What:** `load_all() → mutate → save_all()` with no lock, as the reference codebase does.
**Why bad:** Two concurrent `/remember` requests produce a lost update. Under FastAPI's async
model, two BackgroundTasks can interleave at any `await` point.
**Instead:** Wrap the entire sequence in `async with self._write_lock`.

### Anti-Pattern 2: Module-Level Mutable Store
**What:** `store = JsonlStore()` at module level in `patterns/store.py`.
**Why bad:** Initializes before `Settings()` runs, breaks tests, creates import-time side effects.
**Instead:** Initialize in lifespan, attach to `app.state`, inject via `Depends()`.

### Anti-Pattern 3: Feature Code Opening JSONL Files Directly
**What:** Any feature (`recall/service.py`, `stats/service.py`) doing `open("kb/patterns.jsonl")`.
**Why bad:** Bypasses the lock, bypasses deduplication logic, couples features to file format.
**Instead:** All file access goes through `patterns/store.py` methods.

### Anti-Pattern 4: Swallowing BackgroundTask Exceptions
**What:** Background distillation fails silently with no log.
**Why bad:** Qwen API errors, malformed JSON responses, and network timeouts all become
invisible. The demo fails with no diagnostic.
**Instead:** Explicit try/except with `logger.error(...)` in the background function.

### Anti-Pattern 5: Importing engine.py from Feature Folders
**What:** `recall/service.py` importing `from akc.patterns.engine import update_confidence`.
**Why bad:** Lets features trigger writes without going through the lock in store.py.
**Instead:** All writes go through `store.update_pattern()`. Engine is private to store.

---

## Scalability Considerations

| Concern | At hackathon scale (<1K patterns) | At post-hackathon scale (10K+) |
|---------|----------------------------------|-------------------------------|
| JSONL read on every /recall | Fine — full file load is <10ms | Switch to in-memory cache with periodic reload |
| Write serialization via asyncio.Lock | Fine — lock hold time is <50ms | Fine — Qwen calls are already serialized |
| Confidence history file growth | Unbounded append — fine for months | Add periodic rotation by date |
| Memory footprint | All patterns in memory on load | Still fine at 10K — each pattern ~1KB = 10MB |

---

## Sources

- FastAPI lifespan docs: https://fastapi.tiangolo.com/advanced/events/
- FastAPI BackgroundTask exception swallowing: https://github.com/fastapi/fastapi/issues/2505
- BackgroundTask failure modes: https://dev.to/richard_quaicoe_2398278be/managing-background-tasks-in-fastapi-from-basic-to-production-ready-beyond-fire-and-forget-ddm
- asyncio.Lock: https://superfastpython.com/asyncio-lock/
- filelock async support: https://py-filelock.readthedocs.io/
- JSONL concurrent corruption report (NousResearch): https://github.com/NousResearch/hermes-agent/issues/12684
- FastAPI singleton/DI patterns: https://hrekov.com/blog/singleton-fastapi-dependency
- Reference codebase: `/home/brewuser/akc-service/akc_service/learning_engine.py` (lines 91–127: read-modify-write pattern, confirmed no locking)
