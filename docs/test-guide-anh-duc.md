# AKC Test Guide for anh Đức

**Audience**: anh Đức (backend lead, PRD author) — verify deployed AKC matches PRD contract.
**Endpoint**: `https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn`
**Deploy date**: D5 2026-06-15
**Status**: ACTIVE

---

## TL;DR — 30-second verification

```bash
export AKC=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn

# 1. Health check
curl -sf "$AKC/health"
# Expect: {"status":"ok","pattern_count":30}

# 2. Tier distribution (PRD §5)
curl -sf "$AKC/stats" | python3 -m json.tool

# 3. Recall ASO JP patterns (demo persona scenario)
curl -sf -X POST "$AKC/recall" \
  -H "Content-Type: application/json" \
  -d '{"task_context":"launch casual game Japan keyword strategy","tags":["aso","jp"],"top_k":3,"min_tier":"production"}' \
  | python3 -m json.tool
```

If all 3 calls return 200 with expected shape, AKC is fully operational.

---

## Full Test Plan (per PRD section)

### Test 1 — GET /health (PRD §5: health check)

```bash
curl -sv "$AKC/health"
```

**Expected** (200 OK):
```json
{"status":"ok","pattern_count":30}
```

**Note**: pattern_count = 30 confirms baked seed loaded.

### Test 2 — GET /stats (PRD §5: KB health snapshot)

```bash
curl -sf "$AKC/stats" | python3 -m json.tool
```

**Expected fields**: total_patterns, by_tier {gold,production,experimental,demoted}, avg_confidence, top_tags (top 10 lowercase deduped), recall_hit_rate, recently_promoted, total_queries, total_outcomes_recorded.

### Test 3 — POST /recall (PRD §5: pattern retrieval)

```bash
curl -sf -X POST "$AKC/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "launch casual game Japan keyword strategy",
    "tags": ["aso", "jp"],
    "top_k": 3,
    "min_tier": "production"
  }' | python3 -m json.tool
```

**Expected**: 3 patterns. First should be HERO `d25f02b1-...` (JP keyword research, confidence 0.76, tier production) matching storyboard math.

### Test 4 — POST /remember (PRD §5: outcome recording)

```bash
curl -sv -X POST "$AKC/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "test from anh Đức",
    "outcome": "success",
    "what_happened": "Verification test — applied hiragana keyword strategy from recalled pattern",
    "patterns_used": ["d25f02b1-52dd-4a23-a8de-070e0fd8a74c"],
    "success": true,
    "tags": ["test", "verification"]
  }'
```

**Expected**: HTTP 202 Accepted with empty body. Background task runs LLM distillation + store append + confidence update.

After ~2s, re-query /stats and check `total_outcomes_recorded: 1` and `pat_aso_jp_001` confidence bumped from 0.76 → 0.81.

### Test 5 — POST /kb/export (PRD §5: markdown audit trail)

```bash
curl -sf -X POST "$AKC/kb/export" \
  -H "Content-Type: application/json" \
  -d '{}' > /tmp/akc-export.md
head -50 /tmp/akc-export.md
```

**Expected**: Markdown document listing Gold + Production patterns with full `context`, `what_worked`, `what_failed`, `confidence`, `tags`, `times_applied` fields.

### Test 6 — Confidence engine (PRD §9: Bayesian update or fixed deltas)

Cycle pattern through success/failure to observe confidence change:

```bash
PATTERN_ID="d25f02b1-52dd-4a23-a8de-070e0fd8a74c"

# Call /remember 3× with success
for i in 1 2 3; do
  curl -sf -X POST "$AKC/remember" -H "Content-Type: application/json" \
    -d "{\\"task_context\\":\\"loop test $i\\",\\"outcome\\":\\"success\\",\\"patterns_used\\":[\\"$PATTERN_ID\\"],\\"success\\":true}"
  sleep 3  # let background task complete
done

# Check confidence + tier
curl -sf "$AKC/stats" | python3 -m json.tool | grep -A 5 "recently_promoted"
```

