# Phase 1: Foundation - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 8 new/modified files
**Analogs found:** 1 partial / 8 (codebase is a single-file scaffold being replaced; all
real pattern authority comes from RESEARCH.md + ARCHITECTURE.md)

---

## Codebase Analog Assessment

The existing repo contains exactly one Python source file: `main.py` — a LangChain/GreenNode
scaffold that Phase 1 fully replaces. It is the only potential analog and it is a
**negative reference** (anti-pattern) for most concerns:

| Pattern Need | main.py behavior | Phase 1 behavior |
|---|---|---|
| Env validation | Manual `if not VAR: raise ValueError` (lines 23-39) | pydantic-settings BaseSettings — fail-fast |
| App factory | `GreenNodeAgentBaseApp()` (line 21) | `FastAPI(lifespan=lifespan)` |
| Health check | `@app.ping → PingStatus.HEALTHY` (lines 132-133) | `GET /health → {"status": "ok", "pattern_count": N}` |
| LLM imports | `langchain_openai`, `langgraph`, `greennode_agentbase` | None (Phase 1 has no LLM dependency) |
| File I/O | None | asyncio.Lock + asyncio.to_thread + os.replace |

`main.py` is referenced below only where it provides a **reuse opportunity**
(port, host, startup entry point structure).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `main.py` (full replace) | app-factory | request-response | `main.py` lines 137-138 (port/host reuse only) | structural-fragment |
| `akc/__init__.py` | package-init | — | none | no analog |
| `akc/patterns/__init__.py` | package-init | — | none | no analog |
| `akc/patterns/models.py` | model | transform | none in codebase; RESEARCH.md Pattern 2 | research-only |
| `akc/patterns/store.py` | service | file-I/O | none in codebase; RESEARCH.md Pattern 3 | research-only |
| `akc/patterns/engine.py` | utility | transform | none in codebase; RESEARCH.md Pattern 5 | research-only |
| `akc/core/__init__.py` | package-init | — | none | no analog |
| `akc/core/config.py` | config | request-response | `main.py` lines 23-39 (manual env check, negative reference) | negative-reference |
| `.env.example` | config | — | none (missing AKC_KB_DIR) | partial-update |

---

## Pattern Assignments

### `main.py` (app-factory, request-response) — FULL REPLACE

**Analog:** `main.py` lines 137-138 (port/host only)

**Reuse fragment** (lines 137-138 of existing `main.py`):
```python
if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
```
Replace `app.run(...)` with `uvicorn.run(...)` — port 8080 and host 0.0.0.0 are correct.

**New imports pattern** (from RESEARCH.md Pattern 4):
```python
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from akc.core.config import settings
from akc.patterns.store import JsonlStore
```

**Lifespan + health pattern** (RESEARCH.md Pattern 4 + ARCHITECTURE.md Question 4):
```python
logger = logging.getLogger("akc")
store = JsonlStore(kb_dir=settings.akc_kb_dir)

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
```

**Anti-pattern to avoid:** Do NOT use `@app.on_event("startup")` — deprecated in recent
FastAPI. Do NOT import or reference `langchain`, `langgraph`, `greennode_agentbase`,
`GreenNodeAgentBaseApp`, or `PingStatus` anywhere in the new `main.py`.

---

### `akc/core/config.py` (config, request-response)

**Analog:** `main.py` lines 23-39 — negative reference showing the manual pattern to replace.

**Anti-pattern being replaced** (existing `main.py` lines 23-39):
```python
# DO NOT copy this — this is what we are replacing
MEMORY_ID = os.environ.get("MEMORY_ID", "")
if not MEMORY_ID:
    raise ValueError("MEMORY_ID environment variable is required ...")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
if not LLM_MODEL or not LLM_BASE_URL or not LLM_API_KEY:
    raise ValueError(...)
```

**Correct pattern** (RESEARCH.md Pattern 1 — pydantic-settings):
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    llm_model: str           # required — no default; missing → ValidationError at import
    llm_base_url: str
    llm_api_key: str
    memory_id: str
    akc_kb_dir: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

