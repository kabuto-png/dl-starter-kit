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

## Full Flow Test via Claude Code (AI agent, NOT curl)

**Goal**: Verify that Claude Code automatically fires `/recall` + `/remember` against the live AKC endpoint, end-to-end like a real ASO Specialist would.

### Setup (1 phút)

```bash
# 1. Clone repo locally
git clone https://github.com/kabuto-png/dl-starter-kit.git
cd dl-starter-kit

# 2. Install AKC skill into Claude Code
mkdir -p ~/.claude/skills/akc-recall-task-remember
cp skill/SKILL.md ~/.claude/skills/akc-recall-task-remember/

# 3. Export endpoint env var (skill reads this)
export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn

# 4. (Optional) Persist for future shells
echo 'export AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn' >> ~/.zshrc
```

### Verify skill loaded

Mở Claude Code (terminal-based hoặc IDE extension), gõ:

```
list available skills
```

Claude trả lời danh sách, trong đó phải có `akc-recall-task-remember`. Nếu không thấy → skill chưa load, check path `~/.claude/skills/akc-recall-task-remember/SKILL.md`.

---

### Scene 1 — JP Cold Start (full AI flow)

**Anh Đức gõ prompt** (copy paste exact):

```
Tôi là ASO Specialist VNG Publishing. Tuần này phải launch 1 casual game (genre 放置RPG) ở App Store Japan. Đây là geo đầu tiên, team chưa có data nội bộ. Cần week-1 keyword strategy: pick title + subtitle keywords để max impression trong 7 ngày đầu.
```

**Expected Claude behavior** (skill auto-triggers):

1. Claude reads `akc-recall-task-remember/SKILL.md`, recognizes "any task start" trigger
2. **Auto-fire** `POST /recall` với:
   - `task_context`: kiểu "week-1 keyword strategy for Casual game JP launch"
   - `tags`: `["aso", "japan", "casual", "keyword-research"]`
   - `top_k`: 3-5
   - `min_tier`: `"production"`
3. AKC trả về 3 patterns top:
   - HERO `d25f02b1-...` (kanji vs romaji, confidence ~0.81 sau test trước)
   - Screenshot CTR pattern (production)
   - Release cadence pattern (gold)
4. Claude **suggest plan** dùng `what_worked` từ patterns:
   - "Theo team's past experience: target kanji compound terms (3-5x volume), submit metadata Tuesday JST, lead screenshot với high-tension gameplay frame 1..."
5. **Auto-fire** `POST /remember` (fire-and-forget):
   - `task_context`: same
   - `outcome`: `"success"` (hoặc summary)
   - `patterns_used`: list of pattern IDs Claude actually used
   - `success`: `true`
   - `tags`: ASO-related

**How to verify Claude actually called /recall**:

Sau khi Claude trả lời, check:

```bash
curl -sf "$AKC_ENDPOINT/stats" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"total_queries: {d['total_queries']}\")"
```

`total_queries` phải tăng +1 sau mỗi prompt. Nếu không tăng → skill không fire (Claude không hiểu trigger).

**How to verify Claude called /remember**:

```bash
curl -sf "$AKC_ENDPOINT/stats" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"total_outcomes_recorded: {d['total_outcomes_recorded']}\")"
```

`total_outcomes_recorded` phải tăng +1.

Cũng có thể check HERO confidence bumped:

```bash
curl -sf -X POST "$AKC_ENDPOINT/recall" \
  -H "Content-Type: application/json" \
  -d '{"task_context":"JP keyword","tags":["aso","jp","keyword"],"top_k":1,"min_tier":"production"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); p=d['patterns'][0]; print(f\"HERO confidence: {p['confidence']}, times_applied: {p['times_applied']}\")"
```

Mỗi lần Claude fire success → HERO confidence +0.05.

---

### Scene 2 — KR Compound Recall (anh Đức trải nghiệm compound learning)

**Anh Đức mở session Claude Code MỚI** (đóng session cũ — quan trọng để chứng minh memory ở AKC chứ không phải Claude session).

**Prompt** (copy paste):

```
Cùng casual game đó, giờ tới phase launch ở Korea Play Store. Tuần trước đã launch JP rồi (kết quả tốt). Tuần 1 KR muốn áp dụng learning từ JP + add KR-specific knowledge. Cho tôi keyword + creative + release timing plan.
```

**Expected behavior**:

1. Claude **auto-fire** `/recall` với tags `["aso", "korea", "casual", "keyword-research"]` hoặc tương tự
2. AKC trả về:
   - HERO JP pattern (vẫn surface vì same `aso` + `keyword` tag) — confidence giờ đã 0.81+ sau Scene 1
   - KR-specific patterns nếu có seed (KR Play Store title cap, KR localized description)
3. Claude generate plan dùng INSIGHTS từ JP (hangul long-tail keywords, dual-submit ONE Store + Play Store, KakaoTalk integration)
4. **Auto-fire** `/remember` với `success: true` + `patterns_used: ["<HERO-id>", "<KR-pattern-id>"]`
5. **Compound moment**: HERO confidence 0.81 + 0.05 = **0.86 → Gold tier crossed**

**Verify Gold promotion**:

```bash
curl -sf "$AKC_ENDPOINT/stats" | python3 -m json.tool
```

Look for:
- `total_outcomes_recorded: 2` (sau Scene 1 + Scene 2)
- `recently_promoted: [{"pattern_id": "d25f02b1-...", ...}]` ← HERO appeared here ✨
- `by_tier.gold`: 5 → 6 (HERO joined Gold tier)

Hoặc /kb/export sẽ list HERO ở section Gold:

```bash
curl -sf -X POST "$AKC_ENDPOINT/kb/export" -H "Content-Type: application/json" -d '{}' | head -30
```

---

### Verification Cheat Sheet (run before + after Claude session)

**Before Scene 1**:
```bash
curl -sf "$AKC_ENDPOINT/stats" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Q={d['total_queries']}, O={d['total_outcomes_recorded']}, Gold={d['by_tier']['gold']}\")"
```

**After Scene 1**:
- `Q` should be `+1`
- `O` should be `+1`
- HERO confidence bumped 0.05

**After Scene 2**:
- `Q` `+1` again (total +2 from baseline)
- `O` `+1` again (total +2 from baseline)
- `Gold` should be `+1` (HERO promoted)
- `recently_promoted` should list HERO

---

### Common Pitfalls

| Issue | Cause | Fix |
|---|---|---|
| Claude không fire /recall | Skill không load hoặc prompt không match trigger description | Check `~/.claude/skills/akc-recall-task-remember/SKILL.md` exists; restart Claude Code; explicitly say "use the akc skill" in prompt |
| `total_queries` không tăng | Skill fired nhưng /recall fail (network) | Check `$AKC_ENDPOINT` env set; smoke test `curl $AKC_ENDPOINT/health` |
| HERO confidence không bump | Claude gửi `success: false` hoặc thiếu `patterns_used` | Check Claude response — ask "what pattern IDs did you call /remember with?" |
| Scene 2 không thấy HERO ở recall | Tag mismatch — Scene 2 dùng tags không overlap với HERO's tags `["aso","keyword","jp","app-store"]` | Add `keyword` hoặc `aso` tag explicit trong Scene 2 prompt context |

---

## Skill Setup Path (basic — for non-Claude-Code testing)

Nếu anh Đức không dùng Claude Code, vẫn có thể test thủ công bằng curl theo Tests 1-7 ở trên.

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
