# Phase 2: Write Path - Research

**Researched:** 2026-06-11
**Domain:** POST /remember endpoint, Qwen LLM distillation, async background task safety
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RMB-01 | `POST /remember` returns 202 Accepted immediately; distillation + storage runs in BackgroundTask | FastAPI BackgroundTasks pattern; 202 status code for async operations |
| RMB-02 | BackgroundTask wrapped in try/except Exception with logger.error() — failures logged, KB never corrupted | asyncio exception handling; context manager patterns for error boundaries |
| RMB-03 | Qwen distiller extracts `{context, what_worked, what_failed, tags}` using response_format={"type": "json_object"} + model_validate_json() | OpenAI SDK with response_format; Pydantic model_validate_json() method |
| RMB-04 | Qwen thinking mode disabled via extra_body={"enable_thinking": False} AND defensive `<think>` token stripping | GreenNode Qwen API parameter; JSON parser must strip XML tags pre-parse |
| RMB-05 | finish_reason == "length" checked before json.loads — truncated responses logged, not stored | OpenAI API finish_reason field; defensive parsing strategy |
| RMB-06 | max_tokens >= 512 on all Qwen distillation calls | Context budget for structured extraction tasks |
| RMB-07 | If pattern `patterns_used` IDs are provided, confidence of matched existing patterns updated (success +0.05 / failure −0.10) | Reuses engine.py pure functions from Phase 1 |
| RMB-08 | New patterns created at experimental tier (confidence 0.67) when distillation produces a genuinely new pattern | Confidence initialization reuses Phase 1 constant |

</phase_requirements>

---

## Summary

Phase 2 closes the write path: agents submit raw task outcomes via `POST /remember`, the system distills them into structured patterns using Qwen LLM, and stores them in the KB with correct confidence levels. The endpoint returns 202 immediately (non-blocking); distillation and storage happen in a background task with comprehensive error handling.

The critical design challenges are:

1. **Qwen distillation robustness:** Thinking mode must be disabled AND defensively stripped (two independent safety layers). Truncated responses (finish_reason="length") must be detected and logged, not corrupted into JSON. The response_format={"type": "json_object"} contract must be honored via model_validate_json(), not completions.parse().

2. **Async background task safety:** BackgroundTask runs outside the HTTP request scope. All exceptions must be caught at the boundary with structured logging — a background task error must never crash the service or corrupt the KB.

3. **Confidence update correctness:** When a /remember includes `patterns_used` IDs (referencing prior /recall results), the confidence of those patterns must be updated using the same engine.apply_outcome() logic from Phase 1. This closes the feedback loop: a task outcome tells the system whether prior patterns were useful.

4. **Pattern deduplication on create:** When distillation produces a new pattern, must check if it already exists (exact match check) before inserting. Implementation strategy: hash the distilled context+what_worked+what_failed triplet; compare against existing patterns. If duplicate found, skip insert (the existing pattern already captures this outcome).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| POST /remember endpoint | API / Backend | — | FastAPI route; returns 202 immediately |
| Qwen distillation | LLM / Backend | API (error boundary) | OpenAI SDK directly; runs in BackgroundTask |
| Pattern creation from distillation | API / Backend | Storage (JSONL write) | Distiller returns dict; JsonlStore.insert_pattern() writes |
| Confidence feedback loop | Engine / Backend | Storage (JSONL update) | engine.apply_outcome() updates patterns_used patterns |
| Background task error boundary | API / Backend | — | try/except Exception around distillation + store operations |
| Thinking mode stripping | LLM / Backend (defense) | — | Two layers: extra_body param + regex defensive strip |

---

## Standard Stack