# Module-level singleton — raises ValidationError at import if any var missing
settings = Settings()
```

**Key constraint:** Do NOT catch `ValidationError` here or in `main.py`. Let it propagate
to crash the process before uvicorn accepts connections (fail-fast per FNDTN-01).

---

### `akc/patterns/models.py` (model, transform)

**Analog:** None in codebase. Source: RESEARCH.md Pattern 2 + Code Examples section.

**Imports pattern:**
```python
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, field_validator
```

**Tier enum pattern** (RESEARCH.md Code Examples — Tier enum):
```python
class Tier(str, Enum):
    gold = "gold"
    production = "production"
    experimental = "experimental"
    demoted = "demoted"
```

**Pattern model with field_validator** (RESEARCH.md Pattern 2):
```python
class Pattern(BaseModel):
    id: str = ""
    context: str
    what_worked: str = ""
    what_failed: str = ""
    tags: list[str] = []
    confidence: float = 0.67       # ENG-01: Beta(2,1) prior — NOT 0.50
    tier: str = "experimental"
    consecutive_failures: int = 0  # ENG-06: persisted for Gold guardrail
    times_applied: int = 0
    last_updated: datetime | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list) -> list:  # ENG-07
        return [t.lower() for t in v] if isinstance(v, list) else v

    def model_post_init(self, __context: object) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)
```

**ConfidenceEvent model** (audit trail record for confidence_history.jsonl — STORE-02):
```python
class ConfidenceEvent(BaseModel):
    pattern_id: str
    outcome: str              # "success" | "failure"
    old_confidence: float
    new_confidence: float
    old_tier: str
    new_tier: str
    timestamp: datetime = None

    def model_post_init(self, __context: object) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
```

**Anti-pattern to avoid:** Do NOT use `datetime.utcnow()` — deprecated in Python 3.12+.
Always use `datetime.now(timezone.utc)`.

---

### `akc/patterns/store.py` (service, file-I/O)

**Analog:** None in codebase. Source: RESEARCH.md Pattern 3 + ARCHITECTURE.md Questions 1, 2, 6.

**Imports pattern:**
```python
import asyncio
import json
import os
import tempfile
from pathlib import Path

from akc.patterns.models import Pattern, ConfidenceEvent
```

**Constructor + lock pattern** (RESEARCH.md Pattern 3, lines defining `__init__`):
```python
class JsonlStore:
    def __init__(self, kb_dir: str):
        self._dir = Path(kb_dir).resolve()   # security: canonicalize path (ARCHITECTURE.md security)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._patterns_path = self._dir / "patterns.jsonl"
        self._history_path = self._dir / "confidence_history.jsonl"
```

**Sync read with last-write-wins dedup** (RESEARCH.md Pattern 3 + ARCHITECTURE.md Question 2):
```python
    def _read_patterns_sync(self) -> dict[str, dict]:
        """STORE-01: dedup by id, last occurrence wins."""
        if not self._patterns_path.exists():
            return {}
        result = {}
        with open(self._patterns_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    result[record["id"]] = record
        return result
```

**Atomic write pattern** (RESEARCH.md Pattern 3 + ARCHITECTURE.md Question 6):
```python
    def _write_patterns_atomic_sync(self, records: dict[str, dict]) -> None:
        """STORE-03: write to tmp → os.replace (atomic on POSIX)."""
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self._dir, delete=False, suffix=".tmp", encoding="utf-8"
        ) as tmp:
            for record in records.values():
                tmp.write(json.dumps(record) + "\n")
            tmp_path = tmp.name
        os.replace(tmp_path, str(self._patterns_path))
