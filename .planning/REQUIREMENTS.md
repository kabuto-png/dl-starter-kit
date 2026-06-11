# Requirements: AKC — Agent Knowledge Collective

**Defined:** 2026-06-11
**Core Value:** The `/recall` → task → `/remember` loop demonstrably works: confidence rises with success, falls with failure, and Gold-tier patterns surface first on the next query.

---

## v1 Requirements

### Foundation (service skeleton + health)

- [ ] **FNDTN-01**: Service starts cleanly, validates all required env vars at startup (fail-fast via pydantic-settings), and logs KB_DIR path + current pattern count
- [ ] **FNDTN-02**: `GET /health` returns 200 with `{"status": "ok", "pattern_count": N}` — required by AgentBase
- [ ] **FNDTN-03**: All required env vars documented in `.env.example` (LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, MEMORY_ID, AKC_KB_DIR)

### Storage (JSONL append-only)

- [ ] **STORE-01**: `patterns.jsonl` stores Pattern records; deduplication is last-write-wins on read (dict[id → Pattern])
- [ ] **STORE-02**: `confidence_history.jsonl` is pure append-only audit trail — never deduplicated
- [ ] **STORE-03**: All JSONL writes protected by a single `asyncio.Lock` on `JsonlStore` — full read-modify-write cycle held under lock; atomic `write → os.replace` for crash safety
- [ ] **STORE-04**: `JsonlStore` exposes stable 3-method interface: `load_active(min_tier, tags)`, `update_pattern(id, outcome)`, `load_stats()`

### Confidence Engine (pure functions, tier logic)

- [ ] **ENG-01**: Pattern confidence initialized at 0.67 (Beta(2,1) prior) — NOT 0.50 — so first failure does not demote immediately
- [ ] **ENG-02**: Confidence update: success → +0.05 / failure → −0.10, capped at 0.95 max, max delta ±0.15 per update
- [ ] **ENG-03**: Tier classification: Gold ≥0.85, Production 0.70–0.85, Experimental 0.50–0.70, Demoted <0.50
- [ ] **ENG-04**: Demoted patterns never auto-promote — require manual intervention
- [ ] **ENG-05**: Gold exit guardrail: requires 3 consecutive failures to demote a Gold pattern (not a single update)
- [ ] **ENG-06**: `consecutive_failures` field persisted on the Pattern record so it survives container restarts
- [ ] **ENG-07**: Tag normalization: all tags lowercase at write time (`@field_validator`)

### Remember (write path + Qwen distillation)

- [ ] **RMB-01**: `POST /remember` returns 202 Accepted immediately; distillation + storage runs in BackgroundTask
- [ ] **RMB-02**: BackgroundTask is wrapped in `try/except Exception` with `logger.error()` — failures are never silently swallowed
- [ ] **RMB-03**: Qwen distiller extracts structured `{context, what_worked, what_failed, tags}` from raw outcome text using `response_format={"type": "json_object"}` + `model_validate_json()` (NOT `completions.parse()`)
- [ ] **RMB-04**: Qwen thinking mode disabled via `extra_body={"enable_thinking": False}` AND `<think>` tokens stripped defensively before JSON parse
- [ ] **RMB-05**: `finish_reason == "length"` checked before `json.loads` — truncated responses logged and skipped, not stored
- [ ] **RMB-06**: `max_tokens >= 512` on all Qwen distillation calls
- [ ] **RMB-07**: If pattern `patterns_used` IDs are provided, confidence of matched existing patterns updated (success +0.05 / failure −0.10)
- [ ] **RMB-08**: New patterns created at experimental tier (confidence 0.67) when distillation produces a genuinely new pattern

### Recall (read path)

- [ ] **RCL-01**: `POST /recall` accepts `task_context`, `tags` (optional), `top_k` (default 5), `min_tier` (default "production")
- [ ] **RCL-02**: Response includes for each pattern: `id`, `what_worked`, `what_failed`, `confidence`, `tier`, `times_applied`, `tags`, `last_updated`
- [ ] **RCL-03**: Results ranked by confidence descending; Demoted patterns never returned
- [ ] **RCL-04**: AgentBase Memory Service used for semantic similarity search when available; local JSONL tag+tier filter used as fallback with `asyncio.timeout(2.0)` guard
- [ ] **RCL-05**: `relevance_score` from AgentBase Memory Service threaded through to response (behind thin adapter; field name confirmed empirically on Day 4)
- [ ] **RCL-06**: Structured error responses `{"error": "...", "code": "..."}` for all 4xx/5xx — no bare FastAPI 422s

### Stats

- [ ] **STATS-01**: `GET /stats` returns `total_patterns`, `by_tier` counts, `avg_confidence`, `top_tags` (top 10 by frequency)
- [ ] **STATS-02**: `recall_hit_rate` included — fraction of `/recall` queries that returned ≥1 pattern
- [ ] **STATS-03**: `recently_promoted` included — last 5 patterns that tier-upgraded (computed from `confidence_history.jsonl`)

