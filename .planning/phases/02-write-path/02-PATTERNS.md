# Phase 2: Write Path - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 3 new + 1 modified files
**Analogs found:** 2 from Phase 1 reuse / 4 total

---

## Codebase Analog Assessment

Phase 2 builds on Phase 1's foundation (models.py, store.py, engine.py, config.py). The existing Phase 1 architecture provides direct analogs for:

1. **Store patterns** — JsonlStore.insert_pattern() and JsonlStore.update_pattern() (both already exist from Phase 1)
2. **Engine patterns** — engine.apply_outcome() reused directly for confidence feedback loop

New Phase 2 patterns (distillation, LLM integration, BackgroundTask) are not present in Phase 1 and rely entirely on RESEARCH.md.

| Pattern Need | Phase 1 Authority | Phase 2 Authority | Reuse |
|---|---|---|---|
| Store write (insert new pattern) | store.py (to be created) | — | Will be added to Phase 1 |
| Store update (confidence feedback) | store.py (to be created) | — | Will be added to Phase 1 |
| Engine confidence logic | engine.py (to be created) | RMB-07 | Direct reuse: apply_outcome() |
| Qwen distillation | — | RESEARCH.md Pattern 2 | No analog |
| BackgroundTask wiring | — | RESEARCH.md Pattern 1 | No analog |
| LLM client setup | — | RESEARCH.md Pattern 2 | No analog |

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `main.py` (append) | app-factory | request-response | Phase 1's main.py (extension) | structural-extension |
| `akc/remember/__init__.py` | package-init | — | Phase 1's akc/patterns/__init__.py | identical-pattern |
| `akc/remember/models.py` | model | transform | Phase 1's akc/patterns/models.py | similar-scope |
| `akc/remember/distiller.py` | service | LLM-I/O | RESEARCH.md Pattern 2 | research-only |

---

## Pattern Assignments

### `main.py` (app-factory, request-response) — APPEND

**Analog:** Phase 1's main.py lifespan + health route patterns

**Extension point:** Add POST /remember route to existing Phase 1 main.py

**New imports pattern** (addition to Phase 1 imports):
```python
from fastapi import BackgroundTasks, HTTPException
import asyncio

from akc.remember.models import DistillRequest
from akc.remember.distiller import distill_and_store
```

**POST /remember endpoint pattern** (RESEARCH.md Pattern 1):
```python
@app.post("/remember", status_code=202)
async def remember(request: DistillRequest, background_tasks: BackgroundTasks):
    """RMB-01: Return 202 immediately; distillation runs in BackgroundTask."""
    background_tasks.add_task(distill_and_store, request, store)
    return {}  # 202 response body is empty or minimal
```

**Key constraints:**
- Status code MUST be 202 (not 200) per RMB-01
- Response body is minimal `{}`
- `background_tasks: BackgroundTasks` injected as route parameter
- `background_tasks.add_task()` called before return
- Endpoint returns immediately (request body already validated by Pydantic)

[VERIFIED: FastAPI BackgroundTasks pattern from official guide]

**Anti-patterns to avoid:**
- Do NOT await distill_and_store() in the endpoint — that blocks the caller
- Do NOT return the distilled pattern in the 202 response — distillation runs async
- Do NOT catch exceptions in the endpoint — BackgroundTask has its own exception boundary

---

### `akc/remember/__init__.py` (package-init)

**Analog:** Phase 1's akc/patterns/__init__.py, akc/core/__init__.py

**Pattern:** Empty file (or single comment line). Do not add imports; Phase 3 will wire the public interface.

```python
# remember package
```

---

### `akc/remember/models.py` (model, transform)

**Analog:** Phase 1's akc/patterns/models.py (similar Pydantic model patterns)

**Imports pattern:**
```python
from pydantic import BaseModel, field_validator
from typing import Optional
```

