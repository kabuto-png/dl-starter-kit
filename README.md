# AKC — Agent Knowledge Collective

A self-improving knowledge API: patterns rise to **Gold** tier through successful use, fall to **Demoted** when they fail.

> Built for Anthropic's Claw-a-thon 2026 (Nhom 1)

## Why AKC?

Agents learn from experience — but most frameworks discard that learning at restart.
AKC solves this with a persistent, confidence-weighted knowledge base:

- **Patterns persist** across container restarts (JSONL append-only store)
- **Confidence rises** with each successful use (+0.05 per success)
- **Confidence falls** with each failure (−0.10 per failure)
- **Gold-tier patterns surface first** on the next query — the knowledge base gets smarter over time

## Installation

### Option A — Local (no Docker)

**Requirements:** Python 3.11+

```bash
git clone https://github.com/kabuto-png/dl-starter-kit.git
cd dl-starter-kit
pip install -r requirements.txt
```

Create a `.env` file (copy and fill in your credentials):

```bash
LLM_MODEL=qwen-2.5-7b-instruct
LLM_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
LLM_API_KEY=your-api-key
MEMORY_ID=akc-demo
AKC_KB_DIR=./kb_data
```

Start the server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Option B — Docker Compose

```bash
git clone https://github.com/kabuto-png/dl-starter-kit.git
cd dl-starter-kit
```

Export your credentials, then build and start:

```bash
export LLM_MODEL=qwen-2.5-7b-instruct
export LLM_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
export LLM_API_KEY=your-api-key

docker compose up --build
```

The service is ready when you see `AKC starting — KB_DIR: /app/data, patterns: 0` in the logs.
Patterns are persisted in `./kb_data/` on the host.

## Quick Start

Verify the service is running:

```bash
curl http://localhost:8080/health
```

Expected response: `{"status": "ok", "pattern_count": 0}`

Seed demo data (30 patterns across Gold / Production / Experimental tiers):

```bash
# Local
python scripts/seed_kb.py --kb-dir ./kb_data

# Docker (run against the mounted volume)
python scripts/seed_kb.py --kb-dir ./kb_data
```

Expected output: `30 patterns written` (5 Gold, 10 Production, 15 Experimental).

Check the KB loaded the patterns:

```bash
curl http://localhost:8080/health
# {"status": "ok", "pattern_count": 30}
```

## Testing the Core Loop

Run through the full recall → task → remember loop manually:

**1. Recall** — fetch patterns matching a task context:

```bash
curl -s -X POST http://localhost:8080/recall \
  -H "Content-Type: application/json" \
  -d '{"task_context": "write async file I/O in Python", "top_k": 3}' | python3 -m json.tool
```

**2. Remember** — feed back a task outcome (use a pattern `id` from the recall response):

```bash
curl -s -X POST http://localhost:8080/remember \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "write async file I/O in Python",
    "outcome": "success",
    "patterns_used": ["<id-from-recall>"]
  }'
# Returns: 202 (distillation runs in background)
```

**3. Stats** — confirm confidence updated and check tier distribution:

```bash
curl -s http://localhost:8080/stats | python3 -m json.tool
```

**Via Claude Code skill** (automates all three steps):

```bash
/akc-recall-task-remember --task "write async file I/O in Python" --endpoint http://localhost:8080
```

## API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health + pattern count |
| `/recall` | POST | Fetch high-confidence patterns ranked by confidence |
| `/remember` | POST | Learn from task outcome; update pattern confidence (async) |
| `/stats` | GET | KB health metrics (by tier, avg confidence, recently promoted) |
| `/kb/export` | POST | Export Gold + Production patterns as markdown |

### GET /health

Returns service health and current pattern count.

```bash
curl http://localhost:8080/health
```

```json
{
  "status": "ok",
  "pattern_count": 30
}
```

### POST /recall

Fetch patterns matching a task context, ranked by confidence descending. Demoted patterns are excluded.

```bash
curl -X POST http://localhost:8080/recall \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "write async file I/O code in Python",
    "tags": ["python", "async"],
    "top_k": 5,
    "min_tier": "production"
  }'
```

Request body:

```json
{
  "task_context": "write async file I/O code in Python",
  "tags": ["python", "async"],
  "top_k": 5,
  "min_tier": "production"
}
```

Example response (one pattern shown):

```json
[
  {
    "id": "pattern-abc123",
    "context": "Implement async I/O with asyncio in Python",
    "what_worked": "Use asyncio.Lock for concurrent access; hold across full read-modify-write cycle",
    "what_failed": "threading.Lock blocks event loop; avoid in async code",
    "confidence": 0.92,
    "tier": "gold",
    "tags": ["python", "async", "concurrency"],
    "times_applied": 12,
    "last_updated": "2026-06-11T10:30:00Z"
  }
]
```

### POST /remember

Learn from a task outcome. Distills outcome into a new pattern and updates confidence of patterns used.
Returns 202 Accepted immediately — distillation runs in the background.

```bash
curl -X POST http://localhost:8080/remember \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "write async file I/O code in Python",
    "outcome": "success",
    "patterns_used": ["<pattern-id-from-recall>"]
  }'
```

Request body:

```json
{
  "task_context": "write async file I/O code in Python",
  "outcome": "success",
  "patterns_used": ["<pattern-id-from-recall>"]
}
```

Response: `202 Accepted` (distillation runs in background).

### GET /stats

KB health metrics: tier distribution, average confidence, top tags, and recently promoted patterns.

```bash
curl http://localhost:8080/stats
```

