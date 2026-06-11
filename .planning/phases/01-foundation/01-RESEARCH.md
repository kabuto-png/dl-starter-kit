# Phase 1: Foundation - Research

**Researched:** 2026-06-11
**Domain:** FastAPI service skeleton, Pydantic v2 domain models, JSONL append-only store, confidence engine, /health endpoint
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FNDTN-01 | Service starts cleanly, validates all required env vars at startup (fail-fast via pydantic-settings), logs KB_DIR + pattern count | pydantic-settings BaseSettings with ValidationError on missing fields; lifespan startup event for logging |
| FNDTN-02 | `GET /health` returns 200 with `{"status": "ok", "pattern_count": N}` | Plain FastAPI endpoint; `pattern_count` read from JsonlStore.load_stats() |
| FNDTN-03 | `.env.example` documents LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, MEMORY_ID, AKC_KB_DIR | New field AKC_KB_DIR not yet in existing .env.example — must be added |
| FNDTN-04 | requirements.txt uses openai SDK directly; no langchain/langgraph/langchain-openai | requirements.txt already clean; main.py must be fully replaced (current scaffold imports langchain) |
| STORE-01 | patterns.jsonl deduplication is last-write-wins on read (dict[id → Pattern]) | Verified: read into dict keyed by id, last occurrence wins |
| STORE-02 | confidence_history.jsonl is pure append-only audit trail — never deduplicated | Different from patterns.jsonl — no dedup, just keep appending |
| STORE-03 | asyncio.Lock on JsonlStore; atomic write → os.replace for crash safety | Verified: asyncio.to_thread + Lock + tempfile + os.replace pattern works on Python 3.14 |
| STORE-04 | JsonlStore exposes 3-method interface: load_active, update_pattern, load_stats | Interface shape defined in architecture docs |
| ENG-01 | Pattern confidence initialized at 0.67 (Beta(2,1) prior) | Verified: 4 successes from 0.67 reach Gold (≥0.85) |
| ENG-02 | Confidence update: success +0.05, failure −0.10, cap 0.95, max delta ±0.15 | Verified math; natural delta is always exactly ±0.05/−0.10, well within ±0.15 cap |
| ENG-03 | Tier classification: Gold ≥0.85, Production 0.70–0.85, Experimental 0.50–0.70, Demoted <0.50 | Verified in engine simulation |
| ENG-04 | Demoted patterns never auto-promote — require manual intervention | Verified: demotion lock must check `current_tier == 'demoted'` before applying natural tier |
| ENG-05 | Gold exit guardrail: 3 consecutive failures to demote Gold pattern | Verified: consecutive_failures field must be evaluated before natural tier assignment |
| ENG-06 | `consecutive_failures` field persisted on Pattern record | Pydantic field; written to patterns.jsonl on every update |
| ENG-07 | Tag normalization: all tags lowercase at write time (`@field_validator`) | Verified: `field_validator('tags', mode='before')` with list comprehension works correctly |

</phase_requirements>

---

## Summary

Phase 1 builds the domain foundation for AKC: a Python 3.14/FastAPI service that replaces the starter-kit scaffold (currently a LangChain/GreenNodeAgentBaseApp agent) with a plain, thin FastAPI application. The phase has no LLM dependency — it exercises only local file I/O and pure-Python math.

The existing `main.py` imports `langchain_openai`, `langchain.agents`, `langgraph`, and `greennode_agentbase`. It must be completely replaced. The `requirements.txt` is already clean (openai SDK only, no langchain). The `Dockerfile` and overall port/structure are reusable.

All design decisions for this phase are fully locked in REQUIREMENTS.md and the architecture docs. The confidence engine math has been verified by simulation: 4 successes from 0.67 reach Gold, the Gold exit guardrail requires exactly 3 consecutive failures, demoted patterns cannot self-promote, and the atomic JSONL write pattern (asyncio.Lock + asyncio.to_thread + tempfile + os.replace) works correctly on Python 3.14.

