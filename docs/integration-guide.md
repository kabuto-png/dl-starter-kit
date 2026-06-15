# AKC Integration — Two-Plane Architecture

**For**: devs adopting AKC trong daily coding workflow.

AKC runs on a **two-plane model**:
- **Data Plane** (end users): Claude Code, Codex, Gemini — consume patterns via one MCP server (universal tools) + per-client skill instructions (judgment)
- **Control Plane** (curator): OpenClaw, repurposed as "AKC Steward" — governs KB health, evolves patterns server-side. Not a user adoption channel.

---

## Architecture: Two Planes

### Data Plane (End Users)

**Universal Tool Layer** — MCP Server
- 5 tools: `akc_recall`, `akc_remember`, `akc_stats`, `akc_export`, `akc_health`
- Built + tested; works in Claude Code, Claude Desktop, Codex, Gemini
- See `docs/mcp-server-setup.md` for installation

**Judgment Layer** — Per-Client Instructions
- Claude Code: `.claude/skills/akc-recall-task-remember/SKILL.md` (skill routing; auto-fires on relevant tasks)
- Codex: `AGENTS.md` (root) + `.codex/AGENTS.md` (tells agent when to call tools)
- Gemini: `.gemini/GEMINI.md` (same pattern — recall before, remember after)

These are **complementary, not either/or**: MCP = verbs (what tools to call); skills/AGENTS.md = judgment (when to call them).

### Control Plane (Curator — AKC Steward)

**OpenClaw**, repurposed as the "**AKC Steward**" — internal governance layer:
- Calls AKC directly server-side
- Interfaces: curate patterns, audit tier accuracy, identify KB gaps, monitor health
- Intended design: GET `/patterns`, POST `/curate`, GET `/gaps`, but NOT deployed yet (design-stage)
- **Not** a production user adoption channel — used by knowledge curators only

---

## TL;DR — Data Plane Setup (End Users)

```bash
# 1. Clone repo
git clone https://github.com/kabuto-png/dl-starter-kit ~/akc

# 2. Set endpoint trong shell rc (.zshrc / .bashrc)
echo 'export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn' >> ~/.zshrc
source ~/.zshrc

# 3. Install MCP server (one-time, shared)
python3 -m venv ~/.akc-mcp-venv
~/.akc-mcp-venv/bin/pip install mcp httpx

# 4. Verify
curl -sf "$AKC_ENDPOINT/health"   # → {"status":"ok","pattern_count":34}
```

**Then pick ONE of 3 client channels:**

| CLI | Judgment Layer | Setup |
|---|---|---|
| **Claude Code** | `.claude/skills/akc-recall-task-remember/SKILL.md` | Add MCP server to project `.mcp.json` or via `claude mcp add` |
| **Codex CLI** | `AGENTS.md` (root) + `.codex/AGENTS.md` | Add MCP server to `~/.codex/config.toml` |
| **Gemini CLI** | `.gemini/GEMINI.md` | Add MCP server to `~/.gemini/settings.json` |

---

## Channel 1 — Claude Code

### Setup (1 phút)

```bash
# Trong project repo của bạn
cd ~/your-project
mkdir -p .claude/skills

# Copy hoặc symlink skill (symlink dễ update sau)
ln -s ~/akc/skill .claude/skills/akc-recall-task-remember

# Launch
claude
```

### How it works

Claude Code auto-discovers skill qua `SKILL.md` YAML frontmatter:

```yaml
---
name: akc-recall-task-remember
description: Compound team memory for any coding/planning task. Use BEFORE starting any non-trivial task (recall past patterns) and AFTER finishing (remember outcome). Trigger on: debugging, deploying, designing APIs, writing migrations, refactoring, security review, performance tuning.
---
```

→ Description "pushy" → skill tự activate trên task phù hợp.

### Test

```
You> Debug 500 error in /signup endpoint

[Claude Code skill auto-fires /recall with tags: backend, debugging, ...]
[Returns 2 patterns about race conditions in signup flows]
[Claude generates fix citing pattern IDs]

You> Looks good, deploy it

[Skill auto-fires /remember with success: true]
```

### Verify externally

```bash
curl -sf "$AKC_ENDPOINT/stats" | grep total_queries
# total_queries: was N, now N+1
```

---

## Channel 2 — Codex CLI (OpenAI)

### Setup (0 phút — pre-configured)

Codex CLI v0.5+ tự đọc 2 files khi launch trong repo:
- `AGENTS.md` (root) — universal AI agent instructions
- `.codex/AGENTS.md` — Codex-specific overrides

```bash
cd ~/akc       # dl-starter-kit clone
codex          # Codex picks up AGENTS.md
```

### AGENTS.md content (preview)

```markdown
# AGENTS.md — Universal AI Agent Instructions

## Before ANY non-trivial task

POST to $AKC_ENDPOINT/recall:
{
  "task_context": "<one-sentence summary>",
  "tags": ["<domain>", "<tech>", "<scope>"],
  "top_k": 5
}

Read returned patterns' what_worked / what_failed.
Cite real IDs only — never fabricate.

## After task complete

POST to $AKC_ENDPOINT/remember:
{
  "task_context": "<same as recall>",
  "outcome": "<one sentence>",
  "what_happened": "<detailed>",
  "patterns_used": ["<real-id-1>"],
  "success": true
}
```

### Test (Codex chat)

