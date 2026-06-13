# Team Coordination — AKC Build

**Last updated:** 2026-06-11
**Owners:** anh Đức (team lead / architecture / code) + chủ repo (ops / AgentBase / docs / integration)
**Sync cadence:** ad-hoc until D5, then daily until submit

---

## 1. Roles & ownership split

| Area | Owner | Notes |
|---|---|---|
| Architecture + spec | **anh Đức** | `docs/prd/AKC_PRD.md`, `docs/architecture_v1.md` are authoritative |
| Code refactor (main.py → feature-first FastAPI) | **anh Đức** | Port from `akc-service` (his original repo), strip Godot |
| Pattern engine + distiller (Qwen) | **anh Đức** | Confidence tiers, guardrails — lifted from akc-service |
| AgentBase resources (Memory, Identity, LLM key) | **chủ repo** | Wizard provisioning done; deploy blocked on vCR |
| Deploy + runtime ops | **chủ repo** | Block: vCR 403, escalating to BTC |
| Docs index + state snapshot | **chủ repo** | `docs/06-*`, `docs/07-*` |
| Demo video + submission packaging | **TBD** | D7 morning, both align |
| Integration tests + smoke | **TBD** | Need post-refactor |

---

## 2. Communication channels

| Channel | Use for | Latency expectation |
|---|---|---|
| Teams group (BTC) | BTC announcements, urgent blockers | hours |
| GitHub commits + PR comments | Code & doc changes, decision audit trail | async |
| NotebookLM (meeting transcripts) | Decisions from sync calls | post-meeting |
| Direct chat (between anh Đức + chủ repo) | Quick clarifications, blocker triage | minutes |

---

## 3. Branch & merge protocol

**Default:** trunk-based on `main`. Both push directly when work is small + low conflict risk.

**Use a feature branch when:**
- Change touches > 100 LOC in same file
- Refactor across multiple modules
- Spec change that needs review

**Conflict avoidance rules:**
1. **`git pull --rebase origin main` BEFORE any work session.** Forgetting this caused the 2026-06-11 near-miss (parallel docs work, dangling stash recovery via `git fsck`).
2. **Announce intent before large refactors** (in chat or commit message) so the other side doesn't start parallel work.
3. **Atomic commits.** One commit = one logical change. Don't bundle unrelated edits.
4. **Conventional commit prefix:** `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`. No AI references.
5. **NO force push to `main`** without notice + agreement.

**If conflicts happen:**
- Both push to feature branch first, resolve via PR
- If already on main: `git pull --rebase`, resolve, push. If lost work: try `git fsck --lost-found` + `git cat-file -p <blob>` to recover dangling blobs.

---

## 4. Repo structure invariants

```
dl_starter_kit/
├── main.py                  # entry point (will become app factory per architecture_v1)
├── Dockerfile               # FROM python:3.13-slim, port 8080
├── requirements.txt
├── .env.example             # template — NO real secrets
├── .gitignore               # bảo vệ .env, .agentbase/, .claude/, plans/, .ref/
└── docs/
    ├── prd/AKC_PRD.md       # AUTHORITATIVE spec (anh Đức)
    ├── architecture_v1.md   # AUTHORITATIVE code structure (anh Đức)
    ├── COORDINATION.md      # this file
    ├── 06-agentbase-state-snapshot.md   # ops state for partner
    ├── 07-partner-claude-setup.md        # partner Claude Code setup
    └── archive/             # historical docs (00-05), kept for context
```

**Files OUT of repo** (working space, ignored):
- `.claude/`, `.mcp.json`, `CLAUDE.md`, `.ref/`, `plans/`
- `.env`, `.agentbase/`, `.agentbase-state.json`, `.greennode.json`

---

## 5. Decision log

