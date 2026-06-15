# Antigravity Skill — AKC Recall & Remember Loop

For Google Antigravity (browser-based agentic IDE). Place this at `.antigravity/skill.md` in the project root; Antigravity auto-discovers workspace skills.

## Configuration

```bash
export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn
```

Or set the env var in your Antigravity workspace settings.

## What this skill does

Wraps every coding/automation task in a recall → execute → remember loop, using **AKC (Agent Knowledge Catalyst)** as the team's persistent memory.

## Before any task — `/recall`

```bash
curl -sf -X POST "$AKC_ENDPOINT/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<1-sentence description>",
    "tags": ["<domain>", "<tech>", "<focus>"],
    "top_k": 5,
    "min_tier": "production"
  }'
```

Reads top-k patterns. Each has:
- `id` — track for `/remember`
- `what_worked` — apply this approach
- `what_failed` — avoid this antipattern
- `tier` — `gold` > `production` > `experimental`
- `confidence` — 0.0 to ~0.95

## After task — `/remember` (fire-and-forget)

```bash
curl -sf -X POST "$AKC_ENDPOINT/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<same as recall>",
    "outcome": "<one-line result>",
    "what_happened": "<details: what worked, what surprised, root cause>",
    "patterns_used": ["<id-1>", "<id-2>"],
    "success": true,
    "tags": ["<same as recall>"]
  }' || true
```

Returns `202 Accepted`. Continue without waiting.

## Antigravity-specific notes

- Antigravity runs in a browser sandbox — ensure outbound HTTPS to the AKC endpoint is allowed in workspace network policy
- For multi-tab agents, share `AKC_ENDPOINT` via workspace environment variables (not per-tab)
- Antigravity's task-graph view will show recall/remember as steps if you wrap them in named subtasks
- Browser-based fetch is OK too:

```javascript
// JavaScript variant for Antigravity browser context
const recall = await fetch(`${AKC_ENDPOINT}/recall`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    task_context: '<1-sentence>',
    tags: ['<domain>', '<tech>'],
    top_k: 5,
    min_tier: 'production'
  })
}).then(r => r.json()).catch(() => ({ patterns: [], total_found: 0 }));

// ... do work, apply patterns ...

await fetch(`${AKC_ENDPOINT}/remember`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    task_context: '<same>',
    outcome: '<result>',
    what_happened: '<details>',
    patterns_used: ['<id>'],
    success: true,
    tags: ['<same>']
  })
}).catch(() => {});  // fire-and-forget
```

## Rules

1. **Always** recall before generating plans/code
2. **Always** remember after finishing
3. Cite real pattern IDs (do NOT make them up)
4. Never block on AKC — fall back to general best practices if unreachable
5. Tags lowercase, consistent

## Reference

- Universal instructions: root [`AGENTS.md`](../AGENTS.md)
- Repo: https://github.com/kabuto-png/dl-starter-kit
- Endpoint health: `curl -sf $AKC_ENDPOINT/health`