**Primary recommendation:** Build `akc/` package layout as defined in architecture_v1.md. Replace `main.py` entirely. `patterns/` sub-package (`models.py`, `store.py`, `engine.py`) is the only work in Phase 1 besides the app factory and /health.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Domain model (Pattern) | API / Backend | — | Pure Python dataclass; Pydantic BaseModel for validation |
| JSONL persistence | API / Backend | Database / Storage (file) | asyncio.Lock + atomic os.replace; local filesystem |
| Confidence engine | API / Backend | — | Pure functions; no network, no DB |
| /health endpoint | API / Backend | — | FastAPI route; reads pattern_count from store |
| Env validation | API / Backend | — | pydantic-settings BaseSettings; fails at process start |
| Tag normalization | API / Backend | — | @field_validator on Pattern write path |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.136.3 | HTTP framework, routing, dependency injection | Already in requirements.txt; standard async Python API framework |
| uvicorn[standard] | latest | ASGI server | Already in requirements.txt; production-grade |
| pydantic | 2.12.5 (installed) | Domain model validation, field_validator | Ships with FastAPI; v2 is current standard |
| pydantic-settings | 2.14.1 (latest) | Fail-fast env validation via BaseSettings | Already in requirements.txt; idiomatic pydantic v2 approach |
| python-dotenv | latest | .env file loading | Already in requirements.txt |

[VERIFIED: pip index versions pydantic-settings 2>/dev/null; pip show pydantic]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | 3.14 built-in | Lock, to_thread for file I/O | Always — no external async file lib needed |
| tempfile (stdlib) | built-in | Temp file for atomic write | Used inside write_jsonl_atomic helper |
| os (stdlib) | built-in | os.replace for atomic rename | Final step of atomic write |
| pathlib (stdlib) | built-in | Path manipulation, directory creation | Preferred over os.path |
| uuid (stdlib) | built-in | Generate Pattern IDs | uuid4() on Pattern creation |
| json (stdlib) | built-in | JSONL line serialization | One record per line |
| logging (stdlib) | built-in | Startup log of KB_DIR + count | Standard Python logging |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.to_thread (stdlib) | aiofiles | aiofiles not in requirements.txt; to_thread works identically |
| os.replace atomic rename | write-in-place | Write-in-place is NOT crash-safe; os.replace is atomic on POSIX |
| pydantic BaseModel | dataclasses | Loses field_validator, model_dump_json, automatic validation |
| asyncio.Lock | threading.Lock | asyncio.Lock is correct for async context; threading.Lock would block event loop |

**Installation:** No new packages needed. All required packages are already in `requirements.txt`. Phase 1 adds no new dependencies.

[VERIFIED: requirements.txt contents read directly]

---

## Architecture Patterns

### System Architecture Diagram

```
Process Start
    │
    ▼
pydantic-settings BaseSettings
    │ validates env vars
    │ raises ValidationError → process exits (fail-fast)
    ▼
FastAPI lifespan startup
    │
    ├─► JsonlStore.load_stats() ──────► patterns.jsonl (read)
    │       │ pattern_count
    │       ▼
    │   logger.info(KB_DIR, count)
    │
    ▼
Service accepts requests
    │
    └─► GET /health
            │
            ├─► JsonlStore.load_stats()
            │       └── reads patterns.jsonl, counts active patterns
            │
            └─► {"status": "ok", "pattern_count": N}
```

Write path (used by Phase 2, but store must be ready):

```
JsonlStore.update_pattern(id, outcome)
    │
    ├─► asyncio.Lock acquired
    │
    ├─► asyncio.to_thread(read_jsonl, "patterns.jsonl")
    │       └── dedup by id (last-write-wins)
    │
    ├─► engine.apply_outcome(pattern)
    │       ├─► confidence ± delta (capped at 0.95)
    │       ├─► consecutive_failures updated
    │       ├─► tier classified (with Gold guardrail + demotion lock)
    │       └─► returns updated Pattern
    │
    ├─► asyncio.to_thread(write_jsonl_atomic, records)
    │       ├─► NamedTemporaryFile in same directory
    │       ├─► write all records as JSONL
    │       └─► os.replace(tmp_path, target)   ← atomic
    │
    ├─► asyncio.to_thread(append_jsonl, "confidence_history.jsonl", event)
    │       └─► simple open(mode='a') — no dedup, pure append
    │
    └─► asyncio.Lock released
```

