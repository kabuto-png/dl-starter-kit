# OpenClaw Demo Client Integration

**Purpose**: Connect a GreenNode OpenClaw agent to the live AKC backend, creating a no-code demo client that automates the ASO Specialist workflow. AKC = compound memory; OpenClaw = the agent that uses it.

**Status**: Plan ready, requires Console UI provisioning (IAM API denied for OC creation by service account)

---

## Architecture

```
┌─────────────────────────────────────────┐
│ OpenClaw Workspace                      │
│ Persona: ASO Specialist VNG Publishing  │
│ Workflow: recall → plan → remember loop │
└────────────────┬────────────────────────┘
                 │ HTTPS POST /recall, /remember
                 ▼
┌─────────────────────────────────────────┐
│ AKC Runtime (LIVE)                      │
│ runtime-577cd07b-...                    │
│ Endpoint: endpoint-30123c53-...         │
└─────────────────────────────────────────┘
```

Both run on the same GreenNode AgentBase tenant; outbound HTTPS between them works intra-platform.

---

## Provisioning Steps (Console UI)

The OpenClaw provisioning API requires elevated IAM permissions not available to our service account. Use the Console:

1. Login https://aiplatform.console.vngcloud.vn with VNG SSO
2. Navigate **Runtime** → **OpenClaw** OR **Marketplace** → **1-Click OpenClaw**
3. Provision new OC instance:
   - **Name**: `akc-oc-demo`
   - **Flavor**: `runtime-s2-general-2x4` (2 vCPU / 4 GB sufficient for demo)
   - **Region**: same as AKC runtime