### Export

- [ ] **EXPORT-01**: `POST /kb/export` renders all Gold + Production patterns as human-readable markdown
- [ ] **EXPORT-02**: Export grouped by tier, each pattern showing: context, what_worked, what_failed, confidence, tags

### Deployment

- [ ] **DEPLOY-01**: Docker container runs on port 8080 as non-root user, deployable to GreenNode AgentBase
- [ ] **DEPLOY-02**: `VOLUME ["/app/data"]` declared in Dockerfile; `AKC_KB_DIR` env var points to mounted path — patterns survive container restarts
- [ ] **DEPLOY-03**: Startup log shows KB_DIR path and current pattern count so persistence can be verified after deploy

### Demo Assets

- [ ] **DEMO-01**: `SKILL.md` Claude Code skill that drives the recall → task → remember loop automatically
- [ ] **DEMO-02**: Seed KB script / seeded data that pre-populates patterns at various confidence tiers for demo Act 3 (fast-forward)
- [ ] **DEMO-03**: Public GitHub repo with clean README covering one-liner, API reference, demo instructions

---

## v2 Requirements

### Observability

- **OBS-01**: Structured request/response logging with latency per endpoint
- **OBS-02**: Prometheus metrics endpoint (`/metrics`)

### Query Improvements

- **QUERY-01**: Recency filter on `/recall` (exclude patterns older than N days)
- **QUERY-02**: BM25 keyword matching as complement to semantic search

### Management

- **MGMT-01**: `PUT /patterns/{id}` — manual confidence override
- **MGMT-02**: `POST /patterns/{id}/rollback` — restore previous confidence version
- **MGMT-03**: `DELETE /patterns/{id}` — hard delete (admin only)

### Web UI / Dashboard

- **UI-01**: Dashboard showing confidence distribution over time
- **UI-02**: Pattern browser with tier filter

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication / API keys | MVP, hackathon scope — all callers trusted |
| Multi-KB routing | Single-KB MVP is sufficient for demo |
| KB sync between nodes | Phase 2 post-hackathon |
| CSP solver | Godot-specific, dropped with track change |
| Godot adapter | Track changed to General / Self-Evolving Agent |
| 3-stage validation engine | Phase 2 |
| BM25 + vector hybrid search | Adds complexity without improving demo story |
| Answer synthesis over KB | Contradicts AKC's core differentiator (structured patterns, not generated answers) |
| TTL expiry on patterns | Demoted tier handles trust decay; TTL adds complexity |
| Cross-session identity resolution | Out of scope for this track |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FNDTN-01 | Phase 1 | Pending |
| FNDTN-02 | Phase 1 | Pending |
| FNDTN-03 | Phase 1 | Pending |
| STORE-01 | Phase 1 | Pending |
| STORE-02 | Phase 1 | Pending |
| STORE-03 | Phase 1 | Pending |
| STORE-04 | Phase 1 | Pending |
| ENG-01 | Phase 1 | Pending |
| ENG-02 | Phase 1 | Pending |
| ENG-03 | Phase 1 | Pending |
| ENG-04 | Phase 1 | Pending |
| ENG-05 | Phase 1 | Pending |
| ENG-06 | Phase 1 | Pending |
| ENG-07 | Phase 1 | Pending |
| RMB-01 | Phase 2 | Pending |
| RMB-02 | Phase 2 | Pending |
| RMB-03 | Phase 2 | Pending |
| RMB-04 | Phase 2 | Pending |
| RMB-05 | Phase 2 | Pending |
| RMB-06 | Phase 2 | Pending |
| RMB-07 | Phase 2 | Pending |
| RMB-08 | Phase 2 | Pending |
| RCL-01 | Phase 3 | Pending |
| RCL-02 | Phase 3 | Pending |
| RCL-03 | Phase 3 | Pending |
| RCL-04 | Phase 3 | Pending |
| RCL-05 | Phase 3 | Pending |
| RCL-06 | Phase 3 | Pending |
| STATS-01 | Phase 3 | Pending |
| STATS-02 | Phase 3 | Pending |
| STATS-03 | Phase 3 | Pending |
| EXPORT-01 | Phase 3 | Pending |
| EXPORT-02 | Phase 3 | Pending |
| DEPLOY-01 | Phase 4 | Pending |
| DEPLOY-02 | Phase 4 | Pending |
| DEPLOY-03 | Phase 4 | Pending |
| DEMO-01 | Phase 5 | Pending |
| DEMO-02 | Phase 5 | Pending |
| DEMO-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 (complete coverage)

---
*Requirements defined: 2026-06-11*
*Last updated: 2026-06-11 after roadmap creation — all 39 requirements mapped*