### Recommended Project Structure

```
akc/
  patterns/
    __init__.py
    models.py       # Pattern (BaseModel), Tier (str enum), ConfidenceEvent
    store.py        # JsonlStore class — asyncio.Lock, load/write methods
    engine.py       # apply_outcome(), classify_tier() — pure functions

  core/
    __init__.py
    config.py       # Settings (BaseSettings) — validated at import

main.py             # FastAPI app factory, lifespan, /health, router registration
.env.example        # Documents all required env vars including AKC_KB_DIR
```

Note: `recall/`, `remember/`, `stats/`, `export/` sub-packages are Phase 2-3 work. Phase 1 creates only `akc/patterns/` and `akc/core/`.

### Pattern 1: pydantic-settings Fail-Fast Env Validation

**What:** Define all required env vars as non-Optional fields on BaseSettings. If any are missing, ValidationError is raised at module import time, stopping the process before uvicorn accepts connections.

**When to use:** Always — at service startup, before any work is done.

```python
# Source: https://github.com/pydantic/pydantic-settings/blob/main/docs/index.md
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    llm_model: str           # required — no default
    llm_base_url: str        # required
    llm_api_key: str         # required
    memory_id: str           # required
    akc_kb_dir: str          # required

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
    )

# Raises pydantic.ValidationError at module load if any var is missing
settings = Settings()
```

### Pattern 2: Pydantic v2 Domain Model with field_validator

**What:** Use `@field_validator('tags', mode='before')` to normalize tags to lowercase at write time. Use `model_post_init` to set generated defaults (id, timestamps).

**When to use:** On all Pattern creation/deserialization paths.

```python
# Source: https://github.com/pydantic/pydantic/blob/main/docs/concepts/validators.md
from pydantic import BaseModel, field_validator
from datetime import datetime, timezone
import uuid

class Pattern(BaseModel):
    id: str = ""
    context: str
    what_worked: str = ""
    what_failed: str = ""
    tags: list[str] = []
    confidence: float = 0.67       # ENG-01: Beta(2,1) prior
    tier: str = "experimental"
    consecutive_failures: int = 0   # ENG-06: persisted for Gold guardrail
    times_applied: int = 0
    last_updated: datetime | None = None

    @field_validator('tags', mode='before')
    @classmethod
    def normalize_tags(cls, v: list) -> list:  # ENG-07
        return [t.lower() for t in v] if isinstance(v, list) else v

    def model_post_init(self, __context: object) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)
```

[VERIFIED: field_validator with list normalization confirmed working in Python 3.14 + pydantic 2.12.5]

### Pattern 3: Atomic JSONL Write with asyncio.Lock

**What:** Full read-modify-write cycle held under asyncio.Lock. Blocking file I/O dispatched to thread pool via asyncio.to_thread. Atomic rename via os.replace for crash safety.

**When to use:** Every write to patterns.jsonl (not confidence_history.jsonl — that is append-only).

