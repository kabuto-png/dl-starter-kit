# Agent Instructions — AKC Recall & Remember Loop

**Audience**: any AI coding/automation agent (Codex, Claude Code, Aider, Continue, OpenClaw, custom). Universal `AGENTS.md` convention.

You have access to **AKC (Agent Knowledge Catalyst)** — a persistent, confidence-weighted team memory. Before doing any task, recall what worked. After finishing, report the outcome so future runs improve.

## Configuration

- Endpoint env var: `$AKC_ENDPOINT`
- Default: `https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn`

```bash
export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn
```

## Step 1 — Before starting any task: `/recall`

Extract a 1-sentence `task_context` and relevant tags from the user's request, then:

```bash
curl -sf -X POST "$AKC_ENDPOINT/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<concise description of what you are about to do>",
    "tags": ["<domain>", "<tech>", "<focus-area>"],
    "top_k": 5,
    "min_tier": "production"
  }' 2>/dev/null || echo '{"patterns":[],"total_found":0}'
```

**Use the response**:
- If `total_found > 0`: read each pattern's `what_worked` (apply it) and `what_failed` (avoid it). Prefer `tier: "gold"` patterns over `production` and `experimental`.
- If `total_found == 0`: proceed normally without patterns. Cold start is OK.
- If error/timeout: log "AKC unreachable" and continue. Never block on AKC.

**Track pattern IDs you actually apply** — need them for Step 3.

## Step 2 — Do the task

Use the patterns to inform your approach. Cite pattern IDs in your work so the user can audit. Example:
> "Per pattern `d25f02b1-...`: prioritize kanji compound terms over romaji for JP keyword research."

## Step 3 — After finishing: `/remember` (fire-and-forget)

```bash
curl -sf -X POST "$AKC_ENDPOINT/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<same 1-sentence as Step 1>",
    "outcome": "<one-line summary: what was achieved or why it failed>",
    "what_happened": "<detailed: steps taken, patterns applied, surprises, root cause>",
    "patterns_used": ["<pattern-id-1>", "<pattern-id-2>"],
    "success": true,
    "tags": ["<same tags as recall + result-specific>"]
  }' 2>/dev/null || true
```

- Use `success: false` if the task failed; explain why in `what_happened`.
- Pass `patterns_used: []` if you used no recalled patterns (cold start).
- Endpoint returns `202 Accepted` — do NOT wait for body.
- `|| true` ensures the agent continues silently on network failure.

## Field reference

| Field | Type | What to put |
|---|---|---|
| `task_context` | string (1-4000) | 1-sentence summary of the request |
| `tags` | list[str] | lowercase, domain + tech + focus (e.g. `["aso","jp","keyword"]`) |
| `top_k` | int | usually 3-5 |
| `min_tier` | enum: `gold` \| `production` \| `experimental` \| `demoted` | start with `production` |
| `outcome` | string | one-line result summary |
| `what_happened` | string | detailed reflection |
| `patterns_used` | list[str] (max 50) | pattern IDs you applied |
| `success` | bool | true if task completed as requested |

## Rules

1. **ALWAYS** call `/recall` before generating a plan, code, or recommendation. Never skip.
2. **ALWAYS** call `/remember` after the task is done. Don't fake `success: true` — be honest.
3. **Cite real pattern IDs** in your output. Never make up IDs.
4. **Never block** on AKC. If unreachable, continue with general best practices.
5. **Use lowercase tags** consistently. Tags `["ASO"]` and `["aso"]` are deduped on the server but be consistent.

## Setup verification

```bash
curl -sf "$AKC_ENDPOINT/health"
# → {"status":"ok","pattern_count":N}
```

If `pattern_count > 0`, AKC is operational. Otherwise the KB is empty (cold start) but `/recall` will still respond.

## Platform-specific files

- **Claude Code**: `skill/SKILL.md` (copy to `~/.claude/skills/akc-recall-task-remember/`)
- **Codex CLI**: this file (`AGENTS.md`) auto-discovered at repo root, or `.codex/AGENTS.md`
- **Gemini CLI**: `.gemini/GEMINI.md`
- **Antigravity**: `.antigravity/skill.md`
- **OpenClaw**: paste from [`docs/openclaw-integration.md`](docs/openclaw-integration.md) into workspace config

All variants share the same recall → execute → remember loop. AKC backend is platform-agnostic.

## Reference

- Repo: https://github.com/kabuto-png/dl-starter-kit
- API contract: `docs/prd/AKC_PRD.md` §5
- Test guide: `docs/test-guide-anh-duc.md`
