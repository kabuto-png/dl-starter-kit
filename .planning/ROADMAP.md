# Roadmap: AKC — Agent Knowledge Collective

## Overview

Five phases deliver a self-improving knowledge API from skeleton to hackathon-ready demo. Phase 1 lays the domain foundation (models, storage, confidence engine, health endpoint). Phase 2 closes the write path (Qwen distillation, /remember). Phase 3 closes the read path (/recall, /stats, /kb/export). Phase 4 packages the service for production deployment on GreenNode AgentBase. Phase 5 produces the demo assets that make the recall → task → remember loop compelling to judges.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [~] **Phase 1: Foundation** - Domain models, JSONL store, confidence engine, /health endpoint
- [ ] **Phase 2: Write Path** - Qwen distiller, /remember endpoint, background task safety
- [ ] **Phase 3: Read Path** - /recall, /stats, /kb/export endpoints
- [ ] **Phase 4: Packaging & Deploy** - Docker container, AgentBase deployment, volume persistence
- [ ] **Phase 5: Demo Polish** - SKILL.md, seed data, README, demo prep

## Phase Details

### Phase 1: Foundation
**Goal**: The service skeleton runs and its core domain layer is fully correct — patterns persist, confidence math is right, and the health endpoint satisfies AgentBase
**Depends on**: Nothing (first phase)
**Requirements**: FNDTN-01, FNDTN-02, FNDTN-03, STORE-01, STORE-02, STORE-03, STORE-04, ENG-01, ENG-02, ENG-03, ENG-04, ENG-05, ENG-06, ENG-07
**Success Criteria** (what must be TRUE):
  1. `GET /health` returns `{"status": "ok", "pattern_count": N}` with HTTP 200
  2. Service refuses to start when required env vars are missing (pydantic-settings fail-fast)
  3. A pattern written to `patterns.jsonl` survives a process restart and is re-loaded correctly on next startup
  4. Confidence math is verifiable: a pattern starting at 0.67 reaches Gold (≥0.85) after the expected number of successes and stays demoted once below 0.50
  5. Three consecutive failures are required to demote a Gold-tier pattern; one or two failures alone do not demote it
**Plans**: 4 plans

Plans:
- [ ] 01-01-PLAN.md — Package skeleton, pydantic-settings config, Pattern/Tier/ConfidenceEvent models
- [ ] 01-02-PLAN.md — Confidence engine pure functions, .env.example AKC_KB_DIR
- [ ] 01-03-PLAN.md — JsonlStore with asyncio.Lock, atomic JSONL persistence
- [ ] 01-04-PLAN.md — main.py FastAPI app with lifespan and /health endpoint

### Phase 2: Write Path
**Goal**: Agents can submit raw outcomes and the system distills them into structured patterns stored correctly in the KB
**Depends on**: Phase 1
**Requirements**: RMB-01, RMB-02, RMB-03, RMB-04, RMB-05, RMB-06, RMB-07, RMB-08
**Success Criteria** (what must be TRUE):
  1. `POST /remember` returns 202 immediately — the caller is never blocked by Qwen latency
  2. A submitted outcome appears as a structured pattern in `patterns.jsonl` within seconds (Qwen distilled `what_worked`, `what_failed`, `tags`)
  3. A Qwen error (truncation, malformed JSON, thinking tokens) is logged with context and the KB is not corrupted — the endpoint continues serving
  4. Submitting a `/remember` with `patterns_used` IDs updates the confidence of those existing patterns (success +0.05 / failure −0.10)
**Plans**: TBD

### Phase 3: Read Path
**Goal**: Agents can query the KB and receive confidence-ranked patterns; operators can inspect KB health and export the knowledge base
**Depends on**: Phase 2
**Requirements**: RCL-01, RCL-02, RCL-03, RCL-04, RCL-05, RCL-06, STATS-01, STATS-02, STATS-03, EXPORT-01, EXPORT-02
**Success Criteria** (what must be TRUE):
  1. `POST /recall` returns patterns ranked by confidence descending; Demoted patterns are never in the response
  2. Each recall result includes `id`, `what_worked`, `what_failed`, `confidence`, `tier`, `times_applied`, `tags`, `last_updated`, and `relevance_score`
  3. `GET /stats` returns `total_patterns`, `by_tier` counts, `avg_confidence`, `top_tags`, `recall_hit_rate`, and `recently_promoted`
  4. `POST /kb/export` returns a markdown document with all Gold + Production patterns grouped by tier
  5. All 4xx/5xx responses return `{"error": "...", "code": "..."}` — no bare FastAPI 422s
**Plans**: TBD

### Phase 4: Packaging & Deploy
**Goal**: The service runs as a production-ready Docker container on port 8080 and patterns survive container restarts
**Depends on**: Phase 3
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03
**Success Criteria** (what must be TRUE):
  1. `docker build` and `docker run -p 8080:8080` succeed; `GET /health` returns 200 from the container
  2. Patterns written before a container restart are present after restart (volume mount confirmed via startup log)
  3. Container runs as a non-root user and is deployable to GreenNode AgentBase
**Plans**: TBD

### Phase 5: Demo Polish
**Goal**: The recall → task → remember loop is demonstrable end-to-end with pre-seeded data and judge-ready assets
**Depends on**: Phase 4
**Requirements**: DEMO-01, DEMO-02, DEMO-03
**Success Criteria** (what must be TRUE):
  1. `SKILL.md` drives the full recall → task → remember loop from Claude Code without manual API calls
  2. A seed script populates the KB with patterns at multiple confidence tiers (Experimental, Production, Gold) so the demo Act 3 fast-forward is credible
  3. The public GitHub README covers one-liner startup, API reference, and demo instructions — a judge unfamiliar with the project can run it
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/4 | Ready to execute | - |
| 2. Write Path | 0/3 | Ready to execute | - |
| 3. Read Path | 0/4 | Ready to execute | - |
| 4. Packaging & Deploy | 0/2 | Ready to execute | - |
| 5. Demo Polish | 0/3 | Ready to execute | - |