```json
{
  "total_patterns": 30,
  "by_tier": {
    "gold": 5,
    "production": 10,
    "experimental": 15,
    "demoted": 0
  },
  "avg_confidence": 0.72,
  "top_tags": ["python", "async", "fastapi", "docker", "concurrency"],
  "recall_hit_rate": 0.95,
  "recently_promoted": ["pattern-xyz789"]
}
```

### POST /kb/export

Export all Gold + Production patterns as human-readable markdown.

```bash
curl -X POST http://localhost:8080/kb/export \
  -H "Content-Type: application/json" \
  -d '{}'
```

Returns a markdown string with patterns grouped by tier, showing context, what_worked, what_failed, confidence, and tags.

## Demo: Recall → Task → Remember

The AKC skill automates the core loop. Invoke it with:

```bash
/akc-recall-task-remember --task "write async file I/O code in Python" --endpoint http://localhost:8080
```

Skill file: `.claude/skills/akc-recall-task-remember/SKILL.md`

What judges will see:

1. **Recall** — `POST /recall` fetches the top-5 Production+ patterns matching the task context
2. **Task** — The skill synthesizes a solution guided by recalled pattern advice
3. **Remember** — `POST /remember` feeds back the outcome; Qwen distils it into a new pattern
4. **Report** — Confidence deltas, newly learned patterns, and updated tier distribution

Additional flags:

- `--top-k 10` — retrieve more patterns per recall
- `--min-tier gold` — restrict recall to Gold-tier patterns only
- `--show-history` — print all HTTP calls and raw responses (debug mode)

## How the Confidence Engine Works

Every pattern has a `confidence` score (0.0–0.95) that determines its tier. Tiers control whether a pattern surfaces in recall.

### Tier thresholds

| Tier | Confidence | Behaviour |
|---|---|---|
| `gold` | ≥ 0.85 | Highest priority; protected against hair-trigger demotion |
| `production` | ≥ 0.70 | Default minimum for recall |
| `experimental` | ≥ 0.50 | Returned only when `min_tier=experimental` |
| `demoted` | < 0.50 | **Permanently excluded** — never returned, never recoverable |

### Confidence deltas

Each `/remember` call with `patterns_used` IDs updates the referenced patterns:

- `success: true` → **+0.05** per pattern used
- `success: false` → **−0.10** per pattern used

A new pattern starts at **0.67** (experimental). It needs ~4 successful uses to reach production, ~7 to reach gold — but only 2 failures to be demoted.

### Gold tier guardrail

Gold patterns are protected: they require **3 consecutive failures** before they can fall below gold. A single bad application won't demote a well-proven pattern. Once the guardrail triggers, the tier drops naturally based on the resulting confidence.

### Demotion is permanent

Once a pattern reaches `demoted`, it is locked there regardless of future outcomes. It will never appear in recall results again. This is intentional — a pattern that failed enough to be demoted should not silently resurface.

### What happens when no patterns match

If the KB is empty, all patterns are demoted, or no patterns pass the tier/tag filters, `/recall` returns a **200 with an empty list**:

```json
{ "patterns": [], "total_found": 0, "query_ms": 12 }
```

There is no error, no fallback suggestion. The caller is expected to proceed without guidance and then call `/remember` afterward — which is exactly how the KB grows from zero.

### Silence means no penalty

The confidence engine only updates when a caller explicitly reports outcomes via `/remember` with `patterns_used`. If an agent uses a pattern and never reports back, confidence stays unchanged. Consistent feedback is what makes the KB self-improving.

## Architecture

**Recall Flow:**

```
POST /recall {task_context}
    |
    v
AgentBase Memory Service (semantic search)
    |  [timeout 2s — falls back if unavailable]
    v
JSONL Store (tag + tier filter)
    |
    v
Confidence Engine (rank by tier, then confidence desc)
    |
    v
Response: patterns sorted by confidence
```

**Learning Flow:**

```
POST /remember {outcome, patterns_used}
    |
    v
202 Accepted (immediate)
    |
    v
BackgroundTask
    |
    v
Qwen Distillation (extract context, what_worked, what_failed)
    |
    v
Confidence Update  success: +0.05 / failure: -0.10
    |
    v
Tier Promotion/Demotion (Gold needs 3 consecutive failures)
    |
    v
Atomically append to patterns.jsonl
```

**Storage:** `patterns.jsonl` (last-write-wins dedup on read, atomic write via tempfile + os.replace) and
`confidence_history.jsonl` (pure append audit trail), both stored under `/app/data/kb` — mountable as a Docker volume so patterns survive container restarts.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI (Python 3.11+) |
| LLM | OpenAI-compatible Qwen 2.5 7B via GreenNode |
| Storage | JSONL append-only (crash-safe) |
| Deployment | Docker; GreenNode AgentBase |
| Confidence | Bayesian update with Beta(2,1) prior (init 0.67) |

## Roadmap

### v2 Features

- **Observability** — Structured logging + Prometheus `/metrics` endpoint
- **Query** — Recency filter + BM25 keyword search (complement to semantic recall)
- **Management** — Manual confidence override, pattern rollback, hard delete
- **Web UI** — Confidence distribution dashboard and pattern browser

### Out of Scope (v1)

- Authentication / API keys (all callers trusted in MVP)
- Multi-KB routing (single KB sufficient for v1)
- Knowledge base sync between nodes
- 3-stage validation engine

## Contributing

Feedback welcome during judging — file GitHub Issues for feature requests, bugs, or README clarity.

---

Built for Anthropic's Claw-a-thon 2026
