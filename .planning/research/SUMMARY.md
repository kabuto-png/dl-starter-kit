# Research Summary — AKC Agent Knowledge Collective

**Confidence: HIGH across all dimensions**

---

## Executive Summary

AKC is a self-improving knowledge API that gives AI agents a callable memory: `/recall` before a task retrieves confidence-scored patterns, `/remember` after a task distills the raw outcome via Qwen into a structured pattern and updates Bayesian confidence scores. The recommended build approach is a feature-first FastAPI service — each feature (`recall/`, `remember/`, `stats/`, `export/`) is self-contained, sharing only the `patterns/` domain layer (models, store, engine). All storage is JSONL append-only with `asyncio.Lock`-guarded writes; no database infra needed.

The core technical differentiators that must be built correctly are the Beta distribution confidence model with a **Beta(2,1) initial prior** (not 0.50 — see pitfall P5), the Gold exit guardrail (3 consecutive failures required to demote), and the Qwen distillation pipeline (`what_worked`/`what_failed` extraction). These are genuinely novel in combination; no surveyed system (mem0, Cloudflare, Azure AI Search) does exactly this.

The two highest-risk areas are the **Qwen integration** and **Docker persistence**. Qwen 3.x thinking mode injects `<think>` tokens into JSON output by default — the distiller must disable thinking explicitly AND strip defensively. BackgroundTask exceptions are silently swallowed by FastAPI — every background task must be wrapped in `try/except` with structured logging or the KB will stay empty with zero diagnostic signal.

---

## Recommended Stack

| Package | Pin | Role |
|---------|-----|------|
| `fastapi>=0.130.0` | 0.136.3 available | HTTP framework, Pydantic v2 native |
| `uvicorn[standard]>=0.30.0` | 0.49.0 available | ASGI server with uvloop |
| `pydantic>=2.7.0` | 2.13.4 available | Validation, use `ConfigDict` not `class Config` |
| `pydantic-settings>=2.7.0` | 2.14.1 available | Env/dotenv config with startup validation |
| `openai>=2.0.0` | 2.41.1 available | LLM client for Qwen via GreenNode MaaS |
| `portalocker>=3.0.0` | 3.2.0 available | JSONL file locking (cross-platform) |
| `python:3.11-slim` | — | Docker base, ~45 MB |

**Anti-patterns to avoid from reference codebase:**
- Raw `os.environ.get()` everywhere → replace with pydantic-settings `BaseSettings` singleton
- No file locking on JSONL writes → `asyncio.Lock` in `JsonlStore`
- `@app.on_event("startup")` → use `lifespan` asynccontextmanager
- Pydantic v1 `class Config:` inner class → use `model_config = ConfigDict(...)`
- `client.chat.completions.parse()` with Pydantic class → use `json_object` + `model_validate_json()` (Qwen may not support `strict: true`)

---

## Features

### Table Stakes (missing = product feels incomplete)

1. `what_failed` in recall response — exists in storage, not exposed; callers need both sides
2. `tags` and `last_updated` in recall response — zero extra computation, improves trust signal
3. Per-query `relevance_score` — every production retrieval system returns one
4. Structured error responses `{"error": "...", "code": "..."}` — bare 422s signal unfinished API
5. `recall_hit_rate` in `/stats` — makes KB usefulness measurable
6. `recently_promoted` list in `/stats` — makes self-improvement visible in demo

### Differentiators (score points with judges)

1. Beta distribution confidence model — mathematically grounded; ML-literate judges will notice
2. Gold exit guardrail (3 consecutive failures) — no surveyed system has this
3. LLM distillation of `what_worked`/`what_failed` as distinct fields — genuinely novel
4. Confidence progression demo arc: Cold Start → Experimental → Production → Gold
5. `SKILL.md` Claude Code integration — no surveyed system ships a ready-to-use agent skill

### Defer to v2+

- Recency filter on `/recall`, BM25+vector hybrid search, pattern deduplication, auth, Web UI

---

## Architecture: Key Decisions

**Domain boundary:** `patterns/` is the only layer features share. `patterns/engine.py` is private to `store.py` — features never call engine functions directly.

**Stable 3-method interface on `JsonlStore`:**
```
load_active(min_tier, tags) → list[Pattern]     # lock-free read
update_pattern(id, outcome, new_pattern)         # lock-guarded write
load_stats() → StoreStats                        # lock-free read
```

**Concurrency:** Single `asyncio.Lock` on `JsonlStore` singleton (on `app.state`). Lock wraps the full read-modify-write cycle. Atomic tmp-rename (`write → os.replace`) provides crash safety. Read path is lock-free.

**Build order:**
```
Phase 1: models.py → config.py → store.py (read/write) → /health
Phase 2: engine.py (pure functions, unit-testable independently)
Phase 3: distiller.py → remember/service.py → POST /remember
Phase 4: recall/service.py + memory.py → POST /recall + GET /stats + POST /kb/export
Phase 5: Dockerfile + deploy + SKILL.md + seed data
```

---

## Critical Pitfalls

| # | Pitfall | Phase | Severity | Prevention |
|---|---------|-------|----------|------------|
| P1 | BackgroundTask exceptions silently swallowed | Day 1 | CRITICAL | `try/except` wrapper in every background function before any other logic |
| P2 | Qwen thinking mode injects `<think>` tokens | Day 3 | CRITICAL | `extra_body={"enable_thinking": False}` + defensive `re.sub` strip — both layers required |
| P3 | Qwen truncates mid-JSON at token budget | Day 3 | CRITICAL | `max_tokens>=512`, check `finish_reason` before `json.loads` |
| P4 | Docker container restart wipes JSONL | Day 5 | CRITICAL | `VOLUME ["/app/data"]` in Dockerfile, named volume in compose |
| P5 | Beta(1,1) prior causes permanent first-failure demotion | Day 2 | CRITICAL | Use Beta(2,1) initial prior → starts at 0.67, not 0.50. Breaks PRD demo Act 1 otherwise |
| P6 | `consecutive_failures` not persisted across restarts | Day 2 | MODERATE | Add `consecutive_failures: int = 0` to Pattern model; store writes full record |
| P7 | AgentBase Memory Service: no published SLA | Day 4 | MODERATE | `asyncio.timeout(2.0)` + JSONL-based local fallback always present |
| P8 | Tag case sensitivity causes silent misses | Day 2 | MINOR | `@field_validator("tags")` normalizing to lowercase in models.py |

---

## Open Questions (needs verification during build)

| Question | When | Risk if wrong |
|----------|------|---------------|
| GreenNode Qwen `enable_thinking` parameter name | Day 3, first hour | Distiller outputs garbage JSON |
| AgentBase Memory Service response format (`relevance_score` field name) | Day 4 | Recall returns wrong scores; build behind thin adapter |
| AgentBase volume persistence — ephemeral or persistent? | Day 5 | Demo KB wiped on redeploy; prepare seeded KB as fallback |
| Qwen `what_worked`/`what_failed` extraction quality | Day 3 | Low-quality patterns; tune prompt if needed |