| Date | Decision | Rationale | Decided by |
|---|---|---|---|
| 2026-06-10 | Scaffold v1 La Bàn AI (deterministic safety pipeline) | Initial brainstorm direction | chủ repo |
| 2026-06-11 AM | Pivot v2 (Portal/Hub bridging external AI ↔ OpenClaw) | Compliance concern from meeting | team (per NotebookLM) |
| 2026-06-11 PM | **Pivot v3 — AKC (Agent Knowledge Collective)** | anh Đức has akc-service base ready to port; concept proven | anh Đức (PRD) |
| 2026-06-11 PM | Track change: Agentic Assistant → General/Self-Evolving Agent | AKC fits Self-Evolving track better | anh Đức |
| 2026-06-11 PM | Feature-first FastAPI structure (per `architecture_v1.md`) | Clean isolation, swap-friendly | anh Đức |
| 2026-06-11 PM | Storage: JSONL append-only (initial) + AgentBase Memory for semantic recall | Simple, auditable, hybrid for similarity | anh Đức |
| 2026-06-11 | LLM model TBD: minimax-m2.5 (current `.env`) vs Qwen3 (PRD spec) | Discrepancy flagged — needs decision | open |
| 2026-06-11 17:12 | **Distillation handled by AgentBase Memory itself, NOT a separate Qwen call in AKC code** | "khúc distill là agent base", "con agent base chỉ tổng hợp thôi"; calling agent (Claude) already pre-structures payload — AKC stays light | anh Đức |
| 2026-06-11 17:16 | **`/remember` payload is pre-structured** by calling Claude (task, approach tried, why failed, how worked) | "việc nặng nhọc đã có claude lo" — keep AKC backend simple | anh Đức |
| 2026-06-11 17:21-17:26 | **MCP vs plain HTTP — DEBATE OPEN** | anh Đức: "skill biết endpoint + schema là đủ, không cần MCP cho nặng". Long: "có nhiều tool khác nhau → MCP đáng vì auto-discover". Question: AgentBase native expose MCP sẵn không? | open |
| 2026-06-11 17:19 | **Calling-side skill** (slash command for source Claude) — owns when/how to invoke `/recall` and shape `/remember` payload | Long = design owner, anh Đức = concept lead | Long |
| 2026-06-11 17:28 | **Add OpenClaw demo client** — AKC core stays FastAPI per PRD. Build 1 OpenClaw agent (no-code markdown workspace) with skill that calls AKC. Shows AKC integration in automation workflow. | Long |
| 2026-06-11 17:28 | **Track candidate: Automation & Integration** — pitch via demo (OpenClaw agent automating workflow, using AKC to learn) | Long (TBD with anh Đức) |
| 2026-06-11 22:50 | **Track confirmed: Automation & Integration** (anh Đức OK switch from Self-Evolving) | anh Đức |
| 2026-06-11 22:55 | Devil's advocate confirmed: **compliance IS the USP**. VNG-er CANNOT use external Claude/Codex on internal data (DPO blocks). Starter Kit = legal way to use AI on VNG internal data. | both |
| 2026-06-11 22:56 | **Stop-doing list locked**: no Web UI desktop, no self-host OpenClaw, no LLM change, no re-architect, no new endpoints | both |
| 2026-06-11 23:01 | **Use case candidate: ASO (App Store Optimization) per geo deploy** — replaces Mai UA onboarding (too generic). ASO has compound learning, compliance need, measurable metrics. To confirm with anh Đức morning D3. | anh Đức (proposed) |
| 2026-06-11 23:05 | Persona doesn't need to be real user — demo persona = PLAUSIBLE + MEASURABLE + SHOWABLE. Mai "ví dụ" admission from Long. ASO persona = "ASO Specialist VNG Publishing" works without naming real person. | both |
| 2026-06-11 23:06 | **Session close tonight.** Locked: Track Automation, ASO use case candidate, Stop-doing list. Awaiting morning D3: anh Đức confirm 3 items (ASO OK / LLM / /remember). vCR mail + .env fix queued for chủ repo D3 morning. | both |

---

## 6. Open items / blockers