**DistillRequest model** (request body for POST /remember):
```python
class DistillRequest(BaseModel):
    task_context: str              # Required: context of the task
    outcome: str                   # Required: raw outcome text to distill
    patterns_used: Optional[list[str]] = None  # Optional: IDs of patterns that were applied
    success: Optional[bool] = None              # Optional: whether the task succeeded
```

**DistilledPattern model** (output from Qwen distillation):
```python
class DistilledPattern(BaseModel):
    context: str                   # Brief description of the task scenario
    what_worked: str               # Specific thing that succeeded
    what_failed: str               # Specific thing that failed (or empty if success)
    tags: list[str] = []           # Lowercase tags describing this outcome

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list) -> list:
        """Match Phase 1's tag normalization pattern (ENG-07)."""
        return [t.lower() for t in v] if isinstance(v, list) else v
```

**Key constraints:**
- Use Pydantic v2 (matching Phase 1)
- All models use BaseModel (not TypedDict)
- Tags are normalized to lowercase at validation time
- patterns_used is optional — None or absent means no confidence feedback

**Anti-patterns to avoid:**
- Do NOT use pydantic v1 API (dict(), json() methods — removed in v2)
- Do NOT assume patterns_used is always present — check with if request.patterns_used before iterating

---

### `akc/remember/distiller.py` (service, LLM-I/O)

**Analog:** None in codebase. Source: RESEARCH.md Pattern 2 + Pattern 3

**Imports pattern:**
```python
import re
import json
import logging
import asyncio
from openai import OpenAI, APIError

from akc.core.config import settings
from akc.remember.models import DistilledPattern
from akc.patterns.models import Pattern
from akc.patterns import engine

logger = logging.getLogger("akc.remember")
```

**async def distill_task_outcome()** (RESEARCH.md Pattern 2 — Qwen distillation):

```python
async def distill_task_outcome(task_context: str, outcome_text: str) -> dict | None:
    """
    RMB-03, RMB-04, RMB-05, RMB-06: Call Qwen with json_object response_format.
    Disable thinking mode. Defensively strip <think> tokens. Check finish_reason.
    Returns dict {context, what_worked, what_failed, tags} or None on error.
    """
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    system_prompt = """Extract the key learning from this task outcome. Respond with ONLY a JSON object (no markdown, no extra text).
    {
      "context": "brief description of the task or scenario",
      "what_worked": "specific thing that succeeded",
      "what_failed": "specific thing that failed, or empty string if success",
      "tags": ["lowercase", "tags", "describing", "this", "outcome"]
    }
    """

    user_prompt = f"""Task context: {task_context}

Outcome: {outcome_text}"""

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},  # RMB-03
            max_tokens=512,  # RMB-06: >= 512
            extra_body={"enable_thinking": False},  # RMB-04: disable thinking
            temperature=0.5,  # Low temperature for structured extraction
        )

        # RMB-05: Check finish_reason before parsing
        if response.choices[0].finish_reason == "length":
            logger.warning(
                "Qwen distillation truncated (finish_reason=length); skipping store",
                extra={"task_context_len": len(task_context)}
            )
            return None

        content = response.choices[0].message.content

        # RMB-04: Defensively strip <think> tokens (second safety layer)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = content.strip()

        if not content:
            logger.warning("Qwen response empty after think-stripping")
            return None

        # RMB-03: Use model_validate_json (NOT completions.parse)
        try:
            distilled = DistilledPattern.model_validate_json(content)
        except json.JSONDecodeError as e:
            logger.error(
                f"Qwen response not valid JSON: {e}",
                extra={"content_sample": content[:200]}
            )
            return None
        except Exception as e:
            logger.error(
                f"Distilled pattern failed validation: {e}",
                extra={"content": content}
            )
            return None

        return distilled.model_dump()

    except APIError as e:
        logger.error(f"Qwen API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during distillation: {e}", exc_info=True)
        return None
```

