# AKC PRD — AUTHORITATIVE v3

**Source:** Anh Đức (team lead), shared 2026-06-11 afternoon
**Status:** ✅ LOCKED — supersedes `01-architecture.md` (v1) and `04-specs-v2-from-meeting-260611.md` (v2 Portal/Hub direction)
**Track:** **General / Self-Evolving Agent** (NOT Agentic Assistant — track changed)
**Deadline:** 2026-06-17 12:00

---

## 0. Reconciliation with prior docs

| Prior direction | Status | Notes |
|---|---|---|
| v1 La Bàn AI — deterministic 6-step safety pipeline (`01-architecture.md`) | ❌ DISCARDED | Concept abandoned |
| v2 Portal/Hub bridging external AI ↔ OpenClaw (`04-specs-v2-from-meeting-260611.md`) | ❌ DISCARDED | Concept abandoned |
| v3 **AKC — Agent Knowledge Collective** (this doc) | ✅ LOCKED | Strip Godot from `.ref/akc-service`, adapt for AgentBase |

**Track changed:** Agentic Assistant → **General / Self-Evolving Agent**

**Base codebase:** `.ref/akc-service` (already cloned to working space). MVP = strip Godot/CSP/validation/sync, keep learning/safety/monitoring/KB layers, add AgentBase Memory for semantic recall.

---

## 1. One-liner

> AKC is a self-improving knowledge service that any AI agent can call to retrieve proven patterns before a task and record outcomes after — so the agent gets measurably smarter with every run.

---

## 2. Problem statement

LLMs are stateless. Every task starts from zero:
- Repeats same mistakes from last week
- Cannot learn from what worked
- No way to know "this approach failed 3 times before"

Existing memory solutions store **conversation history** (raw text, low signal, no trust scoring) — accumulate noise as fast as knowledge.

**AKC stores structured, confidence-scored patterns — not raw history.**

---

## 3. Core flow

```
              Any AI Agent (Claude / Qwen / etc.)
                │                          │
          BEFORE TASK                AFTER TASK
                │                          │
                ▼                          ▼
        POST /recall              POST /remember
        "I'm about to do X"       "I just did X, here is what happened"
                │                          │
                ▼                          ▼
      Returns top N patterns      LLM distills outcome
      ranked by confidence        → structured pattern
      (Gold first)                → confidence updated
                │                          │
                ▼                          ▼
       Agent applies              Tier adjusts:
       knowledge                  success → +0.05
                                  failure → −0.10
                                  Gold (≥0.85) trusted
                                  Demoted (<0.50) excluded
```

**Self-improvement loop:** higher-confidence pattern next time → fewer mistakes → better outcomes → confidence rises further.

---

## 4. Core concepts

### Pattern (atomic unit)

```json
{
  "id": "pat_001",
  "context": "fixing null pointer in Python when iterating dict",
  "what_worked": "check key existence with .get() before access",
  "what_failed": "direct dict[key] access without guard",
  "tags": ["python", "debugging", "dict"],
  "confidence": 0.87,
  "tier": "gold",
  "times_applied": 12,
  "times_succeeded": 10
}
```

### Confidence tiers

| Tier | Range | Behavior |
|---|---|---|
| **Gold** | 0.85 – 1.0 | Always returned; guardrail-protected |
| **Production** | 0.70 – 0.85 | Returned in normal queries |
| **Experimental** | 0.50 – 0.70 | Returned when few patterns exist |
| **Demoted** | < 0.50 | Never returned; preserved for audit |

### Distillation

When agent records raw outcome → AKC runs small LLM call (**Qwen3 / Gemma on GreenNode MaaS**) to extract structured pattern before storing. Raw noise → structured knowledge.

---

## 5. API contract (MVP)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Required by AgentBase, returns 200 + status |
| POST | `/recall` | Query patterns BEFORE task |
| POST | `/remember` | Record outcome AFTER task (fire-and-forget, 202) |
| GET | `/stats` | KB health snapshot for demo |
| POST | `/kb/export` | Export Gold + Production patterns as markdown |

### `POST /recall`

**Request:**
```json
{
  "task_context": "I need to write a Python function that parses JSON from an API response",
  "tags": ["python", "api"],
  "top_k": 5,
  "min_tier": "production"
}
```