| # | Item | Owner | Severity | Target |
|---|---|---|---|---|
| 1 | **vCR 403** — runtime deploy blocked, need `vcrFullAccess` from BTC | chủ repo (file ticket) | HIGH | D4 (13/06) |
| 2 | LLM model: minimax-m2.5 vs Qwen3 — which one final? | anh Đức decide | MED | before D2 code work |
| 3 | AgentBase Memory custom schema for Pattern struct — verify supported | chủ repo (test API) | MED | D3 (12/06) |
| 4 | Demo dataset — seed patterns for /recall demo (need realistic examples) | TBD | LOW | D6 (15/06) |
| 5 | Demo "fast-forward 5 successes" — scripted, seeded, or test endpoint? | TBD | LOW | D6 |
| 6 | License for public repo — confirm with team/legal | TBD | LOW | D6 |
| 7 | Submission description (100-300 words) | chủ repo draft, anh Đức review | LOW | D7 (16/06) |
| 8 | Repo rename: `dl-starter-kit` → `akc`? | both decide | LOW | optional |
| 9 | **Design calling-side skill** (Claude slash command) — when/how to call `/recall` + structure `/remember` payload | **Long** (design), anh Đức (concept review) | HIGH | D3-D4 |
| 10 | **MCP vs plain HTTP** — debate open. Argument MCP: 5 endpoints in PRD → Claude auto-discover; new tools no skill update. Argument HTTP: skill knows endpoint + schema is enough, less moving parts. Need to confirm: AgentBase agent native expose MCP? | both | HIGH | before D3 code |
| 11 | **PRD update needed:** §4 (Distillation) and §7 (Architecture) describe Qwen call inside AKC — superseded by 17:12 decision. anh Đức to revise PRD or note in `architecture_v1.md`. | anh Đức | MED | D2-D3 |
| 12 | **`/remember` payload schema** — pre-structured fields: `{task, approach_tried, why_failed, how_worked, outcome, tags}`. Lock the shape before skill design starts. | both | HIGH | D2 |
| 13 | **OpenClaw demo client** — provision separate OpenClaw agent (Marketplace 1-Click), workspace markdown configures the demo persona, skill to call AKC | Long (provision + skill), anh Đức (review demo flow) | HIGH | D5-D6 |
| 14 | **Track final: Automation & Integration vs General/Self-Evolving** — sync with anh Đức. Affects pitch framing + submission description. | both | MED | D5 |
| 15 | **Demo workflow scenario** — pick a concrete automation use case OpenClaw runs (e.g. "summarize daily feedback" with AKC pattern memory). Locks demo script. | both | MED | D6 |

---

## 7. Build plan (per PRD §11) — current view

| Day | Date | Focus | Owner | Status |
|---|---|---|---|---|
| D1 | 10/06 | Scaffold + provision AgentBase | chủ repo | DONE |
| D2 | 11/06 | `/recall` + `/remember` endpoints; folder restructure | **anh Đức** | IN-PROGRESS |
| D3 | 12/06 | LLM distillation (Qwen) | anh Đức | TODO |
| D4 | 13/06 | AgentBase Memory integration | anh Đức + chủ repo | TODO |
| D5 | 14/06 | Dockerize + deploy AgentBase | chủ repo (blocked on vCR) | BLOCKED |
| D6 | 15/06 | `/stats` + `/kb/export` + polish | both | TODO |
| D7 morning | 16/06 | Demo video + description | both | TODO |
| D7 noon | 17/06 12:00 | Submit | both | TODO |

---

## 8. How partner gets context quickly

**For anh Đức (or anyone joining):**
1. `git clone` + `git pull --rebase`
2. Read in order:
   - This doc (`docs/COORDINATION.md`)
   - `docs/prd/AKC_PRD.md`
   - `docs/architecture_v1.md`
   - `docs/06-agentbase-state-snapshot.md` (AgentBase state)
   - `docs/07-partner-claude-setup.md` (optional skill install)
3. Set up `.env` (ask chủ repo for shared values via private channel)
4. Verify with sanity check script in doc 07 §6

**For new sync calls / NotebookLM:**
- Drop transcript link in chat
- Whoever ingests first updates §5 (decisions) + §6 (open items) here