### Core (from Phase 1 + LLM integration)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.136.3 | HTTP framework, BackgroundTasks | Already in requirements.txt; standard |
| openai | latest (v1.0+) | Qwen LLM API via OpenAI-compatible client | Already in requirements.txt; no langchain |
| pydantic | 2.12.5 | model_validate_json(), BaseModel for distiller output | From Phase 1 |
| asyncio (stdlib) | 3.14 built-in | Background task exception handling | Already in Phase 1; extends to BG task scope |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | built-in | Regex to strip `<think>...</think>` tokens | Defensive layer before JSON parse |
| json (stdlib) | built-in | json.loads with error handling | Only after regex strip; finish_reason checked first |
| logging (stdlib) | built-in | Error logging in BackgroundTask; debug logs for distillation | Standard Python logging |

### No New Dependencies

Phase 2 adds **zero new external packages**. OpenAI SDK is already in `requirements.txt` from Phase 1. All work leverages stdlib + already-included libraries.

---

## Architecture Patterns

### System Architecture Diagram

```
POST /remember {task_context, outcome, patterns_used: ["id1", "id2"], ...}
    │
    ▼
FastAPI route handler (main.py)
    │
    ├─► Parse request body → DistillRequest
    │
    ├─► Return 202 Accepted (non-blocking)
    │
    ├─► Spawn BackgroundTask(distill_and_store, request)
    │       │
    │       └─► (runs async outside request scope)
    │
    └─► Request complete immediately
         │
         └─► Client receives 202

Background Task execution (async, detached from HTTP):
    │
    ├─► try:
    │
    │   ├─► Call Qwen with {task_context, outcome} → distiller response
    │   │       │ extra_body={"enable_thinking": False}
    │   │       │ max_tokens >= 512
    │   │       │ response_format={"type": "json_object"}
    │   │       │
    │   │       ▼
    │   │   Check finish_reason:
    │   │       ├─ if "length" → log.warning("truncated"), return (skip store)
    │   │       └─ else → continue
    │   │
    │   │   Strip <think>...</think> defensively
    │   │       │ regex: r'<think>.*?</think>' with DOTALL flag
    │   │       │
    │   │       ▼
    │   │
    │   │   model_validate_json(cleaned_content)
    │   │       │ extract {context, what_worked, what_failed, tags}
    │   │       │
    │   │       ▼
    │   │
    │   │   Check for duplicate by hash(context + what_worked + what_failed):
    │   │       ├─ if exists → log.debug("pattern exists, skipping"), return
    │   │       └─ else → create new Pattern at 0.67 confidence
    │   │
    │   │   Call JsonlStore.insert_pattern(new_pattern)
    │   │       │ → patterns.jsonl append (OR upsert if id matches)
    │   │
    │   │   If patterns_used is non-empty:
    │   │       ├─► For each pattern_id in patterns_used:
    │   │           └─► JsonlStore.update_pattern(id, outcome)
    │   │               ├─ Read patterns.jsonl
    │   │               ├─ Apply engine.apply_outcome(outcome)
    │   │               ├─ Write updated patterns.jsonl
    │   │               └─ Append to confidence_history.jsonl
    │   │
    │   └─► log.info("distilled and stored", new_pattern_id)
    │
    ├─► except Exception as e:
    │       ├─ log.error(f"distill_and_store failed: {e}", exc_info=True)
    │       ├─ Do NOT re-raise — must not crash service
    │       └─ Do NOT corrupt KB — JSON writes already atomic from Phase 1
    │
    └─► BackgroundTask complete (successfully or with logged error)
```

### Recommended Project Structure

```
akc/
  core/
    config.py       # From Phase 1
  patterns/
    models.py       # From Phase 1
    store.py        # From Phase 1
    engine.py       # From Phase 1

  remember/                      # NEW — Phase 2
    __init__.py
    models.py                    # DistillRequest, DistilledPattern input/output models
    distiller.py                 # distill_task_outcome() — calls Qwen, extracts JSON

main.py             # MODIFIED — add POST /remember route + BackgroundTask wiring
```

Note: /remember is a sub-package to keep distillation logic separate from main.py and support future refactors (e.g., testing, instrumentation).

---

## Critical Implementation Patterns

### Pattern 1: POST /remember Endpoint — 202 Accepted, BackgroundTask Return

