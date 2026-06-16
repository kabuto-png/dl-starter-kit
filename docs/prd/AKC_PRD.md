# AKC — Agent Knowledge Collective
## Product Requirements Document
**Claw-a-thon 2026 Submission** | Track: General / Self-Evolving Agent | Deadline: Jun 17, 12:00

---

## 1. One-Liner

AKC is a self-improving knowledge service that any AI agent can call to retrieve proven patterns before a task and record outcomes after — so the agent gets measurably smarter with every run.

---

## 2. Problem

LLMs are stateless. Every time Claude (or any agent) starts a task, it starts from zero:
- It repeats the same mistakes it made last week
- It can't learn from what worked in the past
- It has no way to know "this approach failed 3 times before, try something else"

Existing memory solutions store *conversation history* — raw text, low signal, no trust scoring. They accumulate noise as fast as they accumulate knowledge.

**AKC solves this by storing structured, confidence-scored patterns — not raw history.**

---

## 3. The Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        Any AI Agent                         │
│                    (Claude, Gemma, etc.)                    │
└──────────┬──────────────────────────────────────┬──────────┘
           │                                      │
    BEFORE TASK                             AFTER TASK
           │                                      │
           ▼                                      ▼
  POST /recall                           POST /remember
  "I'm about to do X,                    "I just did X,
   what do you know?"                     here's what happened"
           │                                      │
           ▼                                      ▼
  Returns top N patterns              LLM distills outcome into
  ranked by confidence                structured pattern, updates
  (Gold first)                        confidence score
           │                                      │
           ▼                                      ▼
  Agent applies knowledge             Pattern tier adjusts:
  to the task                         success → confidence +0.05
                                      failure → confidence -0.10
                                      Gold (≥0.85): trusted
                                      Demoted (<0.50): excluded
```

**Next time** the agent queries for a similar task → it gets higher-confidence patterns → makes fewer mistakes → records better outcomes → confidence rises further.

This is the self-improvement loop.

---

## 4. Core Concepts

### Pattern
The atomic unit of knowledge. Not raw text — a structured record:

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

### Confidence Tiers

| Tier | Range | Behavior |
|---|---|---|
| **Gold** | 0.85 – 1.0 | Always returned; guardrail-protected |
| **Production** | 0.70 – 0.85 | Returned in normal queries |
| **Experimental** | 0.50 – 0.70 | Returned when few patterns exist |
| **Demoted** | < 0.50 | Never returned; preserved for audit |

### Distillation
When an agent records a raw outcome, AKC runs a small LLM call (Gemma 4-31b-it on GreenNode MaaS) to extract a structured pattern before storing. Raw noise → structured knowledge.

---

## 5. API Contract (MVP)

### `GET /health`
Required by AgentBase. Returns 200 + status.

---

### `POST /recall`
Query for relevant patterns before a task.

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

---

### `POST /remember`
Record a task outcome after completion. Fire-and-forget (returns 202 immediately, processes async).

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
1. LLM call distills `what_happened` → structured pattern
2. If pattern matches existing → update confidence (+0.05 success / -0.10 failure)
3. If new → create pattern at `experimental` tier (confidence 0.55)
4. Tier re-evaluated after update

---

### `GET /stats`
Return KB health snapshot for the demo.

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

### `POST /kb/export`
Export all Gold + Production patterns as markdown for human review.

---

## 6. Integration Layer — How Knowledge Gets Into AKC

AKC is the knowledge backend. Something must **drive the recall→task→remember loop**. Two approaches exist; MVP ships Option A.

### Option A — Claude Code Skill (MVP) ✅

A `SKILL.md` that ships in the same repo as AKC. When Claude Code loads it, Claude automatically:
1. Calls `POST /recall` with task context before starting any task
2. Executes the task using retrieved patterns as additional context
3. Calls `POST /remember` with the outcome after finishing

**Ships as:** `skill/SKILL.md` in the repo. Any developer clones the repo, points the skill at their AKC endpoint, done.

```
Developer's Claude Code session
    │
    ├── [task starts] → POST /recall → AKC returns patterns
    │                                   Claude uses them
    │
    ├── [Claude does the task]
    │
    └── [task ends]   → POST /remember → AKC distills + stores