```python
# Source: verified by direct execution in project environment
import asyncio, json, os, tempfile, pathlib
from typing import TYPE_CHECKING

class JsonlStore:
    def __init__(self, kb_dir: str):
        self._dir = pathlib.Path(kb_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._patterns_path = self._dir / "patterns.jsonl"
        self._history_path = self._dir / "confidence_history.jsonl"

    def _read_patterns_sync(self) -> dict[str, dict]:
        """Dedup: last-write-wins by id. STORE-01."""
        if not self._patterns_path.exists():
            return {}
        result = {}
        with open(self._patterns_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    result[record["id"]] = record  # last occurrence wins
        return result

    def _write_patterns_atomic_sync(self, records: dict[str, dict]) -> None:
        """STORE-03: atomic write → os.replace."""
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self._dir, delete=False, suffix=".tmp"
        ) as tmp:
            for record in records.values():
                tmp.write(json.dumps(record) + "\n")
            tmp_path = tmp.name
        os.replace(tmp_path, str(self._patterns_path))

    async def update_pattern(self, pattern_id: str, outcome: str) -> None:
        """STORE-03: full cycle under lock."""
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
            if pattern_id not in patterns:
                return
            # engine.apply_outcome modifies in place, returns updated
            patterns[pattern_id] = apply_outcome(patterns[pattern_id], outcome)
            await asyncio.to_thread(self._write_patterns_atomic_sync, patterns)
            # append to history (pure append, no lock required beyond what we hold)
            await asyncio.to_thread(self._append_history_sync, pattern_id, outcome)
```

[VERIFIED: asyncio.Lock + asyncio.to_thread + os.replace confirmed working, Python 3.14]

### Pattern 4: FastAPI Lifespan Startup with Pattern Count Logging

**What:** Use `@asynccontextmanager` lifespan (not deprecated `@app.on_event("startup")`) to load pattern count at startup and log it. This satisfies FNDTN-01 and DEPLOY-03.

```python
# Source: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/events.md
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

logger = logging.getLogger("akc")

@asynccontextmanager
async def lifespan(app: FastAPI):
    stats = await store.load_stats()
    logger.info("AKC starting — KB_DIR: %s, patterns: %d", settings.akc_kb_dir, stats["total"])
    yield
    logger.info("AKC shutting down")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    stats = await store.load_stats()
    return {"status": "ok", "pattern_count": stats["total"]}
```

### Pattern 5: Confidence Engine Pure Functions

**What:** `engine.py` contains only pure functions — no I/O, no state. The store calls these functions; they return updated values.

**Critical implementation detail verified by simulation:**

- From 0.67, reaching Gold (≥0.85) requires exactly **4 successes**: 0.67 → 0.72 → 0.77 → 0.82 → 0.87
- Gold exit guardrail: 3 consecutive failures to demote. With start conf=0.90: after f1=0.80 (gold), f2=0.70 (gold), f3=0.60 (experimental at consec=3)
- Demotion lock: `if current_tier == "demoted": return "demoted"` regardless of new confidence
- Success resets consecutive_failures to 0

```python
# Source: verified by simulation in project environment
INIT_CONFIDENCE = 0.67  # ENG-01
SUCCESS_DELTA = 0.05    # ENG-02
FAILURE_DELTA = -0.10   # ENG-02
MAX_CONFIDENCE = 0.95   # ENG-02
GOLD_EXIT_THRESHOLD = 3 # ENG-05

def classify_tier(confidence: float) -> str:  # ENG-03
    if confidence >= 0.85: return "gold"
    if confidence >= 0.70: return "production"
    if confidence >= 0.50: return "experimental"
    return "demoted"

def apply_outcome(pattern: dict, outcome: str) -> dict:
    """Returns a new dict with updated confidence, tier, consecutive_failures."""
    delta = SUCCESS_DELTA if outcome == "success" else FAILURE_DELTA
    new_conf = max(0.0, min(MAX_CONFIDENCE, pattern["confidence"] + delta))

    if outcome == "failure":
        new_consec = pattern["consecutive_failures"] + 1
    else:
        new_consec = 0

    # ENG-04: demotion lock
    if pattern["tier"] == "demoted":
        new_tier = "demoted"
    # ENG-05: Gold exit guardrail
    elif pattern["tier"] == "gold" and new_consec < GOLD_EXIT_THRESHOLD:
        new_tier = "gold"
    else:
        new_tier = classify_tier(new_conf)

    return {
        **pattern,
        "confidence": new_conf,
        "tier": new_tier,
        "consecutive_failures": new_consec,
        "times_applied": pattern["times_applied"] + 1,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
```

[VERIFIED: math and guardrail logic confirmed by simulation]

### Anti-Patterns to Avoid