---

## 9. Lessons learned (running)

| Date | Lesson | Action taken |
|---|---|---|
| 2026-06-11 | Both pushed to `main` in parallel → stash drop nearly lost docs. | Recovered via `git fsck --lost-found`. Adopted §3 rules. |
| 2026-06-11 | docs-manager subagent leaked `.claude/agent-memory/` into repo root. | Cleaned. Note: agents writing memory should target working space `/Users/.../clawathon/.claude/`, NOT repo `dl_starter_kit/.claude/`. |
| 2026-06-11 | Pivoted direction 3× in one day (v1→v2→v3). | Authoritative doc is `docs/prd/AKC_PRD.md`. Everything else = history. |

---

## 10. Touchpoints to keep alive

- **Update this doc** when: a decision is made, a blocker resolves, a role shifts
- **Open items §6** is the canonical TODO — keep it tight
- **Don't archive** this file until after submission — it tracks the path

---

## 11. Architecture refinement (2026-06-11 17:12-17:21 chat with anh Đức)

**Supersedes PRD §4 (Distillation) and §7 (Architecture) where conflicting. PRD doc to be revised by anh Đức.**

```
┌────────────────────────────────────────────┐
│  Calling Agent (Claude Code / Qwen / ...)  │
│  - Does heavy work: extract task, approach │
│  - Pre-structures /remember payload         │
│  - Decides when to /recall vs not           │
└─────────────────┬──────────────────────────┘
                  │
                  │  [DEBATE: MCP vs plain HTTP — see open item #10]
                  │  - anh Đức (17:24): plain HTTP, skill knows schema
                  │  - Long (17:27): MCP, ≥3 tools → Claude auto-discover
                  ▼
┌────────────────────────────────────────────┐
│  AKC Agent (deployed on AgentBase)          │
│  - "thủ thư" — librarian storing patterns   │
│  - FastAPI HTTP endpoints                   │
│  - Thin orchestrator: receive + route       │
│  - NO inline LLM distillation               │
│  - MCP wrapper TBD (resolve before D3)      │
└─────────────────┬──────────────────────────┘
                  │
                  │  (also called by demo client)
                  ▲
┌────────────────────────────────────────────┐
│  Demo Client: OpenClaw agent (no-code)      │
│  - Provisioned via Marketplace 1-Click      │
│  - Markdown workspace = automation persona  │
│  - Has skill to call AKC /recall + /remember│
│  - Runs an automation use case for demo     │
│  - Shows AKC integration in real workflow   │
└────────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────┐
│  AgentBase Memory Service                   │
│  - Handles "distillation" (aggregate, dedup)│
│  - Stores Pattern records                   │
│  - Confidence tracking + tier promotion     │
│  - Semantic search for /recall              │
└────────────────────────────────────────────┘
```

**Key shifts vs initial PRD:**

| Aspect | PRD initial | After 17:12 chat |
|---|---|---|
| Distillation engine | Separate Qwen call inside AKC | **AgentBase Memory handles** it natively |
| /remember payload | Raw `what_happened` text | **Pre-structured** by calling Claude (task / approach_tried / why_failed / how_worked) |
| Heavy LLM work | Inside AKC service | **Inside calling agent (Claude)** |
| Integration | HTTP REST API | **MCP endpoint** (AgentBase exposes naturally) |
| AKC backend complexity | Moderate (FastAPI + Qwen + storage) | **Light** (FastAPI + AgentBase Memory client + thin routing) |

**Calling-side skill (Long owns design):**

This is a Claude Code slash command (e.g. `/akc-recall`, `/akc-remember`) that:
- Knows the MCP endpoint URL
- Builds structured /remember payload from current Claude task context
- Calls /recall automatically before task execution (optional auto-trigger)
- Interprets tier/confidence results to decide whether to use pattern
- Lives in `~/.claude/skills/akc-*/` for any Claude user

Open: where does this skill live? (separate repo for distribution, OR bundled in dl-starter-kit as `skills/` folder, OR contributed to unclaude-code).