```

### Option B — Curator Agent (Phase 2) 🔜

A second AgentBase service that wraps any task end-to-end. Caller just sends `POST /task {"task": "..."}` and gets a result back. The Curator handles recall→execute→remember internally — fully automatic, no Claude Code or skill needed.

Deferred because it requires: two deployed services, a reliable task success/failure evaluator, and the Curator's own LLM task execution logic. Natural Phase 2 once AKC is stable.

---

## 7. What's OUT of Scope (MVP)

Built from scratch — none of the following will be included:

- ❌ Curator Agent (Option B) — Phase 2
- ❌ KB sync between nodes (push/pull remote)
- ❌ Authentication / API keys
- ❌ Web UI
- ❌ Failure detection / anomaly alerts
- ❌ Multi-agent federation

These are Phase 2 after the hackathon.

---

## 8. Architecture on AgentBase

```
┌─────────────────────────────────────────────────┐
│           AKC Container (port 8080)             │
│                                                 │
│  FastAPI app (main.py)                          │
│    /health      → status check                  │
│    /recall      → kb.query()                    │
│    /remember    → distill() → kb.store()        │
│    /stats       → kb.snapshot()                 │
│    /kb/export   → kb.export_markdown()          │
│                                                 │
│  distill.py                                     │
│    Gemma 4-31b-it via GreenNode MaaS            │
│    raw outcome text → structured Pattern        │
│                                                 │
│  kb.py                                          │
│    AgentBase Memory Service (semantic search)   │
│    patterns.jsonl (append-only source of truth) │
│    confidence_history.jsonl (audit trail)       │
└─────────────────────────────────────────────────┘
```

**Key decision:** AgentBase Memory Service handles semantic similarity for `/recall`. Local JSONL is the append-only source of truth and audit trail. No external DB needed.

---

## 9. Confidence Calculation

### Model: Beta Distribution

Each pattern maintains two counters — `alpha` (successes + 1) and `beta` (failures + 1) — starting from a weak uniform prior of `(1, 1)`.

```
confidence = alpha / (alpha + beta)
```

Every recorded outcome updates the counters, and confidence is recomputed from scratch. No fixed deltas, no magic numbers.

**Why Beta distribution:**
- Hard to fake Gold — needs sustained evidence, not a lucky streak
- One failure doesn't kill a proven pattern (20 successes + 1 failure = 21/23 = 0.91, still Gold)
- New patterns are volatile (small evidence base → fast movement)
- Mature patterns are stable (naturally dampens without extra logic)

### Confidence progression examples

| History | alpha | beta | Confidence | Tier |
|---|---|---|---|---|
| Brand new | 1 | 1 | 0.50 | Experimental |
| 3 success, 0 fail | 4 | 1 | 0.80 | Production |
| 10 success, 0 fail | 11 | 1 | 0.92 | Gold |
| 10 success, 2 fail | 11 | 3 | 0.79 | Production |
| 1 success, 5 fail | 2 | 6 | 0.25 | Demoted |

### Gold exit guardrail

A Gold pattern cannot be demoted by a single bad outcome. It must show **3 consecutive failures** before dropping below the Gold boundary:

```python
def update_confidence(pattern, outcome):
    if outcome == "success":
        pattern.alpha += 1
        pattern.consecutive_failures = 0
    else:
        pattern.beta += 1
        if pattern.tier == "gold":
            pattern.consecutive_failures += 1

    raw = pattern.alpha / (pattern.alpha + pattern.beta)

    # Gold patterns need 3 consecutive failures to exit
    if pattern.tier == "gold" and pattern.consecutive_failures < 3:
        return min(raw, 0.95)   # stay Gold, just cap at 0.95

    return min(raw, 0.95)       # hard cap — no pattern is infallible