- **`datetime.utcnow()`:** Deprecated in Python 3.12+. Use `datetime.now(timezone.utc)` instead. [VERIFIED: DeprecationWarning confirmed in Python 3.14]
- **`@app.on_event("startup")`:** Deprecated in recent FastAPI. Use `lifespan` context manager. [CITED: fastapi.tiangolo.com/advanced/events/]
- **Write directly to target file:** Not atomic. A crash mid-write corrupts the JSONL. Always write to tmp then `os.replace`.
- **`threading.Lock` instead of `asyncio.Lock`:** Will block the event loop. Use `asyncio.Lock` for async code.
- **Mutable global state (patterns dict):** Don't cache patterns in memory for Phase 1 — always read from file. Caching is Phase 3+ concern.
- **`model_validate` without `model_dump` round-trip test:** Pydantic v2 silently drops unknown fields by default. Test that JSON round-trips preserve all fields including `consecutive_failures`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var validation | Custom env-var checker | pydantic-settings BaseSettings | Handles type coercion, .env loading, error messages |
| Atomic file writes | Custom file locking | `tempfile + os.replace` (POSIX atomic) | os.replace is atomic on Linux (rename syscall) |
| Thread-safe async I/O | asyncio.Queue-based file serializer | asyncio.Lock + asyncio.to_thread | Standard pattern; simpler, correct |
| JSON schema for Pattern | Manual dict validation | Pydantic BaseModel + model_dump_json | Free validation, serialization, and documentation |
| UUID generation | Custom ID scheme | `uuid.uuid4()` | Collision-free, no coordination needed |

**Key insight:** The confidence engine is genuinely simple — it's just addition with clamping. The complexity lives in the guardrails (Gold exit, demotion lock), not the math. Keep engine.py as pure functions with no hidden state.

---

## Common Pitfalls

### Pitfall 1: main.py Scaffold Must Be Completely Replaced

**What goes wrong:** Developer extends existing `main.py` instead of replacing it. The LangChain/GreenNodeAgentBaseApp scaffold tries to import `langchain_openai`, `langchain.agents`, `langgraph`, which are not in `requirements.txt`. Service crashes on startup.

**Why it happens:** The starter kit scaffold is the only Python file in the repo; it's tempting to edit rather than replace.

**How to avoid:** Delete `main.py` content entirely. Build new app from scratch using FastAPI directly. The `Dockerfile`, `requirements.txt`, and port 8080 remain unchanged.

**Warning signs:** Any import of `langchain`, `langgraph`, `greennode_agentbase`, or `ChatOpenAI` in the new Phase 1 code.

### Pitfall 2: confidence_history.jsonl Mixed with patterns.jsonl Logic

**What goes wrong:** Developer applies last-write-wins dedup to `confidence_history.jsonl`, destroying the audit trail. Or applies append-only to `patterns.jsonl`, causing duplicate records to accumulate without dedup.

**Why it happens:** Both files live in the same directory and have similar format. The dedup rule differs per file.

**How to avoid:** Two separate methods: `_read_patterns_sync` (deduplicates by id), `_append_history_sync` (pure append, no read-back). Never use the atomic write pattern on history file.

**Warning signs:** `os.replace` being called on `confidence_history.jsonl`.

### Pitfall 3: Gold Exit Guardrail Applied in Wrong Order

**What goes wrong:** Developer checks `new_conf >= 0.85` before checking consecutive failures, so a Gold pattern that has taken 2 failures but still has conf ≥ 0.85 is wrongly kept at Gold for the wrong reason — and one that has 3+ failures but dropped below 0.85 is also handled incorrectly.

**Why it happens:** Natural tendency to classify tier from confidence first.

**How to avoid:** Evaluation order must be: (1) demotion lock check, (2) Gold guardrail check (consec < 3 while current_tier == gold), (3) classify from confidence. See Pattern 5 above.

**Warning signs:** `classify_tier(new_conf)` called before checking `consecutive_failures`.

### Pitfall 4: asyncio.Lock Not Held Across Entire Read-Modify-Write

