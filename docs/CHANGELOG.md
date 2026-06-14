# AKC Changelog

**Project**: Agent Knowledge Catalyst (AKC)
**Track**: Automation & Integration — Anthropic Claw-a-thon 2026
**Submission deadline**: 2026-06-17 12:00 (Asia/Saigon)

---

## v1.0.0 — D4 Checkpoint (2026-06-14)

Backend feature-complete. Two audit rounds applied. Direction locked at Level L (REUSE-MAX: 30 generic patterns + 10 ASO patterns + 2-scene demo). Deploy queued for D5.

### ✨ New Features

- **Confidence Engine**: Bayesian update with Beta(2,1) prior (initial 0.67), tier transitions (gold / production / experimental / demoted), and 3-failure Gold guardrail. Pure functions, fully testable.
- **JSONL Store**: Append-only persistent storage with `asyncio.Lock`, atomic writes via tempfile + `os.replace()`, and crash-safe replay.
- **`POST /recall` Endpoint**: Returns top-k patterns ranked by confidence, filtered by `min_tier` and tag overlap. Optional semantic recall via AgentBase Memory Service.
- **`POST /remember` Endpoint**: Fire-and-forget (202 Accepted) outcome ingestion with `BackgroundTasks`. Pipeline: LLM distillation → store append → confidence update → tier re-evaluation.
- **`GET /stats` Endpoint**: KB health snapshot — `total_patterns`, `by_tier`, `avg_confidence`, `top_tags`, `total_queries`, `total_outcomes_recorded`, `recently_promoted`.
- **`POST /kb/export` Endpoint**: Human-readable markdown export of Gold + Production tier patterns for offline review and judge inspection.
- **`GET /health` Endpoint**: Returns `{status, pattern_count}` for orchestration health checks.
- **GreenNode Memory Service Integration**: Semantic recall via platform-native vector search, with automatic JSONL fallback on Memory Service unavailability. Memory sync retry with exponential backoff.
- **Claude Code Skill** (`akc-recall-task-remember`): Automates the recall → task → remember loop. Skill triggers `/recall` before task execution and `/remember` after task completion.
- **Seed Script** (`scripts/seed_kb.py`): Pre-populates KB with 30 realistic patterns (5 Gold, 10 Production, 15 Experimental), including 10 ASO-specific patterns for the demo persona (2 Gold + 4 Production + 4 Experimental).
- **Docker Deployment**: Production-grade Dockerfile (non-root user, declared VOLUME, uvicorn entry point) + `docker-compose.yml` for local volume persistence testing.
- **VNG MaaS LLM Integration**: OpenAI-compatible client wired to MiniMax M2.5 via GreenNode MaaS for distillation. Configurable via `LLM_MODEL` env var.

### 🔧 Improvements

- **Feature-first FastAPI Architecture**: Refactored to feature-first layout (`akc/recall/`, `akc/remember/`, `akc/stats/`, `akc/export/`, `akc/patterns/`, `akc/core/`). Features isolated; only `patterns/` is shared.
- **Global 422 Handler**: Pydantic validation errors return structured `{error, code}` responses with consistent shape.
- **CORS Middleware**: Configured for Claude Code skill HTTP calls.
- **Settings via `pydantic-settings`**: Single validated `Settings` object, fail-fast at startup on missing required env vars.
- **Dependency Injection**: FastAPI `Depends()` for store and LLM clients — swap implementations without touching feature code.
- **AKC Orientation 1-pager**: Single-page status doc (`docs/AKC-ORIENTATION.md`) covering team setup, locked decisions, D4-D7 roadmap, and demo storyboard summary.
- **Coordination Decisions Log**: Living `docs/COORDINATION.md` recording all architectural and scope decisions with timestamps and rationale.
- **README Rewrite**: Judge-facing documentation — quick start (local + Docker Compose), API contract, tech stack, VNG compliance USP. Reduced 409 → 204 LOC for clarity.

### 🐛 Bug Fixes

