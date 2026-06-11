# La Bàn AI — Current State & Execution Plan (2026-06-11)

**Hackathon:** Claw-a-thon 2026 | **Track:** Agentic Assistant | **Team:** DL Starter Kit (Nhóm 1) | **Submission Deadline:** 2026-06-17 12:00 (6 days remaining)

---

## Status Summary

| Dimension | Status | Last Update |
|-----------|--------|-------------|
| **Project Phase** | D2 of 7 (Phase 1 closure in progress) | 2026-06-11 |
| **Days Elapsed / Remaining** | 1 day elapsed (D1 10/06 workshop); 6 days remaining | Deadline 17/06 12:00 |
| **Original vs Current** | ~12h behind D1-evening checkpoint | Plan issued 10/06 14:53; wizard setup ongoing |
| **Overall Health** | YELLOW — on track if P0 items completed D2-D5 | ~75-80% win probability per brainstorm §10 |

---

## Artifact Status Table

| Artifact | Expected | Status | Owner | Blocker | Notes |
|----------|----------|--------|-------|---------|-------|
| **Infrastructure** | | | | | |
| IAM config (`.greennode.json`) | D1 | DONE | Wizard | None | Auto-provisioned |
| Identity `dl-starter-kit` | D1 | DONE | Wizard | None | Confirmed in platform |
| Memory store `memory-0b08d38f-...` | D1 | DONE | Wizard | None | CUSTOM strategy `la-ban-ai-coach` TBD |
| CUSTOM strategy (3-field extraction) | D1 | BLOCKED | Dev A | Wizard | Add strategy def to memory (turn count allowance) |
| LLM API key (Gemma/Qwen enable) | D1 | TODO | Dev A | .env config | Need `/agentbase-llm` skill activation + smoke test |
| **Code Scaffold** | | | | | |
| main.py skeleton (remember/recall tools) | D1 | DONE | Both | None | 138 LOC; basic LangChain setup with AgentBaseMemoryEvents |
| 3-layer LLM fallback wrapper | D2 | TODO | Dev A | .env LLM_* | AIP Gemma → Qwen → Ollama chain |
| 6-step pipeline orchestrator | D3-D4 | TODO | Dev A | fallback wrapper | Integrates: intent, recall, pii, improve, forward, remember |
| **Templates (Core Moat)** | | | | | |
| 5 Dept templates (BI/UA/Dev/HR/Designer) | D2-D3 | NOT STARTED | Dev B | None | Draft due D2 EOP |
| **Pipeline Tools** | | | | | |
| `pii_detector` (regex-first) | D3 | TODO | Dev A | None | Cuts 1 LLM call; fallback to LLM if regex miss |
| `recall_user_context` (Identity SSO) | D3 | TODO | Dev A | **SSO dept/title access** | Needs Identity service to expose dept/title |
| `improve_prompt` (template rewrite) | D3 | TODO | Dev B | templates DONE | Applies dept template + rewrites |
| `remember_pattern` (Memory CUSTOM extract) | D3 | TODO | Dev B | CUSTOM strategy DONE | Extracts role/topic/output_format (3 fields only) |
| **Deliverables** | | | | | |
| Runtime deploy (AgentBase Runtime) | D5 | TODO | Dev A | Pipeline DONE + latency bench | Public `/invocations` + `/health` |
| Latency benchmark | D5 | TODO | Dev A | Runtime DONE | p95 ≤ 3s total (287ms pipeline excl. LLM) |
| Pitch deck 5 slides | D5 | TODO | Dev B | None | Lock structure D5 EOP |
| Cookbook 8-10 pages (GreenNode artifact) | D6 | TODO | Both | Runtime + bench DONE | Strategic: Memory CUSTOM methodology |
| Repo polish (README/tests/benchmarks) | D6 | TODO | Both | Code DONE | Public GitHub |
| Demo video (3-act script) | D7 | TODO | Both | All above | Record D7 morning; backup pre-recorded |

---

## Critical Code Gaps vs Target Pipeline