**What goes wrong:** Lock is acquired for write but not read. Two concurrent calls read the same stale state, both compute updates, and one overwrites the other.

**Why it happens:** Developer thinks "I only need the lock for the write."

**How to avoid:** `async with self._lock:` wraps the entire `read → modify → write` sequence. See Pattern 3.

**Warning signs:** `async with self._lock:` block that only contains the write call.

### Pitfall 5: pydantic-settings ValidationError Not Caught — Service Hangs

**What goes wrong:** If `Settings()` raises `ValidationError` inside a `try/except Exception as e: pass` block, the service starts with `None` settings and fails silently on first request.

**Why it happens:** Generic exception swallowing during startup.

**How to avoid:** Let `ValidationError` propagate uncaught at module level. Process exits immediately with a clear error message. Uvicorn will not start. This IS the fail-fast behavior.

---

## Code Examples

### Complete Tier Enum

```python
# Tier as str enum — serializes cleanly to JSONL string values
from enum import Enum

class Tier(str, Enum):
    gold = "gold"
    production = "production"
    experimental = "experimental"
    demoted = "demoted"
```

### load_stats Implementation

```python
async def load_stats(self) -> dict:
    """STORE-04: load_stats() for /health and startup logging."""
    async with self._lock:
        patterns = await asyncio.to_thread(self._read_patterns_sync)
    by_tier = {"gold": 0, "production": 0, "experimental": 0, "demoted": 0}
    for p in patterns.values():
        tier = p.get("tier", "experimental")
        by_tier[tier] = by_tier.get(tier, 0) + 1
    return {"total": len(patterns), "by_tier": by_tier}
```

### load_active Implementation Stub (STORE-04)

