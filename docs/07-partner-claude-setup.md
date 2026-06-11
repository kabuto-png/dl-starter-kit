# Partner Claude Setup Guide

**Audience:** anh Đức + any developer joining the project with Claude Code.

---

## Why This Doc

Repo intentionally excludes `.claude/` tooling (skills, rules, commands) — they're local to each developer's environment, not shared in git. Partner needs separate setup to match skill/workflow parity with lead.

Two paths below: lightweight (docs-only) vs full tooling (skills installed).

---

## Path A: Lightweight (Docs + greennode SDK only)

**Use this if:** You prefer to work without Claude Code skills, or need fast onboarding.

**What you do:**
1. Read [`docs/prd/AKC_PRD.md`](prd/AKC_PRD.md) — authoritative PRD, API contracts, build plan
2. Read [`docs/architecture_v1.md`](architecture_v1.md) — feature-first FastAPI code structure
3. Read [`docs/06-agentbase-state-snapshot.md`](06-agentbase-state-snapshot.md) — memory/LLM/wizard state
3. Clone repo, set up `.env`, run `python3 main.py` locally
4. Use greennode-agentbase SDK directly (already in `requirements.txt`):

```python
from greennode_agentbase import MemoryClient

# Query memory store
client = MemoryClient(
    memory_store_id="memory-d9b9d688-9a28-446c-841a-c70b59cdc446",
    api_key="<from .env LLM_API_KEY>"
)
strategies = client.list_strategies()
```

**Pros:** No extra tooling, direct SDK control, minimal setup.  
**Cons:** Manual inspection of state; no slash commands for quick checks.

---

## Path B: Full Tooling (unclaude-code skills)

**Use this if:** You want skill-driven workflow, `/agentbase-*` commands for inspection, aligned with lead's setup.

### Step 1: Clone unclaude-code

```bash
cd ~
git clone https://github.com/kabuto-png/unclaude-code.git
cd unclaude-code
```

### Step 2: Activate skills in Claude Code

Follow unclaude-code's README for install:
- Copy `.claude/skills/` into your `~/.claude/skills/` (create if missing)
- Copy `.claude/rules/` into your `~/.claude/rules/`
- Copy `.claude/commands/` into your `~/.claude/commands/`

On macOS/Linux:
```bash
mkdir -p ~/.claude
cp -r unclaude-code/.claude/skills/* ~/.claude/skills/
cp -r unclaude-code/.claude/rules/* ~/.claude/rules/
cp -r unclaude-code/.claude/commands/* ~/.claude/commands/
```

### Step 3: Verify

Open Claude Code, type:
```
/uc-help
```

Expected: Displays usage guide for unclaude-code workflows.

---

## Recommended First Commands (Path B)

After installing skills:

### 1. Platform overview
```
/agentbase
```
Shows: all provisioned resources, quotas, project state.

### 2. Real-time monitoring
```
/agentbase-monitor
```
Shows: runtime health, memory queries/latency, LLM usage.

### 3. Memory store inspection
```
/agentbase-memory
```
Shows: strategies list, record counts, custom schema state.

Input Memory ID from [`docs/06-agentbase-state-snapshot.md`](06-agentbase-state-snapshot.md):
```
memory-d9b9d688-9a28-446c-841a-c70b59cdc446
```

---

## Shared State (Both Paths)

Both developer + lead work with **SAME resources:**

| Resource | Shared? | Details |
|----------|---------|---------|
| **AgentBase tenant** | YES | Both call same Memory ID, same Identity |
| **LLM API key** | YES | BTC-provided AIP key in `.env` (shared in private channel) |
| **Memory store** | YES | Patterns, confidence scores stored/retrieved from same place |
| **Claude Code instance** | NO | Skills, plans, working space are LOCAL (not synced) |

**Guard rails:**
- Do NOT run `/agentbase-teardown` without explicit lead approval (destroys all resources)
- Do NOT `/agentbase-deploy` until vCR 403 unblocked (lead will confirm)
- Do NOT push secrets to public repo (API key, credentials in `.env` only, gitignored)

---

## Quick Sanity Check (Both Paths)

Run this after setup to verify connectivity:

```python
import os
from dotenv import load_dotenv
from greennode_agentbase import MemoryClient
from langchain_openai import ChatOpenAI

load_dotenv()

# 1. Memory store test
print("1. Testing Memory store...")
memory_client = MemoryClient(
    memory_store_id="memory-d9b9d688-9a28-446c-841a-c70b59cdc446",
    api_key=os.getenv("LLM_API_KEY")
)
strategies = memory_client.list_strategies()
print(f"   Strategies: {[s.name for s in strategies]}")

# 2. LLM connectivity test
print("2. Testing LLM...")
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL")
)
response = llm.invoke("Say 'connected'")
print(f"   Response: {response.content}")

print("\nSetup verified!")
```

Run:
```bash
python3 sanity_check.py
```

Expected: Both tests print success (strategy names, LLM response).

---

## Next Steps

1. **Path A only:** Read PRD + snapshot docs, start work
2. **Path B:** After skills installed, run `/agentbase-monitor` to see current state
3. **Both:** Sync with lead on current phase (check [`docs/prd/AKC_PRD.md`](prd/AKC_PRD.md) §11 build plan)
4. **Implementation:** Follow PRD roadmap; update `.env` as needed; keep `.agentbase-state.json` local (gitignored)

---

**Document version:** 2026-06-11 | **Audience:** Partner onboarding
