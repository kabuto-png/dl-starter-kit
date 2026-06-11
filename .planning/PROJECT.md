# AKC — Agent Knowledge Collective

## What This Is

AKC is a self-improving knowledge API service built for the Claw-a-thon 2026 hackathon (Track: General / Self-Evolving Agent). Any AI agent calls `/recall` before a task to retrieve confidence-scored patterns, executes the task, then calls `/remember` after — Qwen distills the raw outcome into a structured pattern and updates confidence scores, so the agent gets measurably smarter with every run.

## Core Value

The `/recall` → task → `/remember` loop demonstrably works: confidence rises with success, falls with failure, and Gold-tier patterns surface first on the next query.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] `GET /health` returns 200 with status — required by AgentBase platform
- [ ] `POST /recall` accepts task_context + tags + top_k + min_tier, returns patterns ranked by confidence
- [ ] `POST /remember` accepts raw outcome, returns 202 immediately, distills via Qwen in background, stores structured pattern
- [ ] Confidence scoring: success +0.05 / failure −0.10, tier re-evaluated after each update
- [ ] Tier system: Gold (≥0.85), Production (0.70–0.85), Experimental (0.50–0.70), Demoted (<0.50 — never returned)
- [ ] Guardrails: confidence cap 0.95, max delta ±0.15 per update, demoted never auto-promotes
- [ ] `GET /stats` returns KB health snapshot (total patterns, by-tier counts, avg confidence, top tags)
- [ ] `POST /kb/export` renders Gold + Production patterns as markdown
- [ ] JSONL append-only storage: `kb/patterns.jsonl` + `kb/confidence_history.jsonl`
- [ ] Qwen distillation: raw outcome text → structured Pattern JSON via GreenNode MaaS
- [ ] Docker container on port 8080 — deployable to AgentBase

### Out of Scope

- Authentication / API keys — MVP, hackathon scope
- Web UI / dashboard — Phase 2 post-hackathon
- KB sync between nodes — Phase 2
- CSP solver — Godot-specific, dropped with track change
- Godot adapter — track changed to General / Self-Evolving Agent
- Validation engine (3-stage pipeline) — Phase 2
- Multi-KB routing — single-KB MVP

## Context

- **Hackathon**: Claw-a-thon 2026, deadline Jun 17 12:00. Track: General / Self-Evolving Agent.
- **Base reference**: `/home/brewuser/akc-service` — prior Godot-specific AKC implementation. Core engines (learning, safety, monitoring, export) reusable after stripping Godot code.
- **Platform**: GreenNode AgentBase — container runs on port 8080, Memory Service available for semantic recall.
- **Architecture**: Feature-first FastAPI (`akc/patterns/`, `akc/recall/`, `akc/remember/`, `akc/stats/`, `akc/export/`, `akc/core/`) documented in `docs/architecture_v1.md`.
- **Current scaffold**: `main.py` is a LangChain/LangGraph agent — needs full replacement with FastAPI app.

## Constraints

- **Timeline**: Jun 17 12:00 — 6 days from Jun 11
- **Platform**: Must run as Docker container on port 8080, deployable to GreenNode AgentBase
- **LLM**: Qwen via GreenNode MaaS for distillation (structured JSON extraction)
- **Storage**: JSONL append-only — no database infra, simple, auditable
- **Language**: Python 3.11, FastAPI — matches existing scaffold and reference codebase

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Feature-first architecture | Each feature folder is self-contained; features share only `patterns/` domain | — Pending |
| JSONL over SQLite | No infra, auditable, already in reference codebase, sufficient for hackathon scale | — Pending |
| BackgroundTask for `/remember` | Caller not blocked by Qwen distillation latency; 202 Accepted pattern | — Pending |
| AgentBase Memory for semantic recall | Native platform similarity search, no extra infra | — Pending |
| Strip Godot code, port core engines | Keep learning/safety/monitoring/export logic; drop adapters, CSP, validation | — Pending |
| Qwen via MaaS for distillation | Strong structured JSON extraction, platform-native, VN-friendly | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-11 after initialization*
