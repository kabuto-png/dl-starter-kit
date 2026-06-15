# Codex Agent Instructions — AKC Loop

Codex-specific entry point. Content mirrors root `AGENTS.md` — Codex auto-discovers `.codex/AGENTS.md` and root `AGENTS.md`.

## Quick setup for Codex CLI

```bash
export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn
```

## Workflow (every task)

### Before any code task

Call AKC `/recall` to fetch team patterns matching the request. Use the response to inform your approach.

```bash
curl -sf -X POST "$AKC_ENDPOINT/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<1-sentence summary>",
    "tags": ["<lang>", "<framework>", "<domain>"],
    "top_k": 5,
    "min_tier": "production"
  }'
```

Read `what_worked` (apply) and `what_failed` (avoid). Prefer `tier: gold`. Track IDs you apply.

### After completing the task

Fire-and-forget `/remember` with outcome:

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

## Codex-specific notes

- Codex runs shell commands directly — curl works natively
- Use `--exec-bash-allow` if your Codex config restricts subshell calls
- If running in `--safe` mode, ensure `curl` to `$AKC_ENDPOINT` is in the allowlist
- AKC endpoint returns 202 immediately on `/remember` — Codex should NOT block waiting for response body

## Examples

### Python refactor task

```bash
# Codex receives: "Refactor auth_service.py to use dependency injection"

# Step 1: recall
curl -sf -X POST "$AKC_ENDPOINT/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "refactor Python module to use dependency injection",
    "tags": ["python", "refactor", "dependency-injection", "fastapi"],
    "top_k": 3,
    "min_tier": "production"
  }'

# Step 2: code (apply patterns cited from response)

# Step 3: remember
curl -sf -X POST "$AKC_ENDPOINT/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "refactor Python module to use dependency injection",
    "outcome": "success",
    "what_happened": "Used FastAPI Depends() to inject Store and LLM clients. Per pattern <id>, avoided global mutable state. Tests pass.",
    "patterns_used": ["<id-from-recall>"],
    "success": true,
    "tags": ["python", "fastapi", "refactor", "dependency-injection"]
  }' || true
```

## Reference

See root [`AGENTS.md`](../AGENTS.md) for full field reference and rules.