**Current State (main.py, 138 LOC):**
- Step 2 (recall_user): PARTIAL — recall() tool exists, no namespace filtering by dept
- Step 5 (forward_to_llm): PARTIAL — ChatOpenAI() direct call, no fallback chain
- Step 6 (async_remember): PARTIAL — remember() tool exists, no CUSTOM 3-field extraction
- Missing: Steps 1 (detect_intent), 3 (pii_detector), 4 (improve_prompt) entirely
- Missing: Orchestrator that chains steps 1-6 as pipeline (no agent definition)

**What needs to be built D2-D4:**

```
Input: user message + context headers
  ↓
Step 1: detect_intent (role + task from user_id + prompt) — NEW TOOL
  ↓
Step 2: recall_user_context (Memory.search by /strategies/la-ban-ai-coach/actors/{userId}) — ENHANCE
  ↓
Step 3: pii_detector (regex → LLM fallback if regex hits) — NEW TOOL
  ↓
Step 4: improve_prompt (apply VNG dept template + rewrite) — NEW TOOL
  ↓
Step 5: forward_to_llm (3-layer: AIP Gemma → Qwen → Ollama) — ENHANCE + WRAP
  ↓
Step 6: async_remember (extract 3 fields: role/topic/output_format → Memory) — ENHANCE
  ↓
Output: response + transparency footer
```

**Orchestrator**: Single entry point (e.g., `coach_chat(user_id, message, dept, title)`) that runs steps 1-6 sequentially with error handling.

---

## 7-Day Execution Plan

### Phase Assignments

| Day | Date | Owner | Focus | Dependencies | Status |
|-----|------|-------|-------|--------------|--------|
| **D1** | 10/06 eve | Both | Workshop + wizard scaffold | None | IN-PROGRESS |
| | | | - IAM config (DONE) | | |
| | | | - Identity + Memory provision (DONE) | | |
| | | | - CUSTOM strategy `la-ban-ai-coach` + main.py TBD | Wizard turn allowance | |
| **D2** | 11/06 | Dev A | LLM + fallback wrapper | CUSTOM strategy DONE | TODO |
| | | | - Verify LLM_* env vars via `/agentbase-llm` | | |
| | | | - Smoke test Gemma/Qwen ChatOpenAI wrapper | .env keys | |
| | | | - Implement 3-layer fallback (AIP → OpenAI → Ollama) | | |
| | | | - Local e2e test step 5 only | | |
| | **11/06** | Dev B | Template draft | None | TODO |
| | | | - BI dept template (sample) | | |
| | | | - UA dept template (sample) | | |
| | | | - Lock structure for remaining 3 (Dev/HR/Designer) | | |
| **D3** | 12/06 | Dev A | Pipeline tools phase 1 | Fallback DONE | TODO |
| | | | - `pii_detector` (regex-first, LLM fallback) | | |
| | | | - `recall_user_context` (Identity SSO dept/title) | **Q1: dept/title exposed?** | |
| | | | - Local test steps 1-3 | | |
| | **12/06** | Dev B | Pipeline tools phase 2 | Templates DONE | TODO |
| | | | - `improve_prompt` (apply template + rewrite) | | |
| | | | - `remember_pattern` (Memory CUSTOM extract) | CUSTOM strategy DONE | |
| | | | - Local test steps 4, 6 | | |
| **D4** | 13/06 | Both | Pipeline integration + e2e | All tools DONE | TODO |
| | | | - Orchestrator implementation | | |
| | | | - Full local end-to-end test (steps 1-6) | | |
| | | | - Transparency footer implementation | | |
| | | | - Code review + simplification | | |
| **D5** | 14/06 | Dev A | Deploy + benchmark | Pipeline DONE | TODO |
| | | | - Deploy to AgentBase Runtime | | |
| | | | - Verify `/invocations` + `/health` endpoints | **Q2: autoscale limits?** | |
| | | | - Latency benchmark (p95 ≤ 3s) | | |
| | **14/06** | Dev B | Pitch structure | None | TODO |
| | | | - 5-slide deck lock (safety/memory/benchmark/moat/demo) | | |
| **D6** | 15/06 | Both | Cookbook + repo polish | Deployed + deck DONE | TODO |
| | | | - Cookbook 8-10 pages (Memory CUSTOM methodology) | | |
| | | | - README (setup, usage, benchmarks) | | |
| | | | - Test suite (unit: tools, integration: pipeline) | | |
| | | | - Repo finalization (no secrets, public OK) | **Q3: public repo legal?** | |
| **D7 AM** | 16/06 | Both | Demo video record | All above | TODO |
| | | | - Rehearse 3-act script (safety/memory/benchmark) | | |
| | | | - Record primary video (2-3 min) | | |
| | | | - Record backup video | | |
| **D7 PM** | 17/06 AM | Both | Final submission | Video DONE | TODO |
| | | | - Dry-run endpoint | | |
| | | | - Final video check | | |
| | | | - Submit before 12:00 | | |