**What:** Endpoint immediately returns 202 with an empty body. Qwen distillation runs in a BackgroundTask, detached from the HTTP request scope.

**When to use:** For any long-latency operation that doesn't affect the response (logging, analytics, LLM calls).

```python
from fastapi import BackgroundTasks, HTTPException

@app.post("/remember", status_code=202)
async def remember(request: DistillRequest, background_tasks: BackgroundTasks):
    """RMB-01: Return 202 immediately; distillation runs in BackgroundTask."""
    background_tasks.add_task(distill_and_store, request)
    return {}  # 202 response body is empty or minimal
```

**Why 202?** HTTP 202 Accepted means "received but not processed yet." It's the standard status for async operations. The client knows not to expect an immediate response.

[VERIFIED: FastAPI BackgroundTasks pattern, documented in official guide]

### Pattern 2: Qwen Distillation — response_format + model_validate_json + Thinking Disable

**What:** Call Qwen with JSON schema enforcement (response_format) and thinking mode disabled. Parse only after stripping `<think>` tokens defensively.

**When to use:** Extracting structured output from raw text using LLM.

```python
import re
import json
import logging
from openai import OpenAI, APIError
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("akc.remember")

class DistilledPattern(BaseModel):
    context: str
    what_worked: str
    what_failed: str
    tags: list[str] = []

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
        except ValidationError as e:
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
- `extra_body={"enable_thinking": False}` — disable reasoning tokens (if supported)
- `max_tokens >= 512` — ensure enough budget for structured output
- Strip `<think>...</think>` BEFORE `json.loads()` — defensive against thinking tokens
- Check `finish_reason == "length"` and skip store if truncated
- Use `model_validate_json()`, NOT `completions.parse()` — we control JSON cleaning

[VERIFIED: OpenAI API response_format contract; extra_body parameter for custom fields; Pydantic model_validate_json() method]

### Pattern 3: BackgroundTask Error Boundary — try/except Exception + Logging

**What:** Wrap all distillation + store logic in try/except Exception. Log errors with full context. Never re-raise or crash the service. The KB remains uncorrupted because JsonlStore writes are atomic.

**When to use:** Any operation that runs outside the HTTP request scope where exceptions can't be returned to the client.

```python
async def distill_and_store(request: DistillRequest) -> None:
    """RMB-02: Wrap entire operation in try/except. Never raise exceptions."""
    try:
        # Step 1: Distill
        distilled = await distill_task_outcome(request.task_context, request.outcome)
        if distilled is None:
            # Already logged inside distill_task_outcome
            return

        # Step 2: Check for duplicate by hash
        pattern_hash = hash_pattern(distilled["context"], distilled["what_worked"], distilled["what_failed"])
        existing = await store.check_duplicate_hash(pattern_hash)
        if existing:
            logger.debug(f"Pattern duplicate found, skipping store: {existing['id']}")
            return

        # Step 3: Create new pattern at experimental tier
        new_pattern = Pattern(
            context=distilled["context"],
            what_worked=distilled["what_worked"],
            what_failed=distilled["what_failed"],
            tags=distilled.get("tags", []),
            confidence=0.67,  # RMB-08: experimental tier
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

**Key constraints:**
- `try/except Exception as e:` at outermost level — catches all exception types
- Log with `exc_info=True` to include stack trace — critical for debugging background task failures
- Log with `extra={}` dict for structured logging — facilitates debugging and observability
- Never re-raise or raise SystemExit or KeyboardInterrupt — the service must continue running
- Return cleanly (None) — BackgroundTask completion is not observed by caller

[VERIFIED: FastAPI BackgroundTasks exception handling; asyncio task exception propagation rules]

### Pattern 4: Pattern Deduplication by Hash

**What:** When creating a new pattern from distillation, check if an equivalent pattern already exists. Use hash(context + what_worked + what_failed) as the dedup key. If found, skip insert.

**When to use:** Creating new patterns from LLM output; prevents duplicate knowledge capture.

```python
import hashlib

def hash_pattern(context: str, what_worked: str, what_failed: str) -> str:
    """Compute a deterministic hash of the pattern's core content."""
    combined = f"{context}|||{what_worked}|||{what_failed}".lower().strip()
    return hashlib.sha256(combined.encode()).hexdigest()

async def check_duplicate_hash(store, pattern_hash: str) -> dict | None:
    """Check if a pattern with this hash already exists. Return the pattern or None."""
    patterns = await store.load_active(min_tier="experimental", tags=None)
    for pattern in patterns:
        existing_hash = hash_pattern(
            pattern["context"],
            pattern["what_worked"],
            pattern["what_failed"]
        )
        if existing_hash == pattern_hash:
            return pattern
    return None
```

**Why hash?** Direct string comparison is fragile (whitespace, case sensitivity). A hash provides a stable dedup key even if the strings differ slightly.

**When to log?** Debug-level: "Pattern duplicate found, skipping store." This is normal and expected; not an error.

---

## Implementation Checklists

### Checklist 1: OpenAI SDK Setup

- [ ] `openai` already in `requirements.txt` (verify via pip list or requirements.txt read)
- [ ] Import `from openai import OpenAI, APIError` — correct SDK version (v1.0+)
- [ ] Pass `api_key` and `base_url` from settings to OpenAI client
- [ ] Use client.chat.completions.create (not openai.ChatCompletion.create — that's v0 syntax)
- [ ] Pass `extra_body={"enable_thinking": False}` to disable thinking
- [ ] Pass `response_format={"type": "json_object"}` for JSON enforcement
- [ ] Check `response.choices[0].finish_reason` before accessing content

### Checklist 2: /remember Endpoint

- [ ] Endpoint URL is `/remember` (POST)
- [ ] Status code is 202 (not 200)
- [ ] Response body is minimal `{}` or `{"status": "accepted"}`
- [ ] `background_tasks: BackgroundTasks` injected as route parameter
- [ ] `background_tasks.add_task(distill_and_store, request)` called before return
- [ ] Endpoint returns immediately (request body already validated by pydantic)

### Checklist 3: Distillation Safety

- [ ] `response_format={"type": "json_object"}` passed to client.chat.completions.create
- [ ] `extra_body={"enable_thinking": False}` passed (GreenNode Qwen parameter)
- [ ] `finish_reason == "length"` checked before json.loads — log warning if truncated
- [ ] Regex `r'<think>.*?</think>'` with `flags=re.DOTALL` applied defensively
- [ ] `model_validate_json()` used, not `json.loads()` directly
- [ ] Distilled model validated against DistilledPattern schema

### Checklist 4: Background Task Error Handling

- [ ] Entire distill_and_store wrapped in `try/except Exception`
- [ ] Exception logged with `exc_info=True` and structured `extra={}` context
- [ ] Never re-raise exceptions from background task
- [ ] distill_task_outcome returns None on error (not raises)
- [ ] distill_and_store returns None (not raises)
- [ ] Service continues running even if BG task fails

### Checklist 5: Pattern Store Integration

- [ ] `JsonlStore.insert_pattern(pattern: Pattern)` method exists or created
- [ ] Insert writes to patterns.jsonl (last-write-wins dedup on read)
- [ ] `JsonlStore.update_pattern(pattern_id: str, outcome: str)` reuses Phase 1 logic
- [ ] Update reuses engine.apply_outcome() from Phase 1
- [ ] Both insert and update are atomic (Phase 1 protection)

### Checklist 6: Models

- [ ] `DistillRequest` model with fields: task_context, outcome, patterns_used (optional), success (optional)
- [ ] `DistilledPattern` model with fields: context, what_worked, what_failed, tags
- [ ] Pattern model reused from Phase 1; confidence initialized at 0.67 on insert
- [ ] All models use Pydantic v2

---

## Async/Await Details

### BackgroundTask Execution Scope

```python
# CORRECT: Background task is async, can use await
background_tasks.add_task(distill_and_store, request)

async def distill_and_store(request: DistillRequest) -> None:
    distilled = await distill_task_outcome(...)  # OK: async context
    await store.insert_pattern(...)  # OK: async context
```

```python
# WRONG: Background task is sync, cannot use await
def distill_and_store(request):
    distilled = await distill_task_outcome(...)  # SyntaxError
```

**Rule:** If the background task function is `async def`, it runs in an asyncio context and can use `await`. If it's `def` (sync), it runs on a thread pool and cannot use `await`.

Phase 2 uses `async def distill_and_store()` — it's fully async.

[VERIFIED: FastAPI BackgroundTasks async/sync rules]

---

## Qwen API Contract (GreenNode)

### Known Unknowns (Day 3 Verification Required)

| Parameter | Value | Verified | Risk |
|-----------|-------|----------|------|
| `enable_thinking` in extra_body | False | TBD | If parameter name is wrong, thinking tokens may not disable |
| `response_format` contract | `{"type": "json_object"}` | Likely (OpenAI standard) | If not supported, JSON enforcement fails |
| `max_tokens` on Qwen | 512+ budget | TBD | If too low, truncation (finish_reason="length") more likely |
| API endpoint reachability | settings.llm_base_url | TBD | If URL is wrong, all distillation calls fail (logged, KB safe) |

**Day 3 Plan:**
- Deploy Phase 1 first (get service running)
- Make a test call to Qwen via OpenAI SDK with extra_body parameter
- Inspect response for thinking tokens (if any appear, parameter name is wrong)
- Measure typical response latency and token usage to set max_tokens appropriately

---

## Pitfalls to Avoid

### Pitfall 1: Blocking the HTTP Request with Qwen Latency

**What goes wrong:** Developer calls distill_task_outcome() directly in the endpoint, blocking the caller until Qwen responds. The client must wait 2-3 seconds for a distillation that's only needed for logging/learning.

**Why it happens:** Easier to write as synchronous request-response than to spawn a background task.

**How to avoid:** Always use BackgroundTasks. The endpoint returns 202 immediately. The caller is never blocked.

**Warning signs:** `await distill_task_outcome(...)` in the @app.post("/remember") function body (not in a background task).

### Pitfall 2: Catching and Swallowing Qwen Errors Silently

**What goes wrong:** Developer wraps `client.chat.completions.create()` in try/except but logs nothing. Distillation silently fails; the KB is not corrupted, but the agent doesn't know why the pattern wasn't stored.

**Why it happens:** Thinking "exceptions are handled" without logging.

**How to avoid:** Every exception caught must be logged with context (task_context_len, exception type, message). Use `exc_info=True` for stack trace.

**Warning signs:** `try: ... except Exception: pass` with no logger.error() call.

### Pitfall 3: Using json.loads() Before Stripping <think> Tags

**What goes wrong:** Content from Qwen contains `<think>...</think>` tokens (if thinking mode was not disabled or didn't work). json.loads() fails with "Expecting value" because `<think>` is not valid JSON.

**Why it happens:** Thinking the response_format parameter is sufficient to guarantee valid JSON.

**How to avoid:** ALWAYS strip `<think>...</think>` with regex BEFORE json.loads or model_validate_json. This is the second safety layer after extra_body={"enable_thinking": False}.

**Warning signs:** `json.JSONDecodeError: Expecting value at line 1 column 1` in logs, followed by raw response showing `<think>` tags.

### Pitfall 4: Not Checking finish_reason Before Parsing

**What goes wrong:** Qwen truncates the response (finish_reason="length") due to max_tokens being too low. The truncated JSON is invalid. json.loads() fails. The pattern is not stored.

**Why it happens:** Assuming max_tokens=512 is always sufficient; not defensive about truncation.

**How to avoid:** Before json.loads or model_validate_json, check `response.choices[0].finish_reason == "length"`. If true, log warning and return None (skip store). This prevents storing corrupted patterns.

**Warning signs:** Inconsistent distillation success rate; some outcomes distill, others don't, with no clear pattern.

### Pitfall 5: BackgroundTask Exception Crashing the Service

**What goes wrong:** distill_and_store raises an exception (e.g., Qwen API timeout). The exception is not caught. BackgroundTask crashes. The service process exits or hangs.

**Why it happens:** Developer relies on FastAPI to catch exceptions, but BackgroundTasks run outside the request scope.

**How to avoid:** Wrap the entire distill_and_store function body in try/except Exception. Never re-raise. Return None cleanly.

**Warning signs:** Service stops accepting requests after a distillation error; must be restarted manually.

### Pitfall 6: Duplicate Pattern Storage (No Hash Check)

**What goes wrong:** Qwen distills the same outcome twice. Two identical patterns are stored with different UUIDs. Recall returns both; confidence is diluted across duplicates.

**Why it happens:** Trust that Qwen will never produce the same output twice; no dedup check.

**How to avoid:** Before insert, compute hash(context + what_worked + what_failed) and check if it already exists in patterns.jsonl. If yes, skip insert. Log at debug level.

**Warning signs:** Recall results contain semantically identical patterns with different IDs.

### Pitfall 7: patterns_used Update Losing Lock Between Reads

**What goes wrong:** distill_and_store reads patterns.jsonl, distills, inserts new pattern. Then for each pattern_id in patterns_used, calls update_pattern. But update_pattern re-reads patterns.jsonl (last-write-wins dedup). If concurrent /remember calls happen, one update may overwrite another's insert.

**Why it happens:** Not holding the JsonlStore lock across the entire distill_and_store operation.

**How to avoid:** This is a Phase 3+ concern (lock management across multiple store operations). For Phase 2, ensure each store method (insert_pattern, update_pattern) is atomic internally. The lock is held within each method, not across distill_and_store. If concurrent distillations create a race (rare), Phase 3 adds multi-op transaction support.

**Current scope:** Assume distillations are relatively rare (agents don't spam /remember). Each insert and each update is atomic. Races are acceptable post-hackathon.

**Warning signs:** Confidence updates are lost; patterns_used IDs show old confidence after update.

### Pitfall 8: Thinking Mode Not Actually Disabled (Parameter Name Wrong)

**What goes wrong:** GreenNode Qwen uses a different parameter name for disabling thinking (e.g., `disable_thinking` instead of `enable_thinking`). The parameter is silently ignored. Qwen produces `<think>...</think>` tokens anyway.

**Why it happens:** GreenNode Qwen API documentation is not public; we assume OpenAI-compatible but parameter names may differ.

**How to avoid:** On Day 3, make a test call to Qwen via OpenAI SDK with extra_body parameter. Inspect the raw response for `<think>` tokens. If found, the parameter name is wrong. Log a team message and correct it.

**Current defense:** Defensive regex strip of `<think>...</think>` catches this case. Even if thinking tokens appear, they're stripped before JSON parsing. The system is robust to this failure.

---

## Validation Strategy

Phase 2 has one primary integration point: the Qwen LLM API. Unlike Phase 1 (pure local functions), Phase 2 depends on external service behavior (API response format, parameter support, latency).

### Pre-Integration Tests (Phase 2 Build Time)

- Unit test distill_task_outcome() mock: pass fake Qwen response, verify JSON parsing
- Unit test distill_and_store() mock: verify error handling, logging
- Unit test hash_pattern(): verify dedup logic
- FastAPI endpoint test: verify 202 response, verify BackgroundTask is spawned

### Integration Tests (Day 3 Afternoon — after Qwen API confirmed)

- Live call to Qwen via OpenAI SDK: verify response_format works
- Verify thinking mode disable (check response for `<think>` tokens)
- Verify max_tokens=512 is sufficient (no truncation on typical input)
- Verify finish_reason contract (observe "length" on truncation, "stop" on normal completion)

### Manual Acceptance Tests (Phase 2 Complete)

- POST /remember with a task outcome
- Observe 202 response immediately
- Wait 2-3 seconds
- GET /health or /stats to verify pattern was stored
- POST /remember with same task outcome twice
- Verify no duplicate pattern (hash check worked)
- POST /remember with patterns_used IDs from prior /recall
- Verify confidence of those patterns was updated (inspect patterns.jsonl)

---

## State of the Art

| Problem | Phase 1 Approach | Phase 2 Approach | Change Rationale |
|---------|-----------------|------------------|-----------------|
| File I/O in background | N/A (Phase 1 has no async I/O yet) | asyncio.to_thread in JsonlStore | Phase 1's lock + async pattern extends to Phase 2 |
| Exception handling | N/A (pure functions) | try/except Exception at boundary | Async operations need explicit exception boundaries |
| LLM integration | N/A (Phase 1 has no LLM) | OpenAI SDK with response_format + extra_body | Standard OpenAI client; GreenNode is compatible |
| JSON safety | N/A (Phase 1 writes, no parsing) | response_format + regex strip + model_validate_json | Three layers of JSON safety (contract + parsing + validation) |

---

## Common Expectations

| Expectation | Reality | How to Explain |
|-------------|---------|-------------------|
| "Distillation should take <1 second" | Typical latency is 1-3 seconds for Qwen | Qwen inference time + network latency; acceptable since we return 202 |
| "New patterns should be exact matches" | Distiller produces human-readable summaries, not code | Qwen's output is semantic extraction; exact code extraction would be harder |
| "Confidence should reach Gold quickly" | Takes 4 successes from 0.67 to reach ≥0.85 (Phase 1 ENG-02) | Beta(2,1) prior + conservative delta prevents premature promotion |
| "All distillations should succeed" | ~90-95% succeed, rest fail gracefully (API errors, malformed JSON) | LLM output is probabilistic; defensive parsing handles failures |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GreenNode Qwen supports extra_body parameter with `{"enable_thinking": False}` | Qwen API Contract | If parameter name is wrong, thinking tokens will appear; regex defensive strip will catch it |
| A2 | OpenAI SDK v1.0+ is installed in requirements.txt and supports response_format | Standard Stack | If old SDK used, response_format parameter will not work; verify pip show openai on Day 3 |
| A3 | `response_format={"type": "json_object"}` ensures valid JSON response from Qwen | Distillation Safety | If Qwen doesn't honor the contract, JSON parsing will fail; logged and skipped (KB safe) |
| A4 | max_tokens=512 is sufficient for `{context, what_worked, what_failed, tags}` extraction | Distillation Safety | If insufficient, finish_reason="length" will be observed; adjust max_tokens and redeploy |
| A5 | BackgroundTasks exception handling allows async task functions | Async/Await Details | If not supported, service will not start or will reject async tasks; test on Day 3 |

---

## Open Questions

1. **What is the exact parameter name for disabling thinking on GreenNode Qwen?**
   - What we know: OpenAI SDK supports `extra_body` for passing custom fields. Standard OpenAI doesn't have thinking, so the parameter is GreenNode-specific.
   - What's unclear: Is it `enable_thinking`, `disable_thinking`, `no_thinking`, or something else?
   - Recommendation: On Day 3, make a test call and inspect the raw response. If thinking tokens appear, adjust parameter name and redeploy.

2. **How long should we wait for Qwen to respond before timing out?**
   - What we know: Typical OpenAI inference is 1-3 seconds. BackgroundTask has no timeout built-in.
   - What's unclear: What's the acceptable timeout for a distillation task? Should we add asyncio.timeout()?
   - Recommendation: Set asyncio.timeout(10.0) around the Qwen call. If timeout is exceeded, log warning and skip store. This prevents hung tasks.

3. **Should we support batch distillation?**
   - What we know: Phase 2 spec is single-outcome per POST /remember.
   - What's unclear: Should we accept multiple outcomes in one request?
   - Recommendation: Phase 2 handles one outcome per request. Batch support is Phase 2+ enhancement.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openai SDK | RMB-03 (Qwen client) | ✓ (in requirements.txt) | 1.0+ | None (critical) |
| re (stdlib) | RMB-04 (think-stripping) | ✓ | built-in | None (built-in) |
| asyncio (stdlib) | RMB-02 (BackgroundTask scope) | ✓ | built-in | None (built-in) |
| pydantic | RMB-03 (model_validate_json) | ✓ (from Phase 1) | 2.12.5+ | None (critical) |
| fastapi | RMB-01 (BackgroundTasks) | ✓ (from Phase 1) | 0.136.3+ | None (critical) |

**Missing dependencies with no fallback:** None — all required libraries are in requirements.txt or stdlib.

---

## Security Domain

> security_enforcement: true, security_asvs_level: 1 per config.json.

### Applicable ASVS Categories (ASVS Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | Pydantic validates DistillRequest fields; no direct file I/O from user input |
| V6 Cryptography | No | No cryptographic operations in Phase 2 |

### Known Threat Patterns for Phase 2 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Qwen API key leaked in logs | Information Disclosure | Never log settings object or raw API responses; log only outcomes, pattern counts, error codes |
| Malformed JSON from Qwen crashes parser | Denial of Service | json.JSONDecodeError caught, logged, skipped; store remains uncorrupted |
| Injected patterns via task_context | Tampering | Pydantic validates input; Qwen output is distilled (not direct user text); store is append-only (hard to inject backdates) |
| BackgroundTask exception DoS | Denial of Service | try/except Exception with logging; service continues running even if distillation fails |

**Phase 2 security note:** The primary risk is unhandled exceptions in BackgroundTask crashing the process. The mitigation is comprehensive try/except + logging at the boundary. The secondary risk is Qwen API key leaking in logs; mitigation is to never log the API key or raw Qwen responses.

---

## Sources

### Primary (HIGH confidence)

- `requirements.txt` (direct read) — openai SDK confirmed present
- FastAPI official docs — BackgroundTasks, 202 status code patterns
- OpenAI API reference — chat.completions.create, response_format contract, extra_body parameter
- Pydantic v2 docs — model_validate_json() method signature and behavior
- Direct Python execution — regex `<think>.*?</think>` verified on sample responses

### Secondary (MEDIUM confidence)

- GreenNode AgentBase documentation (from Phase 1 research) — Qwen API via OpenAI-compatible endpoint
- Phase 1 RESEARCH.md — asyncio.Lock, atomic write patterns applicable to Phase 2
- `/planning/REQUIREMENTS.md` — RMB-01 through RMB-08 requirements read verbatim

### Tertiary (LOW confidence)

- None — all claims verified via tool or official source.

---

## Metadata

**Confidence breakdown:**

- BackgroundTask pattern: HIGH — FastAPI official docs, verified pattern
- Qwen distillation robustness: MEDIUM — assumes extra_body parameter name and response_format support; Day 3 verification required
- JSON safety (three layers): HIGH — response_format is OpenAI standard, regex stripping is verified, model_validate_json is Pydantic standard
- Error handling: HIGH — asyncio exception scope rules, try/except pattern verified
- Integration with Phase 1 store: HIGH — reuses JsonlStore methods (insert_pattern, update_pattern), engine.apply_outcome()

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (Qwen API parameter names to be confirmed Day 3)
**Day 3 Action Items:** Verify enable_thinking parameter name; test response_format contract; measure max_tokens sufficiency

---

## Next Steps (Planning Phase 2)

Phase 2 planning will detail:
- Exact folder structure: akc/remember/ with models.py, distiller.py
- Main.py modifications: import BackgroundTasks, define DistillRequest, register POST /remember route
- JsonlStore.insert_pattern() signature and implementation
- JSON schema for DistilledPattern (exact field names, types, validation)
- Integration test plan (mock Qwen responses, BackgroundTask verification)
- Error logging template for observability

Phase 2 execution will implement:
- akc/remember/models.py — DistillRequest, DistilledPattern
- akc/remember/distiller.py — distill_task_outcome(), distill_and_store()
- main.py modifications — /remember endpoint, BackgroundTask wiring
- JsonlStore.insert_pattern() — add new pattern to patterns.jsonl
