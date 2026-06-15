# Gemini CLI Instructions — AKC Loop

Gemini CLI auto-discovers `GEMINI.md` at repo root or `.gemini/GEMINI.md`.

## Endpoint

```bash
export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn
```

## Workflow (mandatory for every task)

You are an AI coding/automation agent with access to **AKC (Agent Knowledge Catalyst)** — a persistent team memory of past task outcomes.

### Step 1 — Recall before starting

Before generating any plan, code, or recommendation, query AKC:

```bash
curl -sf -X POST "$AKC_ENDPOINT/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<concise 1-sentence summary of the request>",
    "tags": ["<domain>", "<tech>", "<focus>"],
    "top_k": 5,
    "min_tier": "production"
  }'
```

Each returned pattern has:
- `what_worked` — apply this approach
- `what_failed` — avoid this antipattern
- `tier` — `gold` (highest trust) > `production` > `experimental`
- `id` — track which IDs you actually use

### Step 2 — Execute

Use the patterns to inform your output. Cite pattern IDs explicitly so the user can audit your reasoning.

### Step 3 — Remember after finishing

```bash
curl -sf -X POST "$AKC_ENDPOINT/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<same 1-sentence as recall>",
    "outcome": "<one-line result>",
    "what_happened": "<detailed reflection: what worked, what surprised, root cause if failed>",
    "patterns_used": ["<id-1>", "<id-2>"],
    "success": true,
    "tags": ["<same tags as recall>"]
  }' || true
```

Endpoint returns 202 Accepted (fire-and-forget). Don't wait for body.

## Gemini-specific notes

- Gemini CLI runs in interactive mode by default — curl works in any shell context
- If using Gemini's tool-use mode, wrap recall/remember as a custom tool definition for cleaner JSON I/O
- For Gemini Code Assist (IDE plugin), this file is loaded as repo context — the AI sees these instructions on every prompt
- Tag suggestion: include `gemini` in tags when the agent is Gemini-specific (e.g. for multi-agent KB analysis)

## Smart-defaults for Gemini

When the user prompt is short or ambiguous, infer `task_context` and `tags` from:
- Programming language detected in surrounding files (e.g. `["python"]` if `.py` open)
- Framework signatures in repo (e.g. `["fastapi"]` if `main.py` imports FastAPI)
- Recent commits' conventional commit type (e.g. `["refactor"]` if user mentions clean-up)

## Reference

- Full universal instructions: root [`AGENTS.md`](../AGENTS.md)
- Repo: https://github.com/kabuto-png/dl-starter-kit
- API contract: `docs/prd/AKC_PRD.md` §5