**Key constraints:**
- `response_format={"type": "json_object"}` — tells Qwen to return valid JSON
- `extra_body={"enable_thinking": False}` — disable reasoning tokens (GreenNode parameter)
- `max_tokens >= 512` — ensure enough budget for structured output
- Strip `<think>...</think>` BEFORE `json.loads()` — defensive against thinking tokens
- Check `finish_reason == "length"` and skip store if truncated
- Use `model_validate_json()`, NOT `json.loads()` directly — we control JSON cleaning

[VERIFIED: OpenAI API response_format contract; extra_body parameter for custom fields; Pydantic model_validate_json() method]

**async def distill_and_store()** (RESEARCH.md Pattern 3 — BackgroundTask error boundary):

```python
async def distill_and_store(request: DistillRequest, store) -> None:
    """RMB-02: Wrap entire operation in try/except. Never raise exceptions."""
    try:
        # Step 1: Distill
        distilled = await distill_task_outcome(request.task_context, request.outcome)
        if distilled is None:
            # Already logged inside distill_task_outcome
            return

        # Step 2: Check for duplicate by hash
        pattern_hash = _hash_pattern(
            distilled["context"],
            distilled["what_worked"],
            distilled["what_failed"]
        )
        existing = await _check_duplicate_hash(store, pattern_hash)
        if existing:
            logger.debug(f"Pattern duplicate found, skipping store: {existing['id']}")
            return

        # Step 3: Create new pattern at experimental tier
        new_pattern = Pattern(
            context=distilled["context"],
            what_worked=distilled["what_worked"],
            what_failed=distilled["what_failed"],
            tags=distilled.get("tags", []),
            confidence=engine.INIT_CONFIDENCE,  # RMB-08: experimental tier (0.67)
            tier="experimental",
        )

        # Step 4: Store new pattern
        await store.insert_pattern(new_pattern)
        logger.info(
            f"Distilled and stored new pattern",
            extra={"pattern_id": new_pattern.id, "tags": new_pattern.tags}
        )

        # Step 5: Update confidence of patterns_used (RMB-07)
        if request.patterns_used:
            outcome_type = "success" if request.success else "failure"
            for pattern_id in request.patterns_used:
                try:
                    await store.update_pattern(pattern_id, outcome_type)
                    logger.debug(f"Updated pattern confidence", extra={"pattern_id": pattern_id, "outcome": outcome_type})
                except Exception as e:
                    logger.error(
                        f"Failed to update pattern confidence",
                        extra={"pattern_id": pattern_id, "error": str(e)}
                    )
                    # Continue updating other patterns; do not re-raise

    except Exception as e:
        # RMB-02: Catch all exceptions at boundary; log with full context
        logger.error(
            f"distill_and_store failed; KB remains consistent",
            extra={
                "task_context_len": len(request.task_context) if request.task_context else 0,
                "exception": type(e).__name__,
                "message": str(e),
            },
            exc_info=True  # Include stack trace
        )
        # DO NOT re-raise; DO NOT crash service
```

**Helper function: _hash_pattern()** (RESEARCH.md Pattern 4):

```python
import hashlib

def _hash_pattern(context: str, what_worked: str, what_failed: str) -> str:
    """Compute a deterministic hash of the pattern's core content."""
    combined = f"{context}|||{what_worked}|||{what_failed}".lower().strip()
    return hashlib.sha256(combined.encode()).hexdigest()
```

**Helper function: _check_duplicate_hash()** (RESEARCH.md Pattern 4):

```python
async def _check_duplicate_hash(store, pattern_hash: str) -> dict | None:
    """Check if a pattern with this hash already exists. Return the pattern or None."""
    patterns = await store.load_active(min_tier="experimental", tags=None)
    for pattern in patterns:
        existing_hash = _hash_pattern(
            pattern.get("context", ""),
            pattern.get("what_worked", ""),
            pattern.get("what_failed", "")
        )
        if existing_hash == pattern_hash:
            return pattern
    return None
```