**Response:**
```json
{
  "patterns": [
    {
      "id": "pat_042",
      "what_worked": "always wrap json.loads() in try/except for malformed responses",
      "confidence": 0.91,
      "tier": "gold",
      "times_applied": 8
    }
  ],
  "total_found": 1,
  "query_ms": 23
}
```

### `POST /remember`

**Request:**
```json
{
  "task_context": "wrote a Python JSON parser for Stripe webhook",
  "outcome": "success",
  "what_happened": "Used try/except around json.loads(), caught a malformed payload that would have crashed the handler",
  "patterns_used": ["pat_042"],
  "tags": ["python", "api", "webhooks"]
}
```

**Response:** `202 Accepted`

Background process:
1. LLM distills `what_happened` → structured pattern
2. If matches existing → confidence update (+0.05 success / −0.10 failure)
3. If new → create at `experimental` tier (confidence 0.55)
4. Tier re-evaluated

### `GET /stats`

```json
{
  "total_patterns": 47,
  "by_tier": { "gold": 12, "production": 18, "experimental": 11, "demoted": 6 },
  "top_tags": ["python", "debugging", "api"],
  "avg_confidence": 0.74,
  "total_queries": 203,
  "total_outcomes_recorded": 187
}
```

---

## 6. Out of scope (MVP)

Already exists in `.ref/akc-service` but **NOT in hackathon build**:

- ❌ Godot adapter, GDScript linting, Godot headless test runner
- ❌ CSP solver
- ❌ Validation engine (3-stage pipeline)
- ❌ KB sync between nodes (push/pull remote)
- ❌ Authentication / API keys
- ❌ Web UI

These = Phase 2 post-hackathon.

---

## 7. Architecture on AgentBase

```
┌─────────────────────────────────────────────────┐
│           AKC Container (port 8080)             │
│                                                 │
│  FastAPI app                                    │
│    /health      → health check                  │
│    /recall      → learning_engine.query()       │
│    /remember    → distill() + learning_engine   │
│    /stats       → monitoring_engine.snapshot()  │
│    /kb/export   → kb_exporter.export()          │
│                                                 │
│  LLM Distillation (Qwen via MaaS)              │
│    Raw outcome text → Pattern struct            │
│                                                 │
│  AgentBase Memory Service                       │
│    Semantic search for /recall queries          │
│    Replaces patterns.jsonl for retrieval        │
│                                                 │
│  Local JSONL (append-only)                      │
│    confidence_history.jsonl  (audit trail)      │
│    patterns.jsonl            (source of truth)  │
└─────────────────────────────────────────────────┘
```

**Key architectural decision:** Use AgentBase Memory Service for semantic `/recall` (similarity search for free). Keep JSONL files as append-only source of truth + audit trail.

---

## 8. Safety guardrails (kept from akc-service)

Ship in MVP — already coded:

1. Confidence cap at 0.95 (no pattern becomes infallible)
2. Max delta ±0.15 per update (no wild swings)
3. Demoted patterns never auto-promote (require manual `/update`)
4. Concurrent write protection on KB files

---

## 9. Demo script (2-3 min video)

**Setup:** AKC deployed on AgentBase, endpoint live. Claude Code as calling agent.

**Act 1 — Cold start (0:00–0:40)**
- Task: "Fix this Python API handler that crashes on malformed input"
- `POST /recall` → 0 patterns (KB empty)
- Claude attempts fix naively → misses edge case → fails
- `POST /remember` outcome: failure

**Act 2 — Knowledge stored (0:40–1:20)**
- `GET /stats` → 1 experimental pattern, confidence 0.55
- Same task again
- `POST /recall` → returns pattern (experimental tier)
- Claude applies pattern → succeeds
- `POST /remember` outcome: success
- `GET /stats` → confidence 0.60, still experimental

**Act 3 — Pattern earns trust (1:20–2:00)**
- Fast-forward: 5 more successes
- `GET /stats` → confidence 0.87, promoted to **Gold**
- New task, different context same tag
- `POST /recall` → Gold pattern returned
- Claude solves on first attempt, zero trial-and-error

**Act 4 — Pitch (2:00–2:30)**
- `GET /kb/export` → human-readable KB markdown
- "This is what your agent has learned. It compounds."

---

## 10. Tech stack (locked)