**Expected**: After 3 successes, HERO pattern crosses Gold threshold (0.85). `recently_promoted` should list it.

### Test 7 — Demo storyboard end-to-end (Scene 1 + Scene 2)

Manual: simulate the 2-scene demo with curl calls. Detailed in `plans/260613-0000-clawathon-L/storyboard-demo-2scene.md`.

---

## Verification Against PRD Contract

Match each PRD section to deployed behavior:

| PRD Section | Endpoint/Behavior | Verified? |
|---|---|---|
| §3 Pattern Model | Pattern fields: id, context, what_worked, what_failed, tags, confidence, tier, times_applied, consecutive_failures, last_updated | ✅ via /recall response |
| §4 Distillation | Gemma 4-31b-it (OpenAI-compatible MaaS) extracts from outcome → structured Pattern | ✅ via /remember + background task |
| §5 API | 5 endpoints: /recall, /remember, /stats, /kb/export, /health | ✅ all 5 + /invocations stub |
| §6 Storage | JSONL append-only + AgentBase Memory Service | ✅ visible via /stats |
| §7 Architecture | Feature-first FastAPI, BackgroundTasks for /remember | ✅ 202 returned immediately |
| §9 Confidence Engine | Tier transitions (gold ≥0.85, prod ≥0.70, exp ≥0.50, demoted <0.50) | ⚠️ Code uses fixed deltas (+0.05/-0.10), PRD §9 specifies Beta dist. Drift documented in qc-spec-validation report. |
| §10 Configuration | LLM_*, MEMORY_ID, AKC_KB_DIR env vars | ✅ all injected at runtime |
| §12 Layout | Module structure matches PRD §12 closely | ✅ |

---

## Known Drift from PRD (anh Đức to decide)

1. **Confidence formula**: Code uses fixed deltas `+0.05`/`-0.10`. PRD §9 mandates Beta distribution with `alpha/(alpha+beta)`. See `plans/reports/qc-spec-validation-260614-1116-pre-submission.md` SPEC-1.
2. **INIT_CONFIDENCE**: Code = 0.67. PRD §5 demo + §10 = 0.55. SPEC-2.
3. **`times_succeeded` field**: PRD §4 example includes; code doesn't expose. SPEC-4.

These are non-blocking for D7 submission — code behavior is sensible and self-correcting. anh Đức can decide post-hackathon whether to align code → PRD or update PRD → code.

---

## Troubleshooting

### Endpoint returns 503 / connection refused
- Runtime may be UPDATING (deploy in progress). Wait ~90s, retry.
- Check status: see `docs/06-agentbase-state-snapshot.md` for runtime ID + IAM URL.

### /remember returns 202 but stats doesn't reflect outcome
- Background task may have failed (LLM timeout, validation error). Check endpoint logs via AgentBase Console at https://aiplatform.console.vngcloud.vn/runtime.
- /remember has retry safety net for Memory Service sync but tolerates failures.

### Memory Service semantic recall not working
- Optional — JSONL fallback always active. /recall works regardless.
- AgentBase auto-injects GREENNODE_CLIENT_ID/SECRET/AGENT_IDENTITY into runtime; Memory client uses these for OAuth.

---

## Skill Setup (optional — for Claude Code users)

```bash
mkdir -p ~/.claude/skills/akc-recall-task-remember
cp skill/SKILL.md ~/.claude/skills/akc-recall-task-remember/
export AKC_ENDPOINT="$AKC"
```

Now any task in Claude Code triggers /recall + /remember loop automatically (when skill is loaded by Claude's prompt-matching).

---

## Submission checklist for anh Đức

- [ ] Smoke test passes (Tests 1-3 above)
- [ ] Demo storyboard runs (Test 7)
- [ ] PRD drift items reviewed (SPEC-1/2/4)
- [ ] L direction confirmed via Telegram
- [ ] LLM choice approved (Gemma 4-31b-it post A/B test)
- [ ] Reference customer quote (em ASO team) — optional

---

**Status**: ACTIVE D5. Ready for D6 demo recording.
