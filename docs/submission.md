# AKC — Agent Knowledge Catalyst (Submission)

**Team:** claw26-team23 (DL Starter Kit) · **Clawathon 2026**

## What it is

AKC is **compound team memory for AI agents**. Agents recall proven patterns before a task and record outcomes after — so the team's knowledge compounds instead of being relearned every session. Patterns carry a confidence score and a tier (`gold > production > experimental > demoted`); confidence rises/falls with real outcomes.

## Architecture — two planes

```
 DATA PLANE  (end users)                 CONTROL PLANE  (curator)
  Claude Code ┐                           OpenClaw "AKC Steward"
  Codex       ├─ 1 MCP server ─┐          (no-code web agent)
  Gemini      ┘  (5 tools)     │               │ direct HTTPS
                               ▼               ▼
        AKC backend: /recall /remember /stats /kb/export /health
        + Steward endpoints: GET /patterns · POST /curate · GET /gaps
```

- **Data plane** — engineers consume AKC through **one MCP server** (universal: same tools in Claude Code, Codex, Gemini) plus a per-client instruction layer (`.claude/skills/`, `AGENTS.md`, `GEMINI.md`) that teaches *when* to recall/remember. MCP = portable verbs; skills = judgment. Complementary, not either/or.
- **Control plane** — **OpenClaw, repurposed as the AKC Steward**: it governs and evolves the knowledge base — audits patterns, **promotes/demotes** with a written reason (`/curate`), and surfaces **coverage gaps** (`/gaps`, what users searched but the KB lacked). It calls AKC server-side; it is *not* a user channel. This is the differentiator: a **self-governing knowledge base** no competitor (Cursor/Continue/Aider) offers.

## Live

- **AKC backend:** `https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn` (`/docs` for OpenAPI)
- **MCP server:** `mcp/server.py` — setup + per-client config in `docs/mcp-server-setup.md`
- **OC Steward:** paste `docs/oc-steward-workspace.md` into the OpenClaw Console workspace
- **KB state (deterministic, baked into the image seed — survives restarts):** 30 patterns (5 gold / 10 production / 15 experimental); recall hit-rate ~0.7; 2 known gaps.

## Demo script (5 min)

1. **Data plane** — In Claude Code (MCP configured): "Plan a Japan casual-game keyword launch." The agent calls `akc_recall`, surfaces the JP kanji-keyword pattern, plans citing it, then `akc_remember` records the outcome.
2. **Control plane** — In OpenClaw (Steward): "Audit the knowledge base." It lists patterns, flags the JP-keyword pattern as an under-tiered, high-usage **promote candidate** (production, confidence 0.82, applied 18×). "Promote it to gold." → `POST /curate` with a reason → `/stats recently_promoted` now shows it. Then "Show coverage gaps." → `/gaps` returns the TH soft-launch + iOS-attribution gaps the team should fill.

The two planes together: users *feed* the KB; the Steward *curates and grows* it.

## Built this iteration

- Universal MCP server (5 tools) unifying 3 CLI clients.
- Steward control-plane endpoints (`/patterns`, `/curate`, `/gaps`) + gap-capture on empty recalls.
- Deterministic demo seed (state reproduces on every container start).
- OpenClaw repurposed from demo-user → AKC Steward.

## Unresolved / follow-ups

- AgentBase runtime volume is **not** persistent across versions → demo state lives in the baked seed (resolved this way); a true persistent volume would let runtime-learned patterns survive restarts.
- `/curate` is gated by an optional `X-Curator-Key` (demo-grade), not full IAM.