```python
async def load_active(self, min_tier: str = "production", tags: list[str] | None = None) -> list[dict]:
    """Return non-demoted patterns filtered by min_tier and tags."""
    tier_rank = {"gold": 3, "production": 2, "experimental": 1, "demoted": 0}
    min_rank = tier_rank.get(min_tier, 2)

    async with self._lock:
        patterns = await asyncio.to_thread(self._read_patterns_sync)

    results = []
    for p in patterns.values():
        if p.get("tier") == "demoted":
            continue
        if tier_rank.get(p.get("tier", "experimental"), 0) < min_rank:
            continue
        if tags:
            pattern_tags = set(p.get("tags", []))
            if not any(t.lower() in pattern_tags for t in tags):
                continue
        results.append(p)
    return sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI ~0.93 | Deprecated startup events; use lifespan |
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 | utcnow deprecated; timezone-aware is correct |
| pydantic v1 `@validator` | pydantic v2 `@field_validator` | Pydantic 2.0 | v1 decorator removed in v2 |
| `aiofiles` for async file I/O | `asyncio.to_thread` (stdlib) | Python 3.9+ | to_thread is stdlib; aiofiles now optional |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `greennode-agentbase` and `greennode-agent-bridge` in requirements.txt are not needed for Phase 1 but are harmless to keep (used in Phase 4 deployment) | Standard Stack | If AgentBase platform requires these even for plain FastAPI, Phase 4 may need adjustment |
| A2 | The `/health` endpoint shape `{"status": "ok", "pattern_count": N}` satisfies the AgentBase health check contract | Architecture Patterns | If AgentBase expects a different response structure, the contract must be verified on Day 3 |
| A3 | `AKC_KB_DIR` is the correct env var name for the JSONL storage directory (appears in requirements but not yet in .env.example) | Standard Stack | Name must match exactly what Phase 2/3/4 code reads |

---

## Open Questions

1. **Does AgentBase require `/health` or use the `@app.ping` PingStatus contract?**
   - What we know: Existing scaffold uses `@app.ping → PingStatus.HEALTHY`. FNDTN-02 specifies `GET /health` returning `{"status": "ok", "pattern_count": N}`.
   - What's unclear: Whether AgentBase will call `/health` (standard) or a platform-specific ping path.
   - Recommendation: Implement `GET /health` per spec. The `PingStatus` approach was for the LangChain scaffold being replaced. FNDTN-02 is the locked decision.

2. **Should LLM env vars (LLM_MODEL, LLM_BASE_URL, LLM_API_KEY) fail-fast in Phase 1?**
   - What we know: FNDTN-01 says "validates all required env vars at startup." FNDTN-03 lists LLM vars as required in .env.example. Phase 1 does NOT use LLM.
   - What's unclear: Whether to require all 5 vars even though LLM isn't called in Phase 1.
   - Recommendation: Include all 5 (LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, MEMORY_ID, AKC_KB_DIR) in Settings. Fail-fast is the stated behavior. This also validates the full deployment config early.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.14.3 | — |
| asyncio (stdlib) | STORE-03 | ✓ | built-in | — |
| pydantic | FNDTN-01, ENG-07 | ✓ | 2.12.5 | — |
| pydantic-settings | FNDTN-01 | not in system env | 2.14.1 (latest) | Install via project venv |
| fastapi | FNDTN-02 | not in system env | 0.136.3 (latest) | Install via project venv |
| uvicorn | Serving | not in system env | latest | Install via project venv |
| os.replace | STORE-03 | ✓ | POSIX stdlib | — |
| asyncio.to_thread | STORE-03 | ✓ | Python 3.9+ stdlib | — |

[VERIFIED: pip index versions, pip show, direct Python execution]

**Missing dependencies with no fallback:** None — all packages are already in `requirements.txt`. They are absent from the system Python environment but will install correctly in a project virtualenv or Docker container.

---

## Validation Architecture

> nyquist_validation is false per config.json — this section is SKIPPED.

---

## Security Domain

> security_enforcement: true, security_asvs_level: 1 per config.json.

### Applicable ASVS Categories (ASVS Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in Phase 1 (or v1 — out of scope per REQUIREMENTS.md) |
| V3 Session Management | No | Stateless HTTP service; no sessions |
| V4 Access Control | No | No access control in v1 scope |
| V5 Input Validation | Yes (limited) | Pydantic BaseModel validates all inputs; no external input in Phase 1 |
| V6 Cryptography | No | No cryptographic operations in Phase 1 |

### Known Threat Patterns for Phase 1 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via AKC_KB_DIR | Tampering | `pathlib.Path(kb_dir).resolve()` to canonicalize; validate dir is writable at startup |
| JSONL injection via pattern fields | Tampering | Pydantic model validates all fields; json.dumps() escapes special characters automatically |
| Uncaught exception leaks env vars | Information Disclosure | Never log raw `settings` object; log only non-sensitive fields (KB_DIR, count) |

**Phase 1 security note:** The primary risk is the KB_DIR path traversal. At startup, resolve and validate the path before any reads or writes. The service has no auth surface in v1 by explicit design decision.

---

## Sources

### Primary (HIGH confidence)
- `/pydantic/pydantic-settings` (Context7) — BaseSettings, SettingsConfigDict, ValidationError patterns
- `/pydantic/pydantic` (Context7) — field_validator, mode='before', BaseModel
- `/fastapi/fastapi` (Context7) — lifespan, asynccontextmanager, endpoint definition
- Direct Python execution — atomic write pattern, confidence math, tag normalization verified running in project environment (Python 3.14.3, pydantic 2.12.5)

### Secondary (MEDIUM confidence)
- `.planning/docs/architecture_v1.md` — folder structure, dependency rules, request flow diagrams
- `.planning/REQUIREMENTS.md` — all 15 phase 1 requirements read verbatim
- `requirements.txt` — package list verified directly

### Tertiary (LOW confidence)
- None — all claims verified via tool or official source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — packages verified via pip index versions and direct import test
- Architecture: HIGH — folder structure, patterns, and dependency rules documented in architecture_v1.md and requirements
- Confidence engine math: HIGH — verified by Python simulation in project environment
- Pitfalls: HIGH — three of five pitfalls verified by direct observation (deprecated utcnow, missing pydantic-settings, langchain in main.py)

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable stack; pydantic and FastAPI versions pinned)