4. Get the OC workspace URL after provisioning completes
5. Open OC workspace, paste the [Workspace Configuration](#workspace-configuration) markdown below as agent instructions
6. In OC environment settings, set:
   ```
   AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn
   ```
7. Run [verification tests](#verification-tests) to confirm OC → AKC connectivity

---

## Workspace Configuration

Paste this markdown into the OpenClaw workspace as agent instructions:

```markdown
# Agent: ASO Specialist (AKC Demo)

You are an ASO (App Store Optimization) specialist at VNG Publishing. Your job: plan keyword + creative + release strategy for mobile games launching across multiple geos (JP / KR / VN / TH / PH).

You have access to AKC (Agent Knowledge Catalyst), a team memory service. Before any task, you MUST query AKC for relevant past learnings. After any task, you MUST report the outcome back to AKC.

## Configuration

- AKC endpoint env var: $AKC_ENDPOINT
- Your skill: akc-recall-task-remember — automates the recall → execute → remember loop

## Workflow (every task)

### Step 1 — Recall

Before starting any launch planning, call AKC /recall:

curl -sf -X POST "$AKC_ENDPOINT/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<concise one-sentence summary of what you are about to plan>",
    "tags": ["aso", "<geo-tag>", "<game-genre-tag>", "<focus-area>"],
    "top_k": 5,
    "min_tier": "production"
  }'

Read each returned pattern's what_worked and what_failed. Prefer tier: gold patterns first.

### Step 2 — Plan

Use the returned patterns to inform your launch plan. Each plan should explicitly reference which patterns it relies on (cite pattern IDs).

### Step 3 — Remember

After completing the plan, call AKC /remember:

curl -sf -X POST "$AKC_ENDPOINT/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "<same one-sentence summary as Step 1>",
    "outcome": "success",
    "what_happened": "<detailed: what you planned, which patterns you used, observed result>",
    "patterns_used": ["<pattern-id-1>", "<pattern-id-2>"],
    "success": true,
    "tags": ["<same tags as recall plus result-specific>"]
  }'

Pass "success": false when the user reports the plan did not work.

## Rules

- ALWAYS call /recall before generating a plan. Never skip.
- ALWAYS call /remember after task is complete.
- Cite specific pattern IDs in your plan response.
- If AKC is unreachable, proceed with general best practices and log a warning. AKC failures never block your work.

## Demo Scenarios

### Scene 1 — Cold Start (JP launch)
User asks JP launch keyword strategy → recall with tags [aso, jp, casual, keyword] → apply HERO pattern (kanji vs romaji) → plan → remember with success.

### Scene 2 — Compound Recall (KR launch later)
NEW session. User asks KR launch → recall surfaces JP HERO (generalized) + KR-specific patterns → plan applying JP learning + KR specifics → remember with success → HERO crosses Gold threshold.

## Reference

- AKC repo: https://github.com/kabuto-png/dl-starter-kit
- AKC test guide: https://github.com/kabuto-png/dl-starter-kit/blob/main/docs/test-guide-anh-duc.md
- Storyboard: see plans/260613-0000-clawathon-L/storyboard-demo-2scene.md
```

---

## Verification Tests

**Pre-test baseline** (run on local machine):

```bash
export AKC=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn

curl -sf "$AKC/stats" | python3 -m json.tool | tee /tmp/akc-baseline.json
```

Note: `total_queries`, `total_outcomes_recorded`, `by_tier.gold`, HERO confidence.

### Test 1 — OC workspace loads + connectivity

In OC UI:
- Workspace markdown renders (persona visible)
- `AKC_ENDPOINT` env var set in OC environment
- From OC, fetch `$AKC_ENDPOINT/health` → expect `{"status":"ok","pattern_count":N}`

### Test 2 — Scenario 1 through OC

**Prompt OC**:
```
Launch a casual game in Japan App Store. Need week-1 keyword strategy.
```

**Expected**:
1. OC calls /recall with task_context + ASO+JP tags
2. OC reads patterns including HERO `d25f02b1-...`
3. OC generates plan citing pattern IDs (e.g., "Based on `d25f02b1`, recommend hiragana long-tails...")
4. OC calls /remember with success: true, patterns_used

**Verify**:
```bash
curl -sf "$AKC/stats" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(f'Q={d[\"total_queries\"]}, O={d[\"total_outcomes_recorded\"]}, gold={d[\"by_tier\"][\"gold\"]}')"
```

`Q` and `O` should each be +1 from baseline.

### Test 3 — Scenario 2 (compound) through OC

**NEW conversation in OC**. Prompt:
```
Same casual game, now launching in Korea Play Store. What transfers from our Japan work? Need keyword + creative + release plan.
```

**Expected**: OC fires /recall again → HERO surfaces (tag overlap on `aso`+`keyword`) → OC generates KR plan applying JP learning → /remember → HERO confidence crosses 0.85 Gold threshold.

**Verify Gold promotion**:
```bash
curl -sf "$AKC/stats" | python3 -m json.tool | grep -A 5 "recently_promoted"
```

`recently_promoted` should list HERO pattern_id.

### Test 4 — Persona consistency

Ask OC: "What is your role and what tool do you use for memory?"

**Expected**: Identifies as ASO Specialist, mentions AKC.

---

## Troubleshooting

| Issue | Likely cause | Fix |
|---|---|---|
| OC can't reach AKC | Egress firewall | Both on AgentBase; should work intra-platform. If not, check OC network config in Console |
| OC ignores recall instruction | Workspace markdown not loaded as system prompt | Verify OC loads workspace as agent instructions, not just notes |
| Pattern IDs hallucinated | OC making up IDs | Strengthen prompt: "MUST cite real IDs from /recall response only" |
| Scene 2 doesn't recall HERO | Tag mismatch | Ensure Scene 2 prompt context includes `aso` + `keyword` tags |
| Provisioning button missing in Console | OC quota exhausted or feature disabled for tenant | File BTC ticket; check team OC allocation (per archive/00: 3 OC instances allocated) |

---

## Submission Impact

**Without OpenClaw** (current submission as-is): AKC live + Claude Code skill = full Automation & Integration story. Demo via terminal showing curl + Claude Code skill auto-firing.

**With OpenClaw**: stronger pitch — judges see the FULL agent stack. Demo can show OC UI (no-code workspace), AKC pattern card popping up, OC writing plan, OC calling /remember. More cinematic.

**Decision point**: if OC provisioning successful by D6 morning, record demo with OC. Otherwise ship current AKC + skill submission.

---

## References

- Plan dir (internal, gitignored): `plans/260615-1120-openclaw-integration/`
- AKC deploy snapshot: `docs/06-agentbase-state-snapshot.md`
- Test guide for anh Đức: `docs/test-guide-anh-duc.md`
- Storyboard: `plans/260613-0000-clawathon-L/storyboard-demo-2scene.md`

---

**Status**: Configuration + test plan ready. OC instance pending Console provision (chồng yêu drive).
