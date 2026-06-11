# Domain Pitfalls — AKC (Agent Knowledge Collective)

**Domain:** Self-improving knowledge API — FastAPI + JSONL + LLM distillation + AgentBase
**Researched:** 2026-06-11
**Confidence:** HIGH (all critical pitfalls verified against official docs + real bug reports)

---

## Critical Pitfalls

Mistakes that cause rewrites, silent data loss, or demo failure.

---

### Pitfall 1: BackgroundTask Errors Are Silently Swallowed

**What goes wrong:**
FastAPI's `BackgroundTasks` runs the distillation+store pipeline after returning 202 Accepted. Any exception inside that pipeline — Qwen API timeout, JSON parse failure, file write error — is caught by the framework and **not re-raised, not logged, not surfaced anywhere** unless you add explicit handling. The caller sees a clean 202; internally the pattern was never stored.

**Why it happens:**
BackgroundTasks execute outside the request/response scope. Middleware exception handlers do not wrap them (confirmed in [fastapi/fastapi discussion #11828](https://github.com/fastapi/fastapi/discussions/11828)). The framework treats the background coroutine as a fire-and-forget; uncaught exceptions print a bare traceback to stderr at best.

**Consequences:**
- `/remember` returns 202 but nothing is stored
- `/stats` shows no growth; confidence never updates
- Demo loop appears to work (no error) but KB stays empty
- Zero debugging signal in logs

**Prevention:**
Wrap the entire background task body in a try/except with structured logging:

```python
async def _distill_and_store(request: RememberRequest):
    try:
        pattern = await distiller.extract(request)
        await store.append(pattern)
        await engine.update_confidence(pattern.id, request.outcome)
    except Exception as exc:
        logger.error("background_task_failed", exc_info=exc,
                     task_context=request.task_context[:100])
        # optionally: write a failed-distillation marker to confidence_history.jsonl
```

Never let the background function body be bare.

**Warning signs:**
- `/stats` shows `total_outcomes_recorded` incrementing but `total_patterns` stays flat
- No errors in HTTP access log (which only covers the 202 response, not the background work)

**Build phase:** Day 1 (remember/router.py skeleton) — add the wrapper before wiring Qwen. It is nearly free to add early and painful to retrofit.

---

### Pitfall 2: JSONL Concurrent Write Corruption

**What goes wrong:**
Multiple simultaneous `/remember` calls trigger multiple BackgroundTasks that all call `store.append()`. Without a lock, two coroutines can both open the file, both seek to the end, and interleave writes — producing a corrupted line (two JSON objects on the same line) or a torn write where one entry is partially overwritten.

**Why it happens:**
`asyncio.Lock` only prevents concurrent access within one event loop (one process, one thread). However, even within a single-worker uvicorn process, two background tasks advancing simultaneously can produce interleaved writes if the file open+seek+write is not atomic from the event loop's perspective. The reference codebase (`akc-service`) uses `fcntl.flock(LOCK_EX)` for this reason — it was a solved problem in the prior implementation.

**Consequences:**
- `json.JSONDecodeError` on the corrupted line when `/recall` reads back patterns
- `/stats` crashes or returns wrong counts
- Lost patterns — only the last writer's data survives the interleaved write

**Prevention:**
Use a module-level `asyncio.Lock` in `patterns/store.py` guarding every write path:

```python
_write_lock = asyncio.Lock()

async def append(pattern: Pattern, filepath: Path) -> None:
    async with _write_lock:
        async with aiofiles.open(filepath, "a", encoding="utf-8") as f:
            await f.write(pattern.model_dump_json() + "\n")
```

One lock instance per process is correct for the single-KB MVP. This is the asyncio-safe equivalent of the `fcntl.flock(LOCK_EX)` pattern in the reference codebase.

**Warning signs:**
- `JSONDecodeError` on line N of patterns.jsonl where N > 1
- Pattern count in file is lower than expected after a burst of `/remember` calls

**Build phase:** Day 2 (patterns/store.py) — add the lock at the same time as the append function. The reference codebase has this solved with fcntl; port that pattern.

---

### Pitfall 3: Qwen Thinking Mode Injects `<think>` Into JSON Output

**What goes wrong:**
Qwen 3.x models ship with reasoning/thinking mode **enabled by default** in many deployment configurations. When `response_format: json_schema` is set alongside thinking mode, the model prepends a `<think>...</think>` block of 50–800 reasoning tokens before the JSON payload. The JSON parser receives `<think>...` as its first bytes and throws `JSONDecodeError` immediately.

**Why it happens:**
Confirmed via HuggingFace Qwen3.5-35B-A3B discussion #18 and the DEV community post on Qwen 3.6. The conflict is between two simultaneous features: `enable_thinking=True` (default-on in some serving configs) and `response_format=json_schema`. When both activate, reasoning content leaks into `message.content` rather than being isolated in `reasoning_content`.

**Consequences:**
- Every distillation call fails
- BackgroundTask swallows the error (Pitfall 1 compounds this)
- KB never populates; demo is dead on arrival

**Prevention:**
Three layers:

1. **Disable thinking explicitly at the API call level** — pass `extra_body={"enable_thinking": False}` in the OpenAI-compatible client call, or set `"thinking": {"type": "disabled"}` in the request body depending on the GreenNode MaaS parameter surface.

2. **Strip `<think>` defensively regardless** — even with thinking disabled, add a pre-parse strip:
   ```python
   import re
   def _strip_think(raw: str) -> str:
       return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
   ```

3. **Validate before parsing** — wrap `json.loads` and on failure attempt `_strip_think` + retry before escalating:
   ```python
   def safe_json_parse(raw: str) -> dict:
       try:
           return json.loads(raw)
       except json.JSONDecodeError:
           cleaned = _strip_think(raw)
           return json.loads(cleaned)  # raises if still malformed
   ```

**Warning signs:**
- `JSONDecodeError` with position 0 (parser failed on first character)
- Response content starting with `<` when inspected in logs

**Build phase:** Day 3 (remember/distiller.py) — both the `enable_thinking` API parameter and the defensive strip must be in the first working version of the distiller. Do not ship a distiller without them.

---

### Pitfall 4: Qwen Response Truncated Mid-JSON (Token Budget)

**What goes wrong:**
The distilled Pattern schema has 8+ fields (`id`, `context`, `what_worked`, `what_failed`, `tags`, `confidence`, `tier`, `times_applied`). If `max_tokens` is too low, the model stops generating mid-structure — producing `{"id": "pat_001", "context": "...", "what_worked": "...` with no closing brace. `json.loads` fails.

**Why it happens:**
The model's `finish_reason` will be `"length"` rather than `"stop"`. This is a configuration problem, not a model intelligence problem. Confirmed as a known structured output failure mode for all OpenAI-compatible APIs.

**Consequences:**
- Distillation silently discards the incomplete pattern (Pitfall 1 multiplier)
- Large or verbose outcomes (long `what_happened` field) fail more often than short ones

**Prevention:**
- Set `max_tokens` to at least 512 for distillation calls (the structured Pattern JSON is ~200–300 tokens)
- Check `response.choices[0].finish_reason` — if `"length"`, log a warning and skip storage rather than attempting parse
- Keep the distillation prompt terse; instruct the model to use short strings in `what_worked`/`what_failed`

**Warning signs:**
- `finish_reason == "length"` in Qwen API response
- `JSONDecodeError` at a high character offset (parser succeeded partway through)

**Build phase:** Day 3 (remember/distiller.py) — add `finish_reason` check alongside the `safe_json_parse` wrapper.

---

### Pitfall 5: Docker Container Restart Wipes JSONL Data

**What goes wrong:**
If `kb/patterns.jsonl` and `kb/confidence_history.jsonl` are written to the container filesystem (not a mounted volume), every container restart — deployment update, crash-restart, AgentBase rebalancing — destroys all accumulated patterns. The KB resets to empty.

**Why it happens:**
Docker's container layer is ephemeral. Data written to `/app/data/` inside the container does not persist unless that path is mounted to a host volume or external storage. This is the most common beginner Docker data loss scenario and is explicitly called out in Docker's own getting-started docs.

**Consequences:**
- All patterns and confidence history lost on redeploy
- Demo loop must be re-run from scratch after any container bounce
- On AgentBase, where container scheduling is managed by the platform, a container restart during the demo would be catastrophic

**Prevention:**
In `Dockerfile`, declare the data directory as a volume:
```dockerfile
VOLUME ["/app/data"]
```

In `docker-compose.yml` (local dev and CI):
```yaml
volumes:
  - akc_kb:/app/data
volumes:
  akc_kb:
```

Set `KB_DIR` env var to `/app/data` (or the mounted path). Verify `config.py` reads this from the environment.

On AgentBase: check whether the platform provides persistent volume mounts or ephemeral-only containers. If ephemeral-only, seed a known-good KB state into the image itself as a fallback for demo stability.

**Warning signs:**
- `/stats` returns `total_patterns: 0` after a deploy
- `patterns.jsonl` exists in the image but is empty

**Build phase:** Day 5 (Dockerfile + deploy) — volume configuration must be in the Dockerfile and docker-compose.yml before first deploy. Also add a startup log line showing `KB_DIR` path and current pattern count so data persistence is immediately visible.

---

### Pitfall 6: AgentBase Memory Service — Unknown Rate Limits and Latency

**What goes wrong:**
The AgentBase Memory Service is the semantic similarity backend for `/recall`. Its rate limits, per-call latency, and failure modes are not publicly documented. If it imposes rate limits or has cold-start latency (first call in a session warms up), `/recall` may return HTTP 429 or timeout silently during the demo.

**Why it happens:**
This is a managed platform service with no published SLA in the available documentation. GreenNode's product page describes the Memory Service but does not specify rate limits, concurrent request limits, or per-call latency bounds.

**Consequences:**
- `/recall` returns empty results or fails during demo
- The entire self-improvement loop breaks at the query side
- Rate limiting during load tests could cause false failures in CI

**Prevention:**
Build the integration with a hard timeout and a local-fallback path:

```python
async def semantic_recall(context: str, top_k: int) -> list[Pattern]:
    try:
        async with asyncio.timeout(2.0):  # 2s hard cap
            return await memory_service.search(context, top_k)
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("memory_service_unavailable", exc_info=exc)
        return []  # fall back to tag-only local search
```

The local fallback — filter by `min_tier` + tags from JSONL — should always work independent of the Memory Service. This is the correct degraded-mode behavior for a hackathon deployment.

**Warning signs:**
- HTTP 429 from the Memory Service during `/recall`
- `/recall` response time spikes to 5+ seconds
- Empty results from `/recall` even when JSONL contains matching patterns

**Build phase:** Day 4 (core/memory.py) — design with the timeout+fallback from day one. Do not wire `/recall` to depend on the Memory Service with no fallback; the JSONL local path must always be the safety net.

---

## Moderate Pitfalls

### Pitfall 7: Confidence Scoring — Demoted Pattern Permanently Excluded at Experimental Tier

**What goes wrong:**
The PRD specifies that demoted patterns (confidence < 0.50) never auto-promote. However, the Beta distribution's prior is `(alpha=1, beta=1)`, which means a brand-new pattern starts at `1/(1+1) = 0.50` — exactly at the Experimental floor, not safely above it. One failure before any success pushes it to `1/3 = 0.33`, directly into Demoted territory. The pattern is permanently suppressed after one bad first outcome.

**Why it happens:**
The Beta(1,1) prior is uniform — it treats success and failure as equally likely. At very small evidence counts (N=2, N=3), the variance is high and a single failure swing is large enough to cross the 0.50 boundary.

**Consequences:**
- New patterns that fail on first try are permanently lost (no retry possible)
- Demo "Act 1 — cold start failure" records a failure as the first event → the pattern immediately demotes → Act 2 cannot retrieve it
- The demo script as written in PRD Section 10 **will break** unless the first-failure-then-success scenario is accounted for

**Prevention:**
Two options (choose one):
1. **Set new pattern initial confidence to 0.60** rather than 0.50, giving one failure buffer before Demoted threshold
2. **Use a stronger prior**: Beta(2,1) starts at `2/3 = 0.67` (Experimental, safely above floor); one failure moves it to `2/4 = 0.50` (still not demoted); two failures demotes

Option 2 is more principled and matches the PRD's stated goal that "one failure doesn't kill a proven pattern." Apply the same principle to new patterns.

**Warning signs:**
- `/stats` shows experimental patterns disappearing rapidly without any visible success history
- Demo Act 2 shows 0 patterns returned even after Act 1 recorded a failure

**Build phase:** Day 2 (patterns/engine.py) — when implementing `create_pattern()`, set initial prior to Beta(2,1) or initial confidence to 0.60.

---

### Pitfall 8: Gold Exit Guardrail — `consecutive_failures` Counter Not Persisted

**What goes wrong:**
The PRD specifies a Gold exit guardrail requiring 3 consecutive failures before a Gold pattern drops tier. The `consecutive_failures` field must be persisted in JSONL. If it is only held in memory (e.g., on the Pattern object during the request lifecycle), it resets to 0 on every container restart. A Gold pattern that received 2 failures then a restart will never exit Gold, even under sustained failure.

**Why it happens:**
It is easy to implement the counter as a Python attribute on an in-memory object without ensuring it is written to `patterns.jsonl` on every confidence update. If the store's `update()` method only writes delta fields, `consecutive_failures` may be missed.

**Prevention:**
Add `consecutive_failures: int = 0` to the Pattern model in `patterns/models.py` and ensure `store.update()` writes the entire updated Pattern record (not just confidence fields) on every outcome.

**Warning signs:**
- After a container restart, a Gold pattern that was "on notice" (1 or 2 consecutive failures) behaves as though it had zero failures
- `consecutive_failures` not visible in patterns.jsonl entries

**Build phase:** Day 2 (patterns/models.py and patterns/store.py) — add the field to the Pydantic model at model-definition time.

---

### Pitfall 9: `/remember` Accepts But Never Processes — No Observability

**What goes wrong:**
The 202 Accepted contract explicitly decouples receipt from processing. Without a metrics counter or status field, there is no way to know how many submitted outcomes were successfully distilled vs. silently dropped. During the demo, if distillation starts failing (Qwen timeout, token budget exceeded), the service continues accepting requests and returning 202 while building up a queue of unprocessed work.

**Prevention:**
Track two counters in an in-memory dict (or as two fields in a simple status module):
- `outcomes_submitted` — incremented when 202 is returned
- `outcomes_stored` — incremented when `store.append()` completes successfully

Expose both in `GET /stats`. The gap between them is the distillation failure rate. This is also the most compelling demo signal — you can show the system is healthy by showing zero gap.

**Build phase:** Day 5 (stats/service.py + remember/service.py) — add the counters when building the stats endpoint.

---

## Minor Pitfalls

### Pitfall 10: Cold Start Demo — Empty KB Returns Confusing Results

**What goes wrong:**
`POST /recall` on an empty KB returns `{"patterns": [], "total_found": 0}`. This is correct behavior but can look like a failure to a judge watching the demo. The demo script (PRD Section 10) accounts for this in Act 1, but if the KB is unexpectedly empty mid-demo (e.g., after a container restart), the loop silently breaks.

**Prevention:**
- Add a clear message to the recall response when KB is empty: `"kb_status": "empty"` alongside the empty patterns list
- Seed the KB with 2–3 pre-seeded "bootstrap" patterns at startup if `patterns.jsonl` is empty — these make the first `/recall` return something useful and demonstrate the system's intended behavior immediately
- In the demo environment, keep a `kb_snapshot.jsonl` as a backup that can be copied into place if the live KB resets

**Build phase:** Day 6 (demo prep) — prepare seed data and the startup check.

---

### Pitfall 11: `POST /kb/export` on Large KB Blocks the Event Loop

**What goes wrong:**
The export endpoint reads all patterns from JSONL and renders them as markdown in a single synchronous pass. On a large KB this will block the uvicorn event loop for hundreds of milliseconds, causing all concurrent requests to stall.

**Prevention:**
Use `aiofiles` for the file read, or run the export in a thread pool executor. For hackathon scale (< 500 patterns), this is acceptable risk — call it out and defer.

**Build phase:** Day 5 — note as known limitation; acceptable for demo scale.

---

### Pitfall 12: Tag Matching Case Sensitivity

**What goes wrong:**
`POST /remember` with tag `"Python"` creates a pattern; `POST /recall` with tag `"python"` misses it. Tags are compared as plain strings unless normalized.

**Prevention:**
Normalize all tags to lowercase in `patterns/models.py` before storage. Add a `@validator` or `@field_validator` on the `tags` field.

**Build phase:** Day 2 (patterns/models.py) — one-liner validator.

---

## Phase-Specific Warnings

| Build Day | Topic | Likely Pitfall | Mitigation |
|-----------|-------|---------------|------------|
| Day 1 | remember/router.py | BackgroundTask silent failure (Pitfall 1) | Wrap task body in try/except + logger before wiring anything else |
| Day 2 | patterns/store.py | Concurrent JSONL corruption (Pitfall 2) | Module-level asyncio.Lock on all write paths |
| Day 2 | patterns/engine.py | First-failure demotes new pattern (Pitfall 7) | Initial prior Beta(2,1) or confidence 0.60 |
| Day 2 | patterns/models.py | consecutive_failures not persisted (Pitfall 8) | Add field to Pydantic model on day 2 |
| Day 3 | remember/distiller.py | Qwen thinking mode injects `<think>` (Pitfall 3) | Disable thinking + defensive strip both required |
| Day 3 | remember/distiller.py | Qwen truncates mid-JSON (Pitfall 4) | Set max_tokens 512+, check finish_reason |
| Day 4 | core/memory.py | Memory Service rate limit / latency (Pitfall 6) | 2s timeout + local JSONL fallback, always |
| Day 5 | Dockerfile | Container restart wipes JSONL (Pitfall 5) | VOLUME declaration + verify KB_DIR env var |
| Day 5 | stats/service.py | No observability on background failures (Pitfall 9) | submitted vs. stored counter gap |
| Day 6 | demo prep | Empty KB mid-demo (Pitfall 10) | Seed data + KB backup snapshot |

---

## Sources

- [FastAPI BackgroundTasks silent failures — fastapi/fastapi discussion #11828](https://github.com/fastapi/fastapi/discussions/11828)
- [FastAPI Background Tasks Were Silently Failing — blog.cubed.run](https://blog.cubed.run/fastapi-background-tasks-were-silently-failing-here-is-the-fix-e734740b5f11)
- [FastAPI BackgroundTasks docs — fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Qwen 3.6 enable_thinking MoE pitfall broke agent JSON parsing — DEV Community](https://dev.to/sleepyquant/qwen-36-enablethinking-the-moe-pitfall-that-broke-my-agent-json-parsing-71a)
- [Qwen3.5-35B-A3B reasoning content leaks into message.content — HuggingFace discussion #18](https://huggingface.co/Qwen/Qwen3.5-35B-A3B/discussions/18)
- [Enforce Structured JSON Output with Qwen Models — Alibaba Cloud](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output)
- [Structured Output response truncation — OpenAI Community](https://community.openai.com/t/structured-output-issue-in-gpt-4o-api-response-truncation-at-specific-index/1146715)
- [JSONL concurrent write corruption — claude-code issue #20992](https://github.com/anthropics/claude-code/issues/20992)
- [asyncio.Lock for file write serialization — Python 3.14 docs](https://docs.python.org/3/library/asyncio-sync.html)
- [Docker volumes persistent data — Docker Docs](https://docs.docker.com/engine/storage/volumes/)
- [FastAPI worker timeout — fastapi/fastapi issue #2682](https://github.com/fastapi/fastapi/issues/2682)
- Reference codebase: `/home/brewuser/akc-service/akc_service/learning_integration.py` — fcntl.flock pattern for JSONL write safety
- Reference codebase: `/home/brewuser/akc-service/tests/test_concurrent_kb_writes.py` — threading.Barrier concurrent write isolation test