```

**Pure append for history** (RESEARCH.md Pitfall 2 — must NOT use atomic write on history):
```python
    def _append_history_sync(self, event: dict) -> None:
        """STORE-02: pure append, never deduplicated, never os.replace."""
        with open(self._history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
```

**Full read-modify-write cycle under lock** (RESEARCH.md Pattern 3):
```python
    async def update_pattern(self, pattern_id: str, outcome: str) -> None:
        """STORE-03: entire read-modify-write held under asyncio.Lock."""
        from akc.patterns import engine  # late import breaks circular dep
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
            if pattern_id not in patterns:
                return
            old = patterns[pattern_id]
            patterns[pattern_id] = engine.apply_outcome(old, outcome)
            await asyncio.to_thread(self._write_patterns_atomic_sync, patterns)
            history_event = {
                "pattern_id": pattern_id,
                "outcome": outcome,
                "old_confidence": old["confidence"],
                "new_confidence": patterns[pattern_id]["confidence"],
                "old_tier": old["tier"],
                "new_tier": patterns[pattern_id]["tier"],
                "timestamp": patterns[pattern_id]["last_updated"],
            }
            await asyncio.to_thread(self._append_history_sync, history_event)
```

**load_stats** (RESEARCH.md Code Examples — load_stats):
```python
    async def load_stats(self) -> dict:
        """STORE-04: used by /health and startup logging."""
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
        by_tier = {"gold": 0, "production": 0, "experimental": 0, "demoted": 0}
        for p in patterns.values():
            tier = p.get("tier", "experimental")
            by_tier[tier] = by_tier.get(tier, 0) + 1
        return {"total": len(patterns), "by_tier": by_tier}
```

**load_active stub** (RESEARCH.md Code Examples — load_active, needed by Phase 2/3):
```python
    async def load_active(
        self, min_tier: str = "production", tags: list[str] | None = None
    ) -> list[dict]:
        """STORE-04: returns non-demoted patterns filtered by min_tier and tags."""
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

**Critical anti-patterns:**
- Do NOT call `os.replace` on `_history_path` — that destroys the audit trail (RESEARCH.md Pitfall 2).
- Do NOT acquire the lock only for the write step — the entire read-modify-write must be atomic (RESEARCH.md Pitfall 4).
- Do NOT use `threading.Lock` — blocks the event loop (RESEARCH.md Standard Stack).

---

### `akc/patterns/engine.py` (utility, transform)

**Analog:** None in codebase. Source: RESEARCH.md Pattern 5 + ARCHITECTURE.md Question 5.

**Imports pattern:**
```python
from datetime import datetime, timezone
```

**Constants + classify_tier** (RESEARCH.md Pattern 5):
```python
INIT_CONFIDENCE = 0.67    # ENG-01: Beta(2,1) prior
SUCCESS_DELTA = 0.05      # ENG-02
FAILURE_DELTA = -0.10     # ENG-02
MAX_CONFIDENCE = 0.95     # ENG-02
GOLD_EXIT_THRESHOLD = 3   # ENG-05: consecutive failures to demote Gold

def classify_tier(confidence: float) -> str:
    """ENG-03."""
    if confidence >= 0.85:
        return "gold"
    if confidence >= 0.70:
        return "production"
    if confidence >= 0.50:
        return "experimental"
    return "demoted"
```

**apply_outcome — evaluation order is critical** (RESEARCH.md Pitfall 3):
```python
def apply_outcome(pattern: dict, outcome: str) -> dict:
    """Returns updated pattern dict. Pure function — no I/O, no state.

    Evaluation order (MUST NOT change):
      1. demotion lock check (ENG-04)
      2. Gold guardrail check (ENG-05)
      3. classify_tier from new confidence (ENG-03)
    """
    delta = SUCCESS_DELTA if outcome == "success" else FAILURE_DELTA
    new_conf = max(0.0, min(MAX_CONFIDENCE, pattern["confidence"] + delta))

    new_consec = 0 if outcome == "success" else pattern["consecutive_failures"] + 1

    # Step 1: demotion lock — ENG-04
    if pattern["tier"] == "demoted":
        new_tier = "demoted"
    # Step 2: Gold exit guardrail — ENG-05
    elif pattern["tier"] == "gold" and new_consec < GOLD_EXIT_THRESHOLD:
        new_tier = "gold"
    # Step 3: natural tier from confidence — ENG-03
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

**Verified math** (RESEARCH.md Pattern 5 — simulation results):
- 0.67 → Gold requires exactly 4 successes: 0.67 → 0.72 → 0.77 → 0.82 → 0.87
- Gold exit: conf=0.90, 3 failures: f1=0.80 (gold, consec=1), f2=0.70 (gold, consec=2), f3=0.60 (experimental, consec=3 ≥ threshold)
- Demotion: once `tier == "demoted"`, `apply_outcome` always returns `"demoted"` regardless of new confidence

---

### `.env.example` (config — partial update)

**Existing state:** `.env.example` contains `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`,
`MEMORY_ID` but is missing `AKC_KB_DIR` (FNDTN-03).

**Add this entry** to existing `.env.example`:
```bash
# Directory where patterns.jsonl and confidence_history.jsonl are stored
# Inside Docker: mount a volume here so patterns survive container restarts
AKC_KB_DIR=/app/data/kb
```

---

### `akc/__init__.py`, `akc/patterns/__init__.py`, `akc/core/__init__.py` (package-init)

**Analog:** None needed. These are empty files.

**Pattern:** All three files are empty (just `# akc package` as a single comment, or
completely empty). Do not add imports to `__init__.py` files in Phase 1 — Phase 2/3 wires
the public interface.

