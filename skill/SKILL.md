# AKC Skill — Agent Knowledge Collective

Trigger: any task start/end when this skill is loaded.

AKC endpoint: `${AKC_ENDPOINT:-http://localhost:8080}`

---

## Before Starting Any Task

**Step 1 — Recall relevant patterns.**

Extract a concise `task_context` (one sentence) from the user's request and call `/recall`:

```bash
AKC="${AKC_ENDPOINT:-http://localhost:8080}"
curl -sf -X POST "$AKC/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<concise description of what you are about to do>",
    "tags": ["<relevant>", "tags"],
    "top_k": 5,
    "min_tier": "production"
  }' 2>/dev/null || echo '{"patterns":[],"total_found":0}'
```

**Step 2 — Apply returned patterns.**

- If `total_found > 0`: read each pattern's `what_worked` and `what_failed`. Prefer `tier: "gold"` patterns. Let them inform your approach — avoid known failure modes, reuse known working approaches.
- If `total_found == 0` (cold start): proceed normally without patterns.
- If the request errors or times out: log "AKC unreachable — continuing without patterns" and proceed. Never block on AKC.

Track the `id` of any pattern you actually apply — you will need these ids in Step 4.

---

## After Finishing the Task

**Step 3 — Remember the outcome (fire-and-forget).**

Call `/remember` with what happened:

```bash
AKC="${AKC_ENDPOINT:-http://localhost:8080}"
curl -sf -X POST "$AKC/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<same description used in /recall>",
    "outcome": "<one-line summary: what was achieved or why it failed>",
    "what_happened": "<detailed description: steps taken, surprises, root causes>",
    "patterns_used": ["pat_id_1", "pat_id_2"],
    "success": true,
    "tags": ["python", "relevant-tags"]
  }' 2>/dev/null || true
```

- Set `"success": false` and describe the failure in `what_happened` when the task did not complete.
- Pass an empty array `[]` for `patterns_used` if no patterns were recalled or applied.
- The endpoint returns `202 Accepted` — do not wait for a body.
- If AKC is unreachable, the `|| true` ensures Claude continues silently.

---

## Field Reference

| Field | What to put |
|---|---|
| `task_context` | One-sentence summary of the request |
| `tags` | File types, frameworks, domain keywords |
| `patterns_used` | `id` values from `/recall` that you acted on |
| `success` | `true` if completed as requested, else `false` |

## Setup

```bash
export AKC_ENDPOINT=http://localhost:8080        # optional override
curl -sf "$AKC_ENDPOINT/health" && echo "AKC OK" # smoke test
```

See `README.md` for running the AKC service locally or via Docker Compose.