### Priority Tiers

| Tier | Items | Owner | If Slipping |
|------|-------|-------|------------|
| **P0 (MUST)** | D1-D5 working demo (steps 1-5 locally) + 1 dept template (BI) + runtime deploy | Both | No cuts; extend D7 hours if needed |
| **P1 (NICE)** | 5 templates + cookbook + repo polish (tests/README) + pitch deck | Both | Cut cookbook to 4 pages; skip fancy tests |
| **P2 (CUTLINE)** | SDK packaging, B2B SaaS pitch, advanced visualizations | Dev B | First cut if time-boxed |

---

## Recovery Actions for Today (D2, 2026-06-11)

**Owner: Dev A** — Unblock .env + LLM setup (2-3 hours)

1. **Verify .env has LLM_* keys**
   - Check: LLM_MODEL, LLM_BASE_URL, LLM_API_KEY set
   - If missing: Use `/agentbase-llm` skill to retrieve platform key
   - Confirm vars in `.env` (not just shell exports)
   - Reference: `main.py` lines 32-39 require all three

2. **Smoke test Gemma/Qwen via ChatOpenAI wrapper**
   - Update `main.py` lines 41-45 to test fallback chain (mock Gemma error → Qwen fallback)
   - Quick script: `python main.py --test-llm <model-name>`
   - Expected: Both Gemma and Qwen respond to "hello" within 5s
   - If Gemma fails: Verify AIP cluster + token not rate-limited

3. **Confirm CUSTOM memory strategy `la-ban-ai-coach`**
   - Check GreenNode platform: Memory ID `memory-0b08d38f-...` → Strategies
   - If missing: Create via platform UI or POST `/memory/{id}/strategies`
   - Schema (3 fields):
     ```json
     {
       "id": "la-ban-ai-coach",
       "extraction_prompt": "Extract: (1) user role, (2) primary topic, (3) desired output format",
       "fields": ["role", "topic", "output_format"]
     }
     ```
   - Validate: memory_client.insert/search works with namespace `/strategies/la-ban-ai-coach/actors/{userId}`

4. **Begin 3-layer fallback wrapper (Dev A)**
   - Create file `./src/llm_fallback.py` (~40 LOC)
   - Implement class `FallbackLLM(BaseLLM)` chaining: AIP Gemma → OpenAI fallback → Ollama local
   - Error handling: Timeout (10s) → next layer; all 3 fail → return error token
   - Test: Unit test for each layer + integration test (mock all 3 fail)
   - Integrate into main.py step 5 by D2 EOP

5. **Begin template drafting (Dev B)**
   - Create file `./src/templates/bi_department.md` (BI dept system prompt)
   - Create file `./src/templates/ua_department.md` (UA dept system prompt)
   - Locks content for steps 3-4 (pii_detector, improve_prompt)
   - Deliverable: 2-3 paragraph templates; structure for Dev/HR/Designer to follow

**Success Criteria (D2 EOP):**
- [ ] .env LLM_* vars confirmed and tested
- [ ] Gemma + Qwen both respond to test prompt
- [ ] CUSTOM strategy created and memory.search works
- [ ] Fallback wrapper code compiles (no test required yet)
- [ ] BI + UA templates drafted (can be incomplete, structure locked)

---

## Open Questions (Carry Forward from Brainstorm)