---

## Shared Patterns

### Datetime — Timezone-Aware Only
**Source:** RESEARCH.md Anti-Patterns + ARCHITECTURE.md
**Apply to:** `akc/patterns/models.py`, `akc/patterns/engine.py`, any file producing timestamps
```python
# CORRECT — Python 3.12+
from datetime import datetime, timezone
datetime.now(timezone.utc)

# WRONG — deprecated in Python 3.12, DeprecationWarning in 3.14
datetime.utcnow()
```

### asyncio.to_thread for Blocking File I/O
**Source:** RESEARCH.md Standard Stack + Pattern 3
**Apply to:** `akc/patterns/store.py` — all sync file operations dispatched via:
```python
await asyncio.to_thread(self._read_patterns_sync)
await asyncio.to_thread(self._write_patterns_atomic_sync, records)
await asyncio.to_thread(self._append_history_sync, event)
```

### Path Resolution (Security — KB_DIR Path Traversal)
**Source:** RESEARCH.md Security Domain (ARCHITECTURE.md path traversal threat)
**Apply to:** `akc/patterns/store.py` `__init__`
```python
self._dir = Path(kb_dir).resolve()   # canonicalize before any I/O
```

### pydantic v2 field_validator
**Source:** RESEARCH.md Pattern 2
**Apply to:** `akc/patterns/models.py` tag normalization
```python
@field_validator("tags", mode="before")
@classmethod
def normalize_tags(cls, v: list) -> list:
    return [t.lower() for t in v] if isinstance(v, list) else v
```

### model_dump_json for JSONL Serialization
**Source:** RESEARCH.md Standard Stack (pydantic BaseModel)
**Apply to:** anywhere a Pattern is written to JSONL — prefer `pattern.model_dump_json()`
over `json.dumps(pattern.dict())` (v1 API — removed in pydantic v2).

---

## No Analog Found

All Phase 1 files are net-new with no existing codebase analog. Pattern authority is
RESEARCH.md and ARCHITECTURE.md exclusively.

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `akc/patterns/models.py` | model | transform | First Python model file in this repo |
| `akc/patterns/store.py` | service | file-I/O | No file-I/O services exist in codebase |
| `akc/patterns/engine.py` | utility | transform | No pure-function utilities exist in codebase |
| `akc/core/config.py` | config | — | pydantic-settings never used before in this repo |
| `main.py` (new) | app-factory | request-response | LangChain scaffold is a negative reference only |

---

## Metadata

**Analog search scope:** `/home/brewuser/work/clawthon/dl-starter-kit/` — entire repo
**Files scanned:** `main.py`, `Dockerfile`, `requirements.txt`, `.planning/research/ARCHITECTURE.md`, `.planning/phases/01-foundation/01-RESEARCH.md`, `.planning/REQUIREMENTS.md`
**Codebase Python files found:** 1 (`main.py` — scaffold being replaced)
**Pattern extraction date:** 2026-06-11
**Pattern authority:** RESEARCH.md (all patterns verified by direct Python execution in project environment per RESEARCH.md Sources section)