**Key constraints:**
- `try/except Exception as e:` at outermost level — catches all exception types
- Log with `exc_info=True` to include stack trace — critical for debugging background task failures
- Log with `extra={}` dict for structured logging — facilitates debugging and observability
- Never re-raise or raise SystemExit or KeyboardInterrupt — the service must continue running
- Return cleanly (None) — BackgroundTask completion is not observed by caller
- New patterns use engine.INIT_CONFIDENCE (0.67) — reuses Phase 1 constant
- Call engine.apply_outcome() is NOT needed here — apply_outcome() is called by store.update_pattern() internally

**Anti-patterns to avoid:**
- Do NOT call engine.apply_outcome() directly — store.update_pattern() does this
- Do NOT use `asyncio.timeout()` here — Phase 2 doesn't specify timeout; Qwen errors are logged and handled
- Do NOT insert the new pattern's id into patterns_used feedback — feedback is only for pre-existing patterns

---

## Integration Points with Phase 1

### JsonlStore Extension (Phase 1 → Phase 2)

Phase 1's store.py MUST provide these methods for Phase 2:

1. **insert_pattern(pattern: Pattern) -> None**
   - Takes a Pattern object (Pydantic model from Phase 1)
   - Writes to patterns.jsonl (append-only, STORE-01 dedup on read)
   - Must be atomic (STORE-03)

2. **update_pattern(pattern_id: str, outcome: str) -> None**
   - Takes pattern_id and outcome ("success" | "failure")
   - Reads patterns.jsonl, finds pattern by id
   - Calls engine.apply_outcome(pattern, outcome) to update confidence
   - Writes updated patterns.jsonl
   - Appends ConfidenceEvent to confidence_history.jsonl
   - Must be atomic (STORE-03)

3. **load_active(min_tier: str, tags: list[str] | None) -> list[dict]**
   - Returns non-demoted patterns filtered by min_tier and tags
   - Used by distiller for dedup check
   - Already defined in Phase 1 (store.py stub)

Both methods already exist in Phase 1 patterns/store.py per PATTERNS.md, so Phase 2 just calls them.

### Engine Reuse (Phase 1 → Phase 2)

Phase 1's engine.py provides:

1. **apply_outcome(pattern: dict, outcome: str) -> dict**
   - Pure function: applies confidence delta + tier update logic
   - Reused by store.update_pattern() when processing /remember feedback
   - No changes needed in Phase 2 — just call it

2. **INIT_CONFIDENCE constant**
   - Value: 0.67 (Beta(2,1) prior)
   - Used in Phase 2 when creating new patterns from distillation

---

## Shared Patterns

### Datetime — Timezone-Aware Only (from Phase 1)
**Source:** Phase 1 PATTERNS.md anti-patterns
**Apply to:** distiller.py (not needed for Phase 2, but if logging timestamps use this pattern)
```python
# CORRECT — Python 3.12+
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

### Pydantic v2 model_validate_json (from Phase 1)
**Source:** Phase 1 PATTERNS.md, RESEARCH.md Pattern 2
**Apply to:** akc/remember/models.py, distiller.py
```python
# Parse JSON string directly to model
distilled = DistilledPattern.model_validate_json(json_string)

# NOT v1 API:
# distilled = DistilledPattern.parse_raw(json_string)  # Removed in pydantic v2
```

### Structured Logging with extra dict (new for Phase 2)
**Source:** RESEARCH.md Pattern 2, Pattern 3
**Apply to:** distiller.py logging calls
```python
logger.error(
    "some message",
    extra={
        "field1": value1,
        "field2": value2,
    }
)
```

### asyncio.to_thread for Blocking Calls (from Phase 1)
**Source:** Phase 1 PATTERNS.md
**Note:** Not used in distiller.py (no blocking I/O), but store.py uses it for file operations.

### Field Validator for Tag Normalization (from Phase 1)
**Source:** Phase 1 PATTERNS.md, engine.py ENG-07
**Apply to:** akc/remember/models.py DistilledPattern tags field
```python
@field_validator("tags", mode="before")
@classmethod
def normalize_tags(cls, v: list) -> list:
    return [t.lower() for t in v] if isinstance(v, list) else v