```

### Additional guardrails

1. **Confidence cap at 0.95** — no pattern becomes infallible
2. **Demoted patterns never auto-promote** — require manual `POST /update`
3. **File locking on JSONL writes** — safe under concurrent requests

---

## 10. Demo Script (2-3 min video)

**Setup:** AKC deployed on AgentBase, endpoint live. Claude Code as the calling agent.

**Act 1 — Cold start (0:00–0:40)**
- Claude gets a task: "Fix this Python API handler that crashes on malformed input"
- Calls `POST /recall` → returns 0 patterns (KB is empty)
- Claude attempts the fix naively → misses the edge case → fails
- Claude calls `POST /remember` with outcome: failure, what happened

**Act 2 — Knowledge stored (0:40–1:20)**
- Show `GET /stats` → 1 experimental pattern, confidence 0.55
- Claude gets the same task again
- Calls `POST /recall` → returns the pattern (experimental tier)
- Claude applies the pattern → succeeds
- Calls `POST /remember` with outcome: success
- Show `GET /stats` → confidence now 0.60, still experimental

**Act 3 — Pattern earns trust (1:20–2:00)**
- Fast-forward: same pattern applied 5 more times, all success
- Show `GET /stats` → confidence 0.87, tier promoted to **Gold**
- New task, different context but same tag
- `POST /recall` → Gold pattern returned immediately
- Claude solves it on first attempt, zero trial and error

**Act 4 — The pitch (2:00–2:30)**
- Show `GET /kb/export` markdown — human-readable KB of earned knowledge
- "This is what your agent has learned. It compounds."

---

## 11. Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Framework | FastAPI + Python 3.11 | Fast to write, async-native, Pydantic validation |
| LLM client | `openai` SDK (direct) | Thin client for OpenAI-compatible APIs; LangChain/LangGraph explicitly excluded — no agent abstractions needed |
| LLM distillation | Gemma 4-31b-it via GreenNode MaaS | Strong structured extraction, OpenAI-compatible API |
| Semantic search | AgentBase Memory Service | Native platform, no extra infra |
| Storage | JSONL append-only | Simple, crash-safe, human-readable audit trail |
| Container | Docker, port 8080 | Required by AgentBase runtime |
| Base image | `python:3.11-slim` | Minimal footprint |

---

## 12. Project Structure (new repo)

```
akc/
  akc_service/
    main.py          # FastAPI app, lifespan, CORS, exception handling
    routes.py        # All 5 endpoints wired up
    models.py        # Pydantic request/response schemas
    kb.py            # Pattern storage, confidence scoring, tier logic, JSONL
    distill.py       # Gemma 4-31b-it call: raw outcome → structured Pattern
    memory.py        # AgentBase Memory Service client (store + semantic search)
    config.py        # Env vars (MaaS key, memory ID, KB dir, safety level)
    kb/
      patterns.jsonl
      confidence_history.jsonl
  skill/
    SKILL.md         # Claude Code skill — instructs Claude to use AKC
  Dockerfile
  requirements.txt
  .env.example
  README.md
```

---

## 13. 7-Day Build Plan

| Day | Focus | Deliverable |
|---|---|---|
| **Jun 10** | Repo setup, models.py, config.py, /health | Skeleton running on port 8080 |
| **Jun 11** | kb.py — JSONL storage, confidence scoring, tier logic | Patterns stored and queried locally |
| **Jun 12** | distill.py — Gemma 4-31b-it call, structured extraction | Raw outcomes → structured patterns working |
| **Jun 13** | memory.py — AgentBase Memory Service integration | Semantic /recall working end-to-end |
| **Jun 14** | Dockerfile + deploy to AgentBase | Live endpoint, ACTIVE on platform |
| **Jun 15** | skill/SKILL.md + /stats + /kb/export + full loop test | Demo-ready, skill drives the loop |
| **Jun 16** | Record demo video + write submission description | Submission assets ready |
| **Jun 17** | Submit by 12:00 | ✅ |

---

## 14. Success Criteria

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

## 15. Submission Assets Checklist

- [ ] GitHub repo: public, clean README
- [ ] `skill/SKILL.md` in repo — usable by anyone with Claude Code
- [ ] Video: 2-3 min, shows skill driving the full recall→task→remember loop
- [ ] Description (100-300 words): lead with the self-improvement story
- [ ] AgentBase endpoint URL (optional but strong signal)

---

*AKC — The agent that learns what to trust.*