| # | Question | Impact | Owner | Resolve By |
|---|----------|--------|-------|-----------|
| Q1 | **Identity service expose dept/title from VNG SSO?** | Blocks `recall_user_context` tool (step 2) | Dev A | D3 (mock if unavailable) |
| Q2 | **Runtime autoscale limits?** | Affects demo day concurrent load stress | Dev A | D5 |
| Q3 | **Public GitHub repo legal OK?** (Rulebook 1.2 says public) | Required for submission | Dev B | D6 (confirm with BTC/legal) |
| Q4 | **Cookbook reviewed by GreenNode docs team before D7?** | Delivery artifact quality | Dev B | D6 EOP (submit early) |
| Q5 | **Submission order affects score ranking?** | Submission strategy | Both | Ask BTC PIC MaiNTT7 (D6) |

---

## Latency Target Validation

Target: **p95 ≤ 3 seconds total** (287ms pipeline excl. main LLM call)

| Step | Estimated p95 (ms) | Notes |
|------|------------------|-------|
| 1. detect_intent | 5 | Local regex/prompt |
| 2. recall_user_context | 50 | Memory search, 10 results |
| 3. pii_detector | 15 | Regex + 1 LLM call if hit |
| 4. improve_prompt | 20 | LLM rewrite (fast) |
| 5. forward_to_llm | 2000-2500 | AIP Gemma main call (excl. fallback cost) |
| 6. async_remember | 5 | Fire-and-forget to Memory |
| **Pipeline overhead** | 90 | Network + serialization |
| **Total (excl. main LLM)** | 185-190 ms | Target: <287ms (cushion for debug ops) |
| **Total (incl. main LLM)** | 2185-2690 ms | p95 <3000ms achievable |

**Benchmark plan (D5):** Run 100 requests with varied payloads; measure latencies at p50/p95/p99.

---

## Key Assumptions (Risk Factors)

| Assumption | Rationale | Fallback |
|-----------|-----------|----------|
| CUSTOM memory strategy allows 3-field extraction | Narrower scope = higher success | Manual string parsing if schema unavailable |
| Identity service exposes dept/title | "Day 1 insight" feature core differentiator | Mock dept/title in recall_user_context |
| AIP Gemma doesn't rate-limit during demo | Pod allocated; token limit 5M | Qwen fallback + OpenAI if needed |
| Public GitHub repo legally OK | Rulebook 1.2 (public required); GreenNode internal | Clarify with BTC D6 — private if blocked |
| 2 devs sufficient for D2-D5 tasks | Non-overlapping: Dev A (infra/tools), Dev B (templates/cookbook) | Parallel + commit frequently to avoid conflicts |

---

## Success Metrics

**By 2026-06-17 12:00:**

- [ ] Runtime endpoint deployed and public-accessible
- [ ] `/health` returns `HEALTHY`
- [ ] `/invocations` accepts coach pipeline requests
- [ ] Demo video shows 3 acts (safety demo 45s, memory demo 90s, benchmark 45s)
- [ ] Cookbook submitted (8-10 pages, GreenNode artifact)
- [ ] README + tests in GitHub public repo
- [ ] Latency benchmark: p95 ≤ 3s reported
- [ ] 1+ dept template (BI) + structure for 4 others

**Win Probability:** ~75-80% per brainstorm §10 (assuming P0 items hit D2-D5 checkpoints).

---

## Notes for Partner Session

1. **This document captures ground truth as of 2026-06-11 11:00 UTC+7.** Code state: main.py scaffold (138 LOC), .env unconfigured, no pipeline yet.

2. **Do not assume phase files exist** (phase-01 through phase-06). These are referenced in plans/ but not yet created as separate docs. Use brainstorm + this document as authoritative.

3. **Dev A focus:** Infrastructure, LLM integration, pipeline tools (pii_detector, recall_user_context), runtime deploy.  
   **Dev B focus:** Templates (BI/UA/Dev/HR/Designer), improve_prompt tool, remember_pattern tool, cookbook + pitch.

4. **Blocker watch:** CUSTOM memory strategy (D1), Identity SSO dept/title access (D3), public repo legal (D6).

5. **Commit early and often.** Git worktrees recommended if parallel branches; main stays stable for runtime deploy.

6. **Demo dry-run:** Schedule for D7 morning (before record). Backup video plan: pre-recorded fallback if live demo fails.

---

**Document Created:** 2026-06-11 | **Status:** ACTIVE | **Next Review:** 2026-06-12 (D3 morning)
