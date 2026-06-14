# AKC Architecture v1

## Overview

AKC is a stateless FastAPI service. Two core flows:

- **`POST /remember`** — receive outcome (pre-structured by calling agent) → optionally distill via Gemma 4-31b-it (OpenAI-compatible, configurable via LLM_MODEL env) → store + update confidence
- **`POST /recall`** — receive task context → search patterns via AgentBase Memory Service (with JSONL fallback) by tier/tags → return ranked by confidence

Everything else (`/health`, `/stats`, `/kb/export`) is operational plumbing. 10 ASO-specific patterns included in default 30-pattern seed (tier distribution: 2 gold, 4 production, 4 experimental).

---

## Folder Structure

```
akc/
  patterns/              # shared domain — core data model
    models.py            # Pattern dataclass, Tier enum
    store.py             # JSONL read/write (patterns.jsonl, confidence_history.jsonl)
    engine.py            # confidence update, tier classification, guardrails

  recall/                # feature: query patterns before a task
    router.py            # POST /recall
    service.py           # filter by min_tier + tags, rank by confidence, return top_k
    schemas.py           # RecallRequest, RecallResponse

  remember/              # feature: record outcome after a task
    router.py            # POST /remember → 202 Accepted
    service.py           # orchestrate: distill → store → update confidence
    distiller.py         # LLM call (Gemma 4-31b-it, OpenAI-compatible) → structured Pattern JSON
    schemas.py           # RememberRequest

  stats/                 # feature: KB health snapshot
    router.py            # GET /stats
    service.py           # aggregate counts, avg confidence, top tags

  export/                # feature: export knowledge base
    router.py            # POST /kb/export
    service.py           # render Gold + Production patterns as markdown

  core/                  # cross-cutting concerns
    config.py            # pydantic-settings — one Settings object, validated at startup
    deps.py              # FastAPI Depends() — get_store(), get_llm()

main.py                  # app factory, register routers, /health endpoint
```

---

## Request Flows

### POST /remember (202 Accepted)

```
router
  └── return 202 immediately
  └── BackgroundTask:
        distiller.extract(task_context, what_happened, outcome)
          └── ChatOpenAI (Gemma 4-31b-it per .env LLM_MODEL, swappable) → structured Pattern JSON
        store.append(pattern)
        engine.update_confidence(pattern_id, outcome)
          └── success → +0.05 / failure → −0.10
          └── tier re-evaluated after update
```

### POST /recall

```
router
  └── service.query(task_context, tags, top_k, min_tier)
        └── store.load_active(min_tier, tags)
        └── rank by confidence descending
        └── return top_k patterns
```

---

## Dependency Rules

- `patterns/` is the **only shared domain**. Features import from it, never from each other.
- Features are isolated — `recall/` and `remember/` share no direct imports.
- `core/deps.py` provides injected dependencies via `Depends()`. No global mutable state.
- `main.py` is the only place routers are registered.

```
main.py
  ├── recall/router     → recall/service → patterns/{store, engine}
  ├── remember/router   → remember/service → remember/distiller, patterns/{store, engine}
  ├── stats/router      → stats/service → patterns/store
  └── export/router     → export/service → patterns/store
```

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Config | `pydantic-settings` | Validated at startup, typed, testable |
| Dependency injection | `FastAPI Depends()` | Swap store/LLM without touching features |
| `/remember` async | `BackgroundTask` → 202 | Caller isn't blocked by LLM distillation latency |
| Storage | JSONL append-only | Simple, auditable, no infra required |
| LLM distillation | Gemma 4-31b-it via GreenNode MaaS (OpenAI-compatible, swappable) | Structured JSON extraction, 9x faster than MiniMax M2.5, cheaper, configurable via `LLM_MODEL` env |
| Semantic recall | AgentBase Memory Service | Native platform, similarity search for free |

---

## Extension Points

| What to add | Where to change |
|---|---|
| Middleware (auth, rate limit, logging) | `main.py` only — one decorator |
| Web UI / dashboard | New `dashboard/` feature folder, reads from `stats/service.py` |
| New endpoints (`/patterns/update`, `/rollback`) | New feature folder + import from `patterns/` |
| Swap storage (SQLite, Postgres) | `patterns/store.py` only — interface stays stable |
| Swap LLM | `remember/distiller.py` only — service calls `distiller.extract()` |
| AgentBase Memory integration | `recall/service.py` — alternative search path |

---

## Data vs Code separation

```
kb/                        # runtime data — gitignored
  patterns.jsonl
  confidence_history.jsonl

akc/                       # application code
  export/                  # feature: /kb/export endpoint
    router.py
    service.py
```

The only contract worth protecting: **`patterns/store.py` interface** (`load`, `append`, `update`). Keep it stable and everything above it stays independent.

---

## Confidence & Tier Model

```
Gold         0.85 – 1.00   Always returned. Guardrail-protected.
Production   0.70 – 0.85   Returned in normal queries.
Experimental 0.50 – 0.70   Returned when few patterns exist.
Demoted      < 0.50        Never returned. Preserved for audit.
```

**Guardrails (non-negotiable):**
- Confidence cap: 0.95 (no pattern becomes infallible)
- Max delta per update: ±0.15 (no wild swings)
- Demoted patterns never auto-promote (require manual intervention)
- Concurrent write protection on JSONL files

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LLM_MODEL` | Yes | Gemma 4-31b-it (OpenAI-compatible, MaaS endpoint, configurable) |
| `LLM_BASE_URL` | Yes | GreenNode MaaS base URL |
| `LLM_API_KEY` | Yes | MaaS API key |
| `MEMORY_ID` | No | AgentBase Memory Service ID for semantic `/recall` (optional, falls back to JSONL if unavailable) |
| `AKC_KB_DIR` | No | Path to JSONL storage (default: `./kb_data` local; `/app/data` in Docker) |
| `AKC_KB_EXPORT_DIR` | No | Path for markdown exports (default: `./kb_export`) |
| `GREENNODE_CLIENT_ID` | No | AgentBase client ID (for Memory Service auth) |
| `GREENNODE_CLIENT_SECRET` | No | AgentBase client secret |
| `GREENNODE_AGENT_IDENTITY` | No | Agent identity for AgentBase registration (default: `dl-starter-kit`) |