```

---

## Critical Design Decisions

### 1. Distillation Happens in BackgroundTask, Not in Request Handler

**Pattern:** POST /remember endpoint returns 202 immediately; distill_and_store runs detached.

**Rationale:**
- Qwen inference latency is 1-3 seconds (unacceptable to block HTTP request)
- Client doesn't need the distilled pattern in the response (202 Accepted means "we got it, processing async")
- Failures in distillation don't affect the HTTP response

**Implementation:** FastAPI BackgroundTasks (not asyncio.create_task — BackgroundTasks ensures proper cleanup)

### 2. Two Layers of Thinking Mode Defense

**Pattern:** Disable thinking via extra_body={"enable_thinking": False} AND defensively strip `<think>` tokens.

**Rationale:**
- extra_body parameter name is assumed (GreenNode Qwen API docs not public)
- If parameter name is wrong, thinking tokens appear anyway
- Regex defensive strip catches this failure without corrupting JSON

**Implementation:** Always strip before json.loads; don't rely on extra_body alone.

### 3. Confidence Feedback via patterns_used IDs

**Pattern:** POST /remember body can include patterns_used (list of pattern IDs). If provided, confidence of those patterns is updated.

**Rationale:**
- Closes the feedback loop: task outcome informs whether prior patterns were useful
- Reuses Phase 1's engine.apply_outcome() logic
- Allows agent to report both "new learning" (new pattern) and "pattern validation" (update confidence)

**Implementation:** For each id in patterns_used, call store.update_pattern(id, outcome_type).

### 4. Pattern Deduplication by Hash

**Pattern:** Before inserting a new pattern from distillation, compute hash(context + what_worked + what_failed). Check if it exists. If yes, skip insert.

**Rationale:**
- Qwen can distill the same outcome multiple times
- Without dedup, duplicate patterns dilute confidence (two patterns capturing the same thing)
- Hash is deterministic; stable across calls

**Implementation:** hash_pattern() + check_duplicate_hash() helper functions.

### 5. Store Integration Via Dependency Injection

**Pattern:** distill_and_store(request, store) takes store as parameter (not global singleton).

**Rationale:**
- Allows testing with mock stores
- Avoids circular import (distiller imports store imports patterns imports distiller)
- main.py passes the live store instance from Phase 1

**Implementation:** main.py does `background_tasks.add_task(distill_and_store, request, store)`.

---

## No New Dependencies

Phase 2 adds **zero new external packages**. All required libraries are in requirements.txt from Phase 1:

| Library | Phase | Purpose | Verified |
|---------|-------|---------|----------|
| openai | Phase 1+ | Qwen LLM API via OpenAI-compatible client | In requirements.txt |
| pydantic | Phase 1+ | model_validate_json(), BaseModel | In requirements.txt |
| fastapi | Phase 1+ | BackgroundTasks | In requirements.txt |
| re (stdlib) | Phase 2 | Regex to strip `<think>` tokens | Built-in |
| asyncio (stdlib) | Phase 1+ | BackgroundTask scope, asyncio.Lock | Built-in |

---

## Metadata

**Analog search scope:** Phase 1 patterns/store.py, patterns/engine.py, core/config.py
**Pattern extraction date:** 2026-06-11
**Pattern authority:** RESEARCH.md (Patterns 1–4), Phase 1 PATTERNS.md (analogous structures)
**Integration status:** Depends on Phase 1 completion (store.insert_pattern, store.update_pattern, engine.apply_outcome, engine.INIT_CONFIDENCE)
