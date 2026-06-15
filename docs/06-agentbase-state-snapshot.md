# AgentBase State Snapshot (2026-06-14 D4)

**Purpose:** Snapshot of provisioned AgentBase resources. State file `.agentbase-state.json` is gitignored. This doc gives partner visibility into IDs/configuration for direct AgentBase queries without needing Claude Code skills.

---

## Project Metadata

| Field | Value |
|-------|-------|
| **Project name** | dl-starter-kit |
| **Agent Identity** | dl-starter-kit |
| **Track** | **Automation & Integration** |
| **Submission Deadline** | 2026-06-17 12:00 GMT+7 |
| **Repo** | https://github.com/kabuto-png/dl-starter-kit (PUBLIC) |
| **Team** | DL Starter Kit (Nhóm 1), 2 developers |
| **Status** | Backend COMPLETE, awaiting AgentBase Runtime deploy |

---

## Memory Store

| Field | Value |
|-------|-------|
| **Memory store ID** | memory-d9b9d688-9a28-446c-841a-c70b59cdc446 |
| **Strategies registered** | `default` → ltms-e8faffe3-522c-4590-815a-7abc4aaa20b8 |
| | `la-ban-ai-coach` → ltms-6e1ad541-59dd-41c3-8b94-6fdac6fdcfe2 |
| **Currently using** | `default` |
| **Pattern schema** | JSONL store local (patterns.jsonl + confidence_history.jsonl). AgentBase Memory Service used for semantic `/recall` search (fallback if unavailable). |

**Update (D4):** JSONL primary storage is stable; AgentBase Memory integration for semantic recall is optional (timeout 2s fallback to tag-based filter). Memory Service custom schema not required for MVP — patterns stored as JSONL locally.

---

## LLM Configuration

| Field | Value |
|-------|-------|
| **Model** | **google/gemma-4-31b-it** (LOCKED after A/B test D4 — 9x faster than MiniMax, valid JSON, cheaper) |
| **Base URL** | https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1 |
| **API key source** | BTC-provided AIP key (in `.env`, NEVER expose) |
| **Key in .env as** | `LLM_API_KEY` |

**Update (D4):** LLM model switched from MiniMax M2.5 to Gemma 4-31b-it after A/B test D4 evening. Gemma won decisively: 579ms vs 5365ms (9x faster), valid JSON extraction, lower token cost (115 vs 301 tokens per call). MiniMax M2.5 available as fallback. See `plans/reports/devils-advocate-260614-2237-akc-round2-deep-dive.md` § E for trust calibration and safety guardrails (patterns start experimental tier, confidence decay protects against wrong distillations).

---

## Deployment State

| Field | Value |
|-------|-------|
| **Current step** | 8 (Deploy) — **DEPLOYED D5 2026-06-15 ACTIVE** ✅ |
| **Runtime ID** | `runtime-577cd07b-33ed-46f1-b134-1149b7137681` |
| **Endpoint URL** | `https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn` |
| **Endpoint ID (DEFAULT)** | `endpoint-30123c53-b859-4599-a339-94b2cedabf7b` |
| **Image** | `vcr.vngcloud.vn/111666-dl-starter-kit/dl-starter-kit:v20260615011317` (Docker v2s2 manifest) |
| **vCR repo** | `dl-starter-kit` (backendName `111666-dl-starter-kit`) |
| **Robot account** | `dl-starter-kit-deploy` (pull+push permissions) |
| **Flavor** | runtime-s2-general-4x8 (4 vCPU / 8 GB / 1 replica) |
| **LLM** | google/gemma-4-31b-it via GreenNode MaaS |
| **Memory store** | memory-d9b9d688-9a28-446c-841a-c70b59cdc446 |
| **Identity** | dl-starter-kit (auto-injected by runtime) |
| **Status** | ACTIVE — all 5 endpoints smoke-tested working |
| **Deploy date** | D5 2026-06-15 09:30 GMT+7 |

---

## Smoke Test Results (D5 deploy verification)

All 5 endpoints verified working on the live AgentBase Runtime:

| Endpoint | Method | Verified Response |
|----------|--------|-------------------|
| `/health` | GET | `{"status":"ok","pattern_count":30}` |
| `/stats` | GET | `{by_tier:{gold:5,production:10,experimental:15,demoted:0}, top_tags:[python, aso, app-store, ...]}` |
| `/recall` | POST | Returns top-k patterns; HERO pat_aso_jp_001 at confidence 0.76 production for JP query — matches storyboard Scene 2 math |
| `/remember` | POST | 202 Accepted (background distill+store+update_confidence) |
| `/kb/export` | POST | Markdown export of Gold + Production patterns |
| `/invocations` | POST | Service directory (Runtime Contract §3 stub) |

## Deploy Lessons (5 ERROR attempts before success)

Documented to inform future deploys. Summary:

1. **v1 ERROR**: lifespan blocked on Memory Service sync (30 patterns × retry). FIX: `asyncio.create_task(_seed_memory_service())` non-blocking.
2. **v2/v3 ERROR**: logger.basicConfig AFTER pydantic-settings import. ValidationError on missing env var was emitted to uncaptured stderr — zero logs reached AgentBase. FIX: reorder so logging configured first, wrap settings load in try/except logger.exception, redirect to stdout.
3. **v4 ERROR**: missing POST /invocations endpoint per AgentBase Runtime Service Contract §3. FIX: added stub returning service directory.
4. **v5 ERROR**: (a) CORS `allow_methods=["GET","POST"]` rejected probe OPTIONS preflight and X-GreenNode-AgentBase-* headers, (b) /health threw 500 on transient stats read failure, (c) Podman OCI manifest possibly rejected by kubelet. FIX: CORS allow_*=["*"], /health try/except always 200, image repushed `--format v2s2`.
5. **6th attempt SUCCESS**: deleted corrupted runtime (stuck in UPDATING/ERROR cycles), created fresh runtime with v5 image. Took ~90s to ACTIVE.

---

## How to Verify State Without Skills

Use greennode-agentbase SDK (already in `requirements.txt`):

### 1. Verify Memory store connectivity

```python
from greennode_agentbase import MemoryClient

client = MemoryClient(
    memory_store_id="memory-d9b9d688-9a28-446c-841a-c70b59cdc446",
    api_key="<from .env LLM_API_KEY>"
)

# List registered strategies
strategies = client.list_strategies()
print(f"Registered: {[s.name for s in strategies]}")
```

Expected: `['default', 'la-ban-ai-coach']` returned.

### 2. Test LLM connectivity

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="minimax/minimax-m2.5",
    api_key="<from .env>",
    base_url="https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"
)

response = llm.invoke("Hello, test completion")
print(response.content)
```

Expected: Non-empty response from MaaS endpoint.

### 3. Skip (cannot verify without admin API)
- Agent Identity state (requires AgentBase admin access)
- Runtime health (requires deployed endpoint)

---

## What's NOT in this snapshot

- Auth tokens (stored in `.env` / BTC-controlled)
- API key values (NEVER in git or shared docs)
- vCR credentials (internal VNG system)
- Runtime endpoint URL (not deployed yet)
- Session state (ephemeral)

---

## For Partner with AgentBase Skills

Partner (anh Đức) can use unclaude-code skills for deeper inspection:

| Skill | What it reveals |
|-------|-----------------|
| `/agentbase` | Platform overview, all resources summary |
| `/agentbase-monitor` | Real-time resource state (runtime health, memory queries, LLM latency) |
| `/agentbase-memory` | Memory store internals, strategy behavior, search logs |
| `/agentbase-llm` | Available models, quota usage, latency profile |
| `/agentbase-deploy` | Build status, vCR push, runtime creation (READY — vCR access cleared D4) |
| `/agentbase-identity` | Agent identity SSO config, permission scope |

See [`docs/07-partner-claude-setup.md`](07-partner-claude-setup.md) for install + first-run commands.

---

## Next Steps

1. ✅ **D5 DONE:** Docker build + push vCR + Runtime creation — ACTIVE at `runtime-577cd07b-33ed-46f1-b134-1149b7137681`
2. ✅ **D5 DONE:** Smoke test deployed endpoint — all 5 endpoints verified, 30 seeded patterns loaded
3. **D6 (2026-06-16):** Record demo video 2-3 min + polish 200-word use case description
4. **D7 (before 12:00 GMT+7):** Final submission

---

**Updated:** 2026-06-15 09:30 GMT+7 | **Status:** DEPLOYED (D5 checkpoint) — ACTIVE for D6-D7
