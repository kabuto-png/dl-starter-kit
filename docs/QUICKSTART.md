# Quickstart — AKC (Agent Knowledge Catalyst)

**For**: judges, reviewers, future adopters
**Time**: 5 phút để chạy demo

## Đây là gì?

AKC = HTTP memory layer cho AI agents. **Bất kỳ AI agent nào** (Claude Code, Codex, Gemini, OpenClaw...) cũng có thể:
- `POST /recall` — query past patterns trước khi làm task
- `POST /remember` — log outcome sau khi task xong
- Patterns auto-promote qua 3 tiers (experimental → production → gold) based on confidence

→ Compound learning, no vendor lock-in, no LLM retraining.

---

## 3 cách dùng (chọn 1)

### Cách 1 — Test trực tiếp qua curl (1 phút)

```bash
export AKC=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn

# Health
curl -sf "$AKC/health"

# Stats live
curl -sf "$AKC/stats" | python3 -m json.tool

# Recall patterns for JP launch
curl -sf -X POST "$AKC/recall" -H "Content-Type: application/json" \
  -d '{
    "task_context": "Plan JP launch keyword strategy",
    "tags": ["aso","jp","casual","keyword"],
    "top_k": 5,
    "min_tier": "production"
  }' | python3 -m json.tool

# Remember an outcome
curl -sf -X POST "$AKC/remember" -H "Content-Type: application/json" \
  -d '{
    "task_context": "Plan JP launch keyword strategy",
    "outcome": "Plan generated, user approved",
    "what_happened": "Applied kanji compound pattern, generated 12-keyword plan",
    "patterns_used": ["d25f02b1-52dd-4a23-a8de-070e0fd8a74c"],
    "success": true,
    "tags": ["aso","jp","casual","keyword"]
  }'
```

→ Stats counters tăng ngay sau call. Live evidence.

---

### Cách 2 — OpenClaw chat (2 phút) ⭐ Easiest cho non-dev

URL: **https://openclaw-111666-akc-oc.agentbase-runtime.aiplatform.vngcloud.vn/chat?session=demo**

Agent "**AKC ASO Specialist**" sẵn sàng. Gõ task bất kỳ:

```
Launch our casual game in Japan App Store next Tuesday. Need week-1 keyword strategy.
```

→ Agent tự call `/recall` → trả plan **cite pattern IDs thật** (vd `d25f02b1`) → tự call `/remember` sau khi user confirm.

**Test scenarios** (paste-ready):

| # | Test | Mục đích |
|---|---|---|
| 1 | "Launch casual game in Japan, week-1 keyword strategy" | Cold start, JP HERO pattern surface |
| 2 | "Same game now Korea Play Store. What transfers from JP?" | **Compound learning** — JP HERO recall lại |
| 3 | "Launch hyper-casual in Mongolia App Store" | Empty recall — agent KHÔNG bịa pattern IDs |

Verify stats:
```bash
curl -sf "$AKC/stats" | grep -E "total_queries|total_outcomes"
```

→ `total_queries` tăng theo số test, `total_outcomes` tăng khi user confirm plan.

---

### Cách 3 — Claude Code skill (5 phút) — cho devs

Skill `akc-recall-task-remember` đã packed sẵn trong repo. Bất kỳ AI coding agent CLI (Claude Code / Codex / Gemini / Aider...) đều dùng được qua `AGENTS.md`.

```bash
# Clone repo
git clone https://github.com/kabuto-png/dl-starter-kit
cd dl-starter-kit

# Set AKC endpoint
export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn

# Open in Claude Code (or Codex/Gemini)
claude  # or: codex, gemini, aider...

# Skill auto-activates on task start
> Debug 500 error in /signup endpoint
# → skill calls /recall before, /remember after
```

Skill structure:
```
skill/
├── SKILL.md          ← YAML frontmatter + pushy description
├── references/
│   ├── tags-taxonomy.md   ← 5 categories, 30+ recommended tags
│   ├── tier-semantics.md  ← gold/production/experimental rules
│   └── error-patterns.md  ← failure modes + recovery
├── examples.md       ← good/bad task_context samples
└── evals/evals.json  ← 6 test cases (incl anti-hallucination)
```

Universal AGENTS.md ở root cho 4 platforms:
- `AGENTS.md` (Codex / universal)
- `.codex/AGENTS.md`
- `.gemini/GEMINI.md`
- `.antigravity/skill.md`

---

## File references

| Path | Mục đích |
|---|---|
| `README.md` | Project overview, deployment details |
| `docs/AKC-ORIENTATION.md` | Architecture deep-dive |
| `docs/test-guide-anh-duc.md` | Dev test guide (curl-based) |
| `docs/oc-user-test-anh-duc.md` | User-role test guide (ASO Specialist) |
| `docs/openclaw-integration.md` | OC config approach (Phase 1+2+3) |
| `docs/06-agentbase-state-snapshot.md` | Live deploy state |
| `main.py` | FastAPI server source |
| `akc/` | Core memory module |
| `kb_data/patterns.jsonl` | 30 seed patterns |

---

## Live state (D5 16:30 ICT)

```
AKC endpoint:    endpoint-30123c53-... (ACTIVE)
OC instance:     openclaw-111666-akc-oc (ACTIVE, ASO Specialist agent)
Patterns:        34 (30 seed + 4 generated D5)
Queries:         14 total (across all tests)
Outcomes:        4 recorded
Gold tier:       6 patterns
Self-promotion:  HERO d25f02b1 (production → gold @ 2026-06-15 04:25 UTC)
```

---

## Pitch in 30 seconds

> **Problem**: AI agents are stateless. Every task starts from zero. Knowledge dies with team members.
>
> **AKC fixes this**: HTTP memory layer. Any AI agent calls `/recall` before tasks, `/remember` after. Patterns promote across tiers based on real outcomes. No retraining. No vendor lock-in.
>
> **Proof**: 34 patterns live. 3 demo scenarios end-to-end (JP cold → KR compound → MN empty-recall anti-hallucination). Universal AGENTS.md works on Claude Code, Codex, Gemini, OpenClaw — same memory.

---

## Submission

- **Track**: Automation & Integration
- **Team**: DL Starter Kit (team 23) · VNG Publishing
- **Deadline**: 2026-06-17 12:00 ICT
- **Trailer**: `plans/260615-1619-video-analysis/AKCTrailer_v4.mp4` (45s)
- **Pitch deck**: `plans/260615-1545-pitch-deck/deck/akc-pitch.html` (8 slides)
- **Repo**: github.com/kabuto-png/dl-starter-kit (public, Apache-2.0)

## Unresolved questions

- Có muốn ship Zalo bot channel cho OC (bonus, 1-2h work)?
- Submission writeup tone: AKC self-evolution focus, hoặc multi-agent universal focus?
- Demo video v4 final hay cần thêm pass?