```
You> Migrate users table from int to uuid id

[Codex reads AGENTS.md → calls /recall via bash tool]
[Returns 1 pattern about online migration strategies]
[Suggests phased rollout citing pattern ID]
[After confirm → calls /remember]
```

---

## Channel 3 — Gemini CLI (Google)

### Setup (0 phút — pre-configured)

Gemini CLI reads `.gemini/GEMINI.md` automatically.

```bash
cd ~/akc
export GEMINI_API_KEY="your-key"   # or use OAuth flow
gemini
```

### GEMINI.md (preview)

Same content pattern as AGENTS.md — recall before, remember after. File em đã commit (commit `074db23`).

### Test

```bash
gemini "Plan keyword strategy for JP casual game launch week 1"
```

→ Gemini calls `/recall` first, then proposes plan with pattern IDs.

---

## Why 3 Data Plane Channels (not more)

| CLI | Plane | Status | Reason |
|---|---|---|---|
| Claude Code | Data | ✅ Adopted | Native skill system, Anthropic ecosystem |
| Codex | Data | ✅ Adopted | OpenAI ecosystem, growing fast |
| Gemini | Data | ✅ Adopted | Google ecosystem, free tier generous |
| OpenClaw | Control | ✅ Adopted (steward role) | Server-side curation + KB governance |
| Cursor | Data | ❌ Skipped | IDE-coupled, không match "CLI-first" target |
| Aider | Data | ❌ Skipped | Niche, smaller community |
| Continue | Data | ❌ Skipped | Plugin model, fragmented |

**Design principle**: Separate **tool portability** (MCP, build once → 3 clients) from **judgment localization** (skills/AGENTS.md/GEMINI.md, one per client). AKC + 3 official coding agent CLIs + OpenClaw steward = complete system. Bất kỳ team nào pick 1 trong 3 CLIs + optional steward will work với AKC ngày đầu.

---

## Tag conventions

Để AKC return relevant patterns, dùng 3-6 tags lowercase kebab-case:

```
domain   → backend / frontend / aso / ua / infra / data / security / db / devops
tech     → python / typescript / go / fastapi / nextjs / postgres / redis / docker
scope    → debugging / migration / performance / localization / monetization
geo      → jp / kr / vn / th / ph / id / mn / apac (cho ASO/UA tasks)
genre    → casual / hyper-casual / rpg / social (cho mobile launches)
```

Full taxonomy: `skill/references/tags-taxonomy.md`.

---

## Common issues

| Issue | Fix |
|---|---|
| Skill không tự fire trong Claude Code | Check `SKILL.md` description có specific trigger phrases. Test: ask Claude "use akc skill" |
| Codex/Gemini ignore AGENTS.md | Đảm bảo CLI version mới nhất. `codex --version` >= 0.5, `gemini --version` >= 0.4 |
| `$AKC_ENDPOINT` empty | Check shell rc reload: `source ~/.zshrc` hoặc mở terminal mới |
| `/recall` returns empty `patterns: []` | Cold start — no patterns for this tag combo yet. Just proceed, `/remember` after → next time có |
| Pattern IDs cited khác trong /recall response | Agent hallucinated. Check skill `references/error-patterns.md` — strengthen prompt |
| Stats counter không tăng | Network issue. Check `curl -sf $AKC_ENDPOINT/health` works |

---

## Production checklist

Adopt AKC vào real team workflow:

- [ ] Each dev: `export AKC_ENDPOINT=...` trong `.zshrc`
- [ ] Each dev: pick 1 of 3 CLIs (Claude Code / Codex / Gemini), không mix
- [ ] Team-wide: agree on tag taxonomy (15 min meeting)
- [ ] Week 1: seed 5-10 patterns từ recent post-mortems / wiki
- [ ] Week 2+: monitor `/stats` — promotion rate, top tags, demoted patterns
- [ ] Quarterly: review patterns trong `gold` tier — still accurate?

---

## Control Plane — OpenClaw as AKC Steward

OpenClaw plays a **curator role**, not an end-user channel:
- **Governance**: Audit pattern tier accuracy, identify KB gaps, monitor recall health
- **Evolution**: Designed interfaces (GET `/patterns`, POST `/curate`, GET `/gaps`) for KB stewardship — design-stage, not yet deployed
- **Who**: Knowledge architects, not devs building features

Optional: If provisioned by D6, can demo live in judges' eval. Otherwise, AKC + data-plane channels (Claude Code / Codex / Gemini) ship complete.

See `docs/openclaw-integration.md` for steward workspace design (or `docs/oc-steward-workspace.md` once created).

---

## References

**Data Plane (End Users)**
- MCP server setup: `docs/mcp-server-setup.md` (5 tools, all clients)
- Claude Code skill: `skill/SKILL.md` + `skill/references/`
- Universal AGENTS.md: root `AGENTS.md` (107 LOC) — Codex + Gemini base
- Per-client: `.codex/AGENTS.md`, `.gemini/GEMINI.md`
- Quickstart (user-facing): `docs/QUICKSTART.md`
- Quickstart slides: `docs/quickstart.html`

**Control Plane (Curator)**
- OpenClaw integration: `docs/openclaw-integration.md`
- Architecture: `docs/AKC-ORIENTATION.md`

## Unresolved questions

- Khi nào Cursor / IDE plugin sẽ join (post-D7)?
- AKC web UI cho non-CLI users (PMs, analysts) — scope?
- Auto-seed from existing repo history (git log analysis) — feasible?
