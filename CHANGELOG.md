# Changelog

All notable changes to **AKC — Agent Knowledge Collectives** documented for the AKC Clawathon 2026 submission (track: Automation & Integration).

---

## Unreleased — June 17, 2026 (Cowork Bundle + Branding)

### ✨ New Features

- **Cowork skill bundle builder** (`scripts/build-cowork-skill.py`): one-command packager turning the AKC skill into a `.skill` archive installable in Claude Cowork. Strips Claude-Code-only syntax (`/uc:` slash commands, `AskUserQuestion`, `TaskCreate`) and names the bundle from frontmatter. Output: `cowork-skills/akc-recall-task-remember.skill`.

### 🔧 Improvements

- **README**: added "Build Claude Cowork bundle" section with usage, output path, install steps, and CLI flags.
- **README**: web demo path switched from Vercel placeholder to local Next.js (`cd webdemo && npm install && npm run dev`) — judges now run a real backend instead of a TBD URL.
- **README**: demo video + thumbnail embedded in hero section.
- **Branding**: AKC expansion finalized as **"Agent Knowledge Collectives"** (was "Codex") across docs.
- **Repo hygiene**: `.mailmap` normalizes author display names in `git log` / `git shortlog`.

---

## v1.1.0 — June 16, 2026 PM (Multi-Client Onboarding + Web Demo)

### ✨ New Features

- **Standalone Web Demo** (`webdemo/`): Next.js + Tailwind page for judges to test AKC end-to-end in a browser — no Claude account, no CLI, no MCP setup. 3-column layout: chat (recall→Gemma→answer) + live stats card (pattern_count auto-refresh) + recent recall feed. Vercel-ready with 4 env vars documented in `.env.example`.
- **5-Path Onboarding**: `README.md` "Pick Your Path" decision table and `ONBOARDING.md` master guide cover Browser (Vercel), Claude Desktop, Claude Code, Generic MCP (Cursor/Codex/Antigravity/Gemini), and direct REST API — pick by tool, 5-min setup each.
- **Claude Cowork / Desktop Setup Guide** (`docs/cowork-setup.md`): Step-by-step MCP connector + Project Instructions block paste-and-go. Covers 7 exposed tools (`akc_recall`, `akc_remember`, `akc_stats`, `akc_export`, `akc_health`, `akc_patterns`, `akc_gaps`) with troubleshooting matrix.

### 🔧 Improvements

- **Try Live Demo** badges in README hero — three live links: web demo (Vercel placeholder), REST `/health`, MCP server endpoint.
- **TL;DR copy-paste block** in README for MCP-capable clients — drops MCP URL + discipline block in one place.
- **Vietnamese use-case description** (`plans/260613-0000-clawathon-L/use-case-vn.md`, 191 từ) matching Clawathon rule of 100-200 từ.
- **Submission day-of runbook** (`plans/260613-0000-clawathon-L/submission-checklist.md`) — T-4h / T-2h / T-1h / T-0 timeline, backup plan matrix.
- **seed_kb.py self-bootstraps `sys.path`** — no PYTHONPATH env needed when running outside container.

### 🐛 Bug Fixes

- **Dedupe `MEMORY_ID`** in `.env` — was set twice; first value (stale) shadowed by dotenv override.

### 🔒 Security

- **Git history audit clean** — confirmed zero secrets ever committed (only `.env.example` tracked). Repo safe to flip from private → public.

### 📦 Infrastructure

- **MCP runtime verified live**: `akc-mcp` runtime at `endpoint-8976bc68-...` responds Streamable HTTP / SSE per MCP 2024-11-05 spec, server `akc` v1.27.2, 7 tools discoverable.
- **`.gitignore` extended** to exclude `webdemo/.env.local`, `webdemo/node_modules/`, `webdemo/.next/`, plus stale planning dirs.

### ⚠️ Known Issues

- **GitHub repo still PRIVATE** at time of this changelog — must flip public before 12:00 17/06 submission. Audit confirmed safe to flip.
- **Vercel URL placeholder** in README — webdemo not yet deployed.
- **`next@14.2.5` security advisory** — webdemo uses Next 14.2.5; bump to 14.2.15+ post-hackathon. Non-blocking for demo.

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
