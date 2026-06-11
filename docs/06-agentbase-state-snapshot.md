# AgentBase State Snapshot (2026-06-11)

**Purpose:** Snapshot of provisioned AgentBase resources. State file `.agentbase-state.json` is gitignored. This doc gives partner visibility into IDs/configuration for direct AgentBase queries without needing Claude Code skills.

---

## Project Metadata

| Field | Value |
|-------|-------|
| **Project name** | dl-starter-kit |
| **Agent Identity** | dl-starter-kit |
| **Track** | General / Self-Evolving Agent |
| **Deadline** | 2026-06-17 12:00 GMT+7 |
| **Repo** | https://github.com/kabuto-png/dl-starter-kit (PUBLIC) |
| **Team** | DL Starter Kit (Nhóm 1), 2 developers |

---

## Memory Store

| Field | Value |
|-------|-------|
| **Memory store ID** | memory-d9b9d688-9a28-446c-841a-c70b59cdc446 |
| **Strategies registered** | `default` → ltms-e8faffe3-522c-4590-815a-7abc4aaa20b8 |
| | `la-ban-ai-coach` → ltms-6e1ad541-59dd-41c3-8b94-6fdac6fdcfe2 |
| **Currently using** | `la-ban-ai-coach` (legacy from prior direction) |
| **Per PRD §5** | May need new `akc-patterns` CUSTOM strategy with Pattern schema (confidence tier enum, tags array, times_applied/times_succeeded counters) |

**Action:** Verify Memory Service supports custom schemas for Pattern struct. Current strategies fit La Bàn AI coach role extraction; AKC requires richer typed storage.

---

## LLM Configuration

| Field | Value |
|-------|-------|
| **Model** | minimax/minimax-m2.5 |
| **Base URL** | https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1 |
| **API key source** | BTC-provided AIP key (in `.env`, NEVER expose) |
| **Key in .env as** | `LLM_API_KEY` |
| **DISCREPANCY FLAG** | PRD §10 specifies Qwen3; current config is minimax. Team decision needed before Phase 2 (Jun 12). Impact: distillation prompt tuning, confidence calibration. |

**Workaround:** Minimax-m2.5 can be used for MVP if structured extraction works in testing (Phase 2 testing will reveal). If results poor, escalate to BTC for Qwen3 quota.

---

## Wizard State

| Field | Value |
|-------|-------|
| **Current step** | 8 (Deploy) — PAUSED |
| **Blocker** | vCR 403 Forbidden — requires `vcrFullAccess` permission from BTC |
| **Escalation** | Contact helpdesk@vng.com.vn with project name + request vcrFullAccess |
| **Next action** | Unblock vCR → `/agentbase-deploy` → customize code/coach pipeline (Phase 3) |
| **Deploy preferences** | flavor=runtime-s2-general-4x8, platform=linux/amd64, replicas=1 |
| **Local test status** | PASSED |
| **Runtime ID** | Not yet deployed |

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
| `/agentbase-deploy` | Build status, vCR push, runtime creation (BLOCKED on vCR 403) |
| `/agentbase-identity` | Agent identity SSO config, permission scope |

See [`docs/07-partner-claude-setup.md`](07-partner-claude-setup.md) for install + first-run commands.

---

## Next Steps

1. **Jun 12 (Phase 2):** Test distillation with current LLM model; if results poor, escalate model to Qwen3
2. **Jun 12 (Phase 2):** Verify Memory Service custom schema support for Pattern struct
3. **Before Jun 14 (Phase 4):** Unblock vCR 403 (BTC escalation)
4. **Jun 14 (Phase 4):** Deploy to AgentBase, get live runtime endpoint
5. **Jun 15 (Phase 5):** Monitor /stats, /health, query latency via `/agentbase-monitor`

---

**Taken:** 2026-06-11 12:00 GMT+7 | **Status:** CURRENT
