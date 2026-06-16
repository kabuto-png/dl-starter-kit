# Changelog

All notable changes to **AKC — Agent Knowledge Codex** documented for the AKC Clawathon 2026 submission (track: Automation & Integration).

---

## v1.0.0 — June 16, 2026 (Hackathon Submission)

### ✨ New Features

- **AKC Memory Loop**: Drop-in `/recall` → reasoning → `/remember` HTTP API for any LLM agent. Patterns auto-distilled by Gemma 4-31b-it on GreenNode MaaS — zero data egress.
- **Claude Code Skill**: Single-file `SKILL.md` integration — agent auto-fires recall before tasks and remember after outcomes, with no code changes.
- **Universal MCP Server**: Native Model Context Protocol server lets any MCP-compatible agent (Cursor, Claude Code, OpenClaw) plug into AKC.
- **OpenClaw Steward Control Plane**: Curate, gap-analysis, and band-clamp endpoints for human-in-the-loop knowledge curation.
- **Steward Heartbeat**: Autonomous `/steward/heartbeat` pulse surfaces KB health metrics for monitoring.
- **Pre-seeded Knowledge Base**: 30 patterns across Gold / Production / Experimental tiers — 10 ASO playbooks (JP, KR, VN) + 20 generic agent dev patterns.
- **Semantic Recall**: GreenNode Memory Service wiring — tag-weighted relevance scoring with min_tier filtering and top_k bounds.
- **Multi-Surface Skill Files**: Adapter files for Claude Code, Gemini, Codex, and Antigravity — same backend, multi-IDE reach.

### 🔧 Improvements

- **9× Faster Distillation**: A/B-tested Gemma 4-31b-it against MiniMax — equal JSON quality, 9× lower latency. LLM swappable via `LLM_MODEL`.
- **Resilient Health Endpoint**: Survives degraded Memory Service — no false-negative health flaps during transient remote 500s.
- **CORS Wildcard**: Frontend integrations (OpenClaw demo client, dashboards) work out of the box.
- **422 Global Handler**: Validation errors return structured payloads instead of FastAPI defaults.
- **Logger-First Boot**: Init order rewritten so deploy errors are captured in logs instead of black-holed.
- **Background Task Queue**: `/remember` returns 202 immediately, distillation runs async via FastAPI BackgroundTasks.
- **Tier Re-evaluation**: Pattern confidence + tier promote/demote logic runs on every outcome record.
- **Docker Seed Bake**: KB pre-seeded at image build → demo `/health` shows 30 patterns instantly on first boot.

### 🐛 Bug Fixes

- **Outcome Detection**: Corrected `outcome="failed"` routing — failures now land in `what_failed` field, not `what_worked`.
- **Asyncio Import**: Missing async import surfaced under load — fixed.
- **patterns_used Cap**: Prevent unbounded `patterns_used` lists; capped to top relevant.
- **Empty Input Guards**: `/recall` and `/remember` reject empty `task_context` cleanly with 422.
- **Tag Case Dedup**: `["ASO", "aso"]` no longer counted twice; tags lowercase-normalized.
- **History Type Tag**: Outcome history entries now carry consistent `type` field.
- **JSONL Parse Defense**: Corrupt lines logged and skipped instead of aborting the read.
- **Recall Sort**: Relevance ordering now stable across ties.
- **Memory Sync Retry**: Transient remote 500s retried 2× before logging `SYNC_FAILED`.
- **Top-K Bounds**: `top_k` capped to prevent runaway recall result sets.
- **Min-Tier Enum**: Validated against `gold|production|experimental` — invalid values rejected.
- **Gold Desync**: Tier promotion logic no longer races with recall reads.
- **Length Limits**: Pattern field max-lengths enforced to prevent KB bloat.
- **Recall Tag Filter**: Edge cases in tag intersection fixed.

### 🔒 Security

- **Non-Root Container**: Dockerfile runs as `appuser` (UID 1001), not root.
- **Curator Key Auth**: `/curate` endpoint now requires `X-Curator-Key` header — re-secured after public exposure.
- **Trust Boundary Doc**: Defense-in-depth model documented (boundary, auth, rate, audit).
- **Skill PRD Alignment**: SKILL.md scoped to least-privilege HTTP calls only.
- **Secret Hygiene**: `.env`, `.greennode.json`, registry creds excluded via `.dockerignore`.

### 📦 Infrastructure

- **Live on GreenNode AgentBase**: Runtime `dl-starter-kit` ACTIVE — endpoint stable since June 15.
- **vCR Image Pipeline**: Docker images pushed to `vcr.vngcloud.vn/111666-dl-starter-kit/` via robot account.
- **Docker Compose**: Local volume-persistent dev setup for offline iteration.
- **JsonlStore**: Atomic JSONL writes with `asyncio.Lock` — durable single-process KB.

### ⚠️ Known Issues

- **Memory Sync 500s**: ~13% of `/remember` calls hit transient HTTP 500 on remote Memory Service. Local KB is authoritative; sync retried 2× then logged. Does not affect demo.
- **No Multi-Process Lock**: `JsonlStore` safe for single uvicorn worker only. Multi-worker deploy requires Redis lock or DB upgrade (post-hackathon).

---

## Submission Highlights

| Metric | Value |
|---|---|
| Track | Automation & Integration |
| Persona | ASO Specialist, VNG Publishing |
| LLM | Gemma 4-31b-it (GreenNode MaaS) |
| KB seed | 30 patterns (10 ASO + 20 generic) |
| Live endpoint | `https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn` |
| Demo runtime | ~90 seconds, 2 cinematic scenes |
| USP | VNG-compliant memory infrastructure — DPO-safe, on-prem, drop-in |