| Component | Choice | Reason |
|---|---|---|
| Framework | FastAPI (Python) | Already in akc-service codebase |
| LLM distillation | **Qwen 3 via GreenNode MaaS** | Strong structured extraction, VN-friendly |
| Semantic search | **AgentBase Memory Service** | Native platform, no extra infra |
| Storage | JSONL append-only | Already in akc-service, simple, auditable |
| Container | Docker, port 8080 | Required by AgentBase |
| Base image | `python:3.11-slim` | Smallest viable |

---

## 11. 7-day build plan

| Day | Focus | Deliverable |
|---|---|---|
| Jun 10 | Setup + strip Godot code from akc-service | Clean FastAPI app running locally |
| **Jun 11 (today)** | `/recall` + `/remember` endpoints | Core flow working end-to-end |
| Jun 12 | LLM distillation (Qwen) | Raw outcomes → structured patterns |
| Jun 13 | AgentBase Memory Service integration | Semantic recall working |
| Jun 14 | Dockerize + deploy to AgentBase | Live endpoint on platform |
| Jun 15 | `/stats` + `/kb/export` + polish | Demo-ready |
| Jun 16 | Record demo video + write description | Submission assets ready |
| Jun 17 | Submit by 12:00 | ✅ |

---

## 12. Success criteria

**Pass/Fail (required):**
- [ ] Agent deployed and ACTIVE on GreenNode AgentBase
- [ ] `/health` returns 200
- [ ] Demo video 2-3 min, public
- [ ] GitHub repo public

**Quality bar (for votes):**
- [ ] `/recall` → `/remember` loop demonstrably works in video
- [ ] Confidence tier promotion visible in demo
- [ ] Stats endpoint shows KB growing
- [ ] KB export shows human-readable earned knowledge

---

## 13. Submission assets

- [ ] GitHub repo: public, clean README
- [ ] Video 2-3 min: shows full recall → task → remember loop
- [ ] Description 100-300 words: lead with self-improvement story
- [ ] AgentBase endpoint URL (optional but strong signal)

---

## 14. Impact on current scaffold

Current `main.py` (LangChain + 2 tools remember/recall + greennode_agentbase scaffold) → **NEEDS REFACTOR** to:
- FastAPI app on port 8080 (not LangChain agent)
- 5 endpoints per §5
- Pattern + confidence engine ported from `.ref/akc-service/akc_service/learning_engine.py`
- Distillation via ChatOpenAI/Qwen MaaS
- AgentBase Memory Service replaces `MemoryClient` direct file ops for semantic recall

**Files to port from `.ref/akc-service` (after strip):**
- `akc_service/learning_engine.py` — pattern store, versioning, tier classification
- `akc_service/safety_engine.py` — guardrails (cap 0.95, max delta ±0.15)
- `akc_service/monitoring_engine.py` — stats snapshot
- `akc_service/kb_exporter.py` — markdown export
- `akc_service/config.py` — env var parsing (adapt for AgentBase)
- `akc_service/api/{main,routes,models}.py` — FastAPI structure

**Files to DROP from `.ref/akc-service`:**
- `adapters/godot/` entirely
- `akc_service/validation_engine.py`
- `akc_service/csp_solver.py`
- `akc_service/sync_*` modules
- `akc_service/learning_integration.py` (Godot-specific outcome shape)
- `tests/test_kb_routing.py` + multi-KB stuff (single-KB MVP)

---

## 15. Tagline

> *AKC — The agent that learns what to trust.*

---

## 16. Open questions (for partner Claude / next pass)

1. **Repo name:** keep `dl_starter_kit` or rename to `akc`? Public repo name matters for submission.
2. **Pattern ID strategy:** UUID vs incrementing? akc-service uses incrementing — preserve?
3. **Tag taxonomy:** free-form vs controlled vocabulary? MVP = free-form per PRD example.
4. **Distillation prompt template:** need to write — see `.ref/akc-service` for inspiration (none exists there, this is new).
5. **AgentBase Memory Service semantic search API:** how exactly does it expose similarity search? `MemoryRecordSearchRequest` in current scaffold uses vector similarity by default — verify before integration.
6. **Demo "fast-forward 5 successes" mechanism:** scripted in video (cut) OR seeded data OR test endpoint to bump confidence?