- **Round 2 Edge Cases** (`31ee2d7`):
  - Empty `task_context` and empty input guards on `/recall` and `/remember`.
  - Tag case-deduplication (e.g. `"ASO"` and `"aso"` no longer double-count in `top_tags`).
  - `/stats` PRD-compliant field shape: `total_queries`, `total_outcomes_recorded`.
  - Memory Service sync retry on transient failure.
- **Round 1 Edge Cases** (`60ca516`):
  - `confidence_history.jsonl` type tag for downstream `/stats` aggregation.
  - JSONL parse defense — malformed lines skipped with logging, not raised.
  - Recall sort stability — confidence-descending order preserved across ties.
  - Seed script progress logging at 10-pattern checkpoints.
- **Round 0 Hardening** (`bcdbfa2`):
  - Security hardening — sensitive paths removed from default settings.
  - PRD alignment — request/response schemas match `docs/prd/AKC_PRD.md` contract exactly.
  - Skill `SKILL.md` refined to reflect actual endpoint URLs and payload shapes.

### 🔒 Security

- Non-root user in Docker image (UID 1000); declared VOLUME prevents writes to image layers.
- Pydantic-validated env settings — fail-fast on missing or malformed `LLM_API_KEY`, `LLM_BASE_URL`.
- No secrets logged; `.env` gitignored; structured logger with no `print()` calls in production paths.
- VNG-compliant data residency: AKC runs on internal GreenNode AgentBase; no internal data crosses to external LLM providers (DPO-approved architecture).
- Tag normalization prevents lower/uppercase tag confusion in confidence weighting.

### 🏗 Architecture Decisions (locked D4)

- **Track**: Automation & Integration (not Self-Evolving).
- **Direction**: Level L (REUSE-MAX) — preserve generic seed, add 10 ASO-specific patterns, ship 2-scene demo (JP cold start → KR compound recall + live tier promotion).
- **LLM**: MiniMax M2.5 (OpenAI-compatible via GreenNode MaaS) — E2E tested. Configurable via `LLM_MODEL`.
- **Storage**: JSONL append-only as primary; AgentBase Memory Service for optional semantic recall.
- **Distillation**: Handled in-process via OpenAI-compatible LLM client (structured JSON output mode); `BackgroundTasks` keeps `/remember` non-blocking.
- **No OpenClaw demo client** — submission scope is AKC backend + Claude Code skill only.

### 📊 Project Metrics

| Metric | Value |
|---|---|
| Total commits | 49 |
| Backend feature commits | 17 |
| Audit fix commits | 3 |
| Seeded patterns (default) | 30 (5 Gold / 10 Production / 15 Experimental, incl. 10 ASO) |
| API endpoints | 5 (`/recall`, `/remember`, `/stats`, `/kb/export`, `/health`) |
| Test status | Local E2E verified (all endpoints functional) |
| Deploy readiness | D5 target — vCR access cleared, Docker + Runtime creation queued |

### ⚠️ Known Limitations (v1)

- No API authentication — MVP assumes trusted callers behind VNG internal network.
- Single KB per runtime — no multi-tenant routing.
- No cross-runtime KB sync — each runtime maintains its own pattern set.
- Memory Service is optional — JSONL fallback active when AgentBase Memory unavailable.

---

## Pre-v1.0 — Foundation Phases (D1-D3, 2026-06-10 → 2026-06-13)

Phase 1 (D1-D2): Project scaffolding, AgentBase resource provisioning (Memory, Identity, LLM key), domain models, configuration, JSONL store, FastAPI lifespan.

Phase 2 (D2): `/remember` endpoint, distillation pipeline, `BackgroundTasks` wiring.

Phase 3 (D3): `/recall`, `/stats`, `/kb/export` endpoints; router wiring; global 422 handler.

Phase 4 (D3): Dockerfile hardening, `docker-compose.yml`.

Phase 5 (D3): Claude Code skill, seed script, README, AKC-ORIENTATION doc.

Phase 6 (D3-D4): GreenNode Memory Service integration; two audit review rounds.

All 5 backend phases marked human-verified at commit `d8291bb` (AKC v1 milestone).

---

**Next milestones**: D5 deploy (Docker build + vCR push + Runtime creation + dress rehearsal). D6 demo video + use case write-up. D7 submission before 12:00 GMT+7.
