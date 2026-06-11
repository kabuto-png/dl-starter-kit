# Environment & Deployment Guide

**La Bàn AI Coaching Agent** — Setup, configuration, and deployment to AgentBase.

---

## Stack Overview

| Component | Version | Purpose |
|-----------|---------|---------|
| **Language** | Python 3.9+ | Runtime |
| **Framework** | LangChain 1.2–1.3.6 | Agent orchestration & tool binding |
| **LLM Orchestration** | LangGraph 1.0+ | Deterministic agent pipeline |
| **SDK** | greennode-agentbase | GreenNode AgentBase integration |
| **API Runtime** | FastAPI (via GreenNodeAgentBaseApp) | HTTP server & request routing |
| **Deployment** | Docker 20.10+ | Container orchestration |
| **Deployment Target** | GreenNode AgentBase Runtime | Production environment |

---

## Required Environment Variables

Configure these variables in `.env` before running locally or deploying:

| Variable | Required? | Source | Example | Purpose |
|----------|-----------|--------|---------|---------|
| `MEMORY_ID` | **YES** | AgentBase provisioning | `mem_xyz...` | Memory store identifier |
| `MEMORY_STRATEGY_ID` | NO (default: `la-ban-ai-coach`) | Custom name | `la-ban-ai-coach` | Namespace for user memory records |
| `LLM_MODEL` | **YES** | GreenNode MaaS | `gemma-4-31b-it` | AI model to invoke |
| `LLM_BASE_URL` | **YES** | GreenNode MaaS | `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | **YES** | Platform API key | `<your-key>` | Authentication for LLM calls |
| `GREENNODE_CLIENT_ID` | NO | AgentBase auth | `client_...` | Optional: explicit AgentBase credentials |
| `GREENNODE_CLIENT_SECRET` | NO | AgentBase auth | `secret_...` | Optional: explicit AgentBase credentials |
| `GREENNODE_AGENT_IDENTITY` | NO | AgentBase config | `la-ban-ai` | Optional: agent identity name |

### Get API Keys

- **LLM_API_KEY**: Use the `/agentbase-llm` skill in Claude Code to obtain platform API key
- **MEMORY_ID**: Automatically provisioned when agent is created in AgentBase
- **GREENNODE_* credentials**: Auto-injected at runtime; only needed for local testing with explicit auth

### .env Template

```env
# GreenNode MaaS — LLM configuration
LLM_MODEL=gemma-4-31b-it
LLM_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
LLM_API_KEY=<your-api-key>

# AgentBase memory
MEMORY_ID=<provisioned-by-agentbase>
MEMORY_STRATEGY_ID=la-ban-ai-coach

# Optional: AgentBase credentials
GREENNODE_CLIENT_ID=
GREENNODE_CLIENT_SECRET=
GREENNODE_AGENT_IDENTITY=
```

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone <project-repo>
cd dl_starter_kit
```

### 2. Create Virtual Environment

```bash
python3.9 -m venv venv
source venv/bin/activate  # macOS / Linux
# or: venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `greennode-agentbase` — SDK for AgentBase integration
- `langchain` — LLM agent framework
- `langgraph` — Deterministic pipeline control
- `langchain-openai` — OpenAI-compatible LLM client
- `python-dotenv` — Environment variable loading

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with:
- `LLM_API_KEY` — from `/agentbase-llm`
- `LLM_MODEL` — choose from available GreenNode MaaS models
- `MEMORY_ID` — from AgentBase provisioning
- Other optional fields

### 5. Run Locally

```bash
python main.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

Agent is ready to receive requests at `http://localhost:8080/invocations`.

---

## Entry Point Contract

All requests to `/invocations` require:

### Request Headers (Required)

```
X-GreenNode-AgentBase-User-Id: <user-id>
X-GreenNode-AgentBase-Session-Id: <session-id>
```

If missing, agent returns HTTP 200 with error status:
```json
{
  "status": "error",
  "error": "Missing required headers: X-GreenNode-AgentBase-User-Id and X-GreenNode-AgentBase-Session-Id are required when using memory."
}
```

### Request Body

```json
{
  "message": "What did I tell you about my learning goals last week?"
}
```

### Response

```json
{
  "status": "success",
  "response": "You mentioned wanting to improve your system design skills...",
  "timestamp": "2026-06-11T14:45:30.123456"
}
```

### Health Check

```bash
curl http://localhost:8080/health
```

Returns HTTP 200:
```json
{
  "status": "ok"
}
```

---

## AgentBase Memory Pattern

Memory is isolated by strategy + actor (user):

```
/strategies/{MEMORY_STRATEGY_ID}/actors/{actor_id}
```

**Example:** `/strategies/la-ban-ai-coach/actors/user_123`

### How It Works

1. **remember(fact)** tool — inserts a fact into the actor's namespace
   ```python
   remember("User wants to master system design in 3 months")
   ```
   Internally: `MemoryClient.insert_memory_records_directly()`

2. **recall(query)** tool — searches for relevant memories
   ```python
   recall("What are my learning goals?")
   ```
   Internally: `MemoryClient.search_memory_records()` with `MemoryRecordSearchRequest`
   Returns top 10 matching memories with relevance scores

3. **Actor ID mapping** — extracted from request context
   ```python
   config["configurable"]["actor_id"] = context.user_id
   ```

### Example Conversation Flow

```
User: "I want to learn Go programming"
Agent: [calls remember("User wants to learn Go programming")]
       returns: "Remembered: User wants to learn Go programming"

[Later session]
User: "What should I focus on?"
Agent: [calls recall("What are my learning goals?")]
       returns: "- User wants to learn Go programming (score: 0.95)"
       uses recalled memory in response
```

---

## Docker Build & Deployment

### Build Locally

```bash
docker build -t la-ban-ai:latest .
```

**Dockerfile strategy:**
- Base: `python:3.13-slim` (lightweight)
- Install deps to image (no runtime pip install)
- Copy source last (cache optimization)
- Expose port 8080
- Run: `python main.py`

### Run in Docker Locally

```bash
docker run \
  --env-file .env \
  -p 8080:8080 \
  la-ban-ai:latest
```

Test with:
```bash
curl -H "X-GreenNode-AgentBase-User-Id: test-user" \
     -H "X-GreenNode-AgentBase-Session-Id: test-session" \
     -X POST http://localhost:8080/invocations \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello"}'
```

### Deploy to AgentBase

**Prerequisites:**
- Docker image built and pushed to GreenNode Container Registry
- `.env` variables configured in AgentBase runtime
- Health check endpoint `/health` exposed

**Use the `/agentbase-deploy` skill:**

```
/agentbase-deploy
```

This orchestrates:
1. Build Docker image
2. Push to GreenNode Container Registry
3. Create/update AgentBase runtime
4. Configure environment variables
5. Expose public endpoint
6. Enable monitoring & logging

**Result:** Agent accessible at stable URL (e.g., `https://agent-la-ban-ai.agentbase.vng.cloud/invocations`)

---

## Sample Agent Reference Patterns

This project follows **Pattern B (Custom Agent)** — intentional choice over Pattern A.

| Aspect | Pattern A: OpenClaw 1-Click | Pattern B: Custom Agent (Our Choice) |
|--------|---------------------------|--------------------------------------|
| **Dev Model** | Markdown-driven (no-code) | Python/FastAPI + Docker |
| **Config Location** | Workspace files (IDENTITY.md, SOUL.md, etc.) | `.env` + `main.py` |
| **Sample Agent** | PM Assistant — market research, roadmap, insights | Interview Assistant — transcribe, assess, report |
| **Capabilities** | Web search, document analysis, scheduled tasks | Deterministic 6-step pipeline + real-time transcription |
| **Deployment** | 1-click from Marketplace; no infrastructure | Docker → AgentBase Runtime → stable endpoint |
| **Customization** | Edit markdown files + reload | Full Python control + CI/CD |
| **Best For** | PM/analyst workflows, rapid iteration | Deterministic processes, strong guarantees |
| **Technical Barrier** | None — PM-friendly | Python + FastAPI knowledge |
| **Dev Time to Production** | ~2 hours | ~5–7 hours |
| **Docs Reference** | https://docs.vngcloud.vn/vng-cloud-document/ai-stack/agent-base/agent-runtime/openclaw/openclaw-1-click | https://github.com/vngcloud/clawathon-2026-sample-agents/tree/main/interview-assistant |

### Why Pattern B for La Bàn AI

**Deterministic gating required.** The 6-step coaching pipeline must execute in strict order with gates:
1. Parse user input
2. Search long-term memory (recall)
3. Classify coaching need
4. Generate personalized advice (LLM)
5. Store new insights (remember)
6. Return response

This sequence cannot be cleanly expressed in markdown-only config (Pattern A). FastAPI endpoints + LangGraph checkpointing provide explicit control.

### Trade-off

**Pattern A** = faster to ship, easier to iterate on prompts.
**Pattern B** = full control over logic flow, can integrate real-time transcription, can export structured reports.

For La Bàn AI's deterministic requirements, Pattern B is the right fit.

---

## Submission Deliverable Checklist

Before final delivery, ensure:

### Code Gates

- [ ] `main.py` exposes `/invocations` (entrypoint) + `/health` (PUBLIC mode, no auth required for health check)
- [ ] All required env vars documented in `.env.example`
- [ ] `requirements.txt` pinned to exact versions
- [ ] `Dockerfile` builds without errors, runs on port 8080
- [ ] Health check passes: `curl http://localhost:8080/health`

### Testing

- [ ] `tests/` folder exists with at least one smoke test
  - Example: `test_smoke_memory_integration.py` — verifies remember/recall cycle
  - Run: `pytest tests/` returns 100% pass
- [ ] No `skip()` markers in tests; all tests must pass

### Performance Validation

- [ ] `benchmarks/` folder with `p95_latency.md`
  - Document: endpoint latency under load, memory search time, LLM generation time
  - Example: "99th percentile latency: 2.3s for recall + LLM inference"

### Documentation

- [ ] `README.md` updated with:
  - Problem statement
  - How to run locally (copy from § Local Development Setup)
  - How to deploy (copy from § Deploy to AgentBase)
- [ ] `docs/` folder contains:
  - `01-product-requirements.md` — detailed PRD + acceptance criteria
  - `02-architecture.md` — system design + data flow diagrams
  - `03-environment-and-deployment.md` — this file

### Templates

- [ ] `templates/` folder with 5 department reference files:
  - `bi.md` — example coaching scenario for Business Intelligence team
  - `ua.md` — User Acquisition team example
  - `dev.md` — Engineering team example
  - `hr.md` — Human Resources team example
  - `designer.md` — Design team example

### Demo & Visibility

- [ ] Demo video link in `README.md`
  - Shows: upload CV/JD, generate questions, run interview, export report
  - Duration: 2–3 minutes
- [ ] Link to deployed agent endpoint (from `/agentbase-deploy`)

---

## Quick Reference

### Entry Point

```python
@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    # context.user_id, context.session_id extracted from headers
    # payload["message"] contains user input
    # Returns: {"status": "success"|"error", "response": str, "timestamp": str}
```

### Memory Tools

```python
# Store a fact
remember("User wants to learn Go in Q3")

# Search memories
results = recall("What are my Q3 learning goals?")
# Returns: ["- User wants to learn Go in Q3 (score: 0.98)"]
```

### Environment

```bash
# Run locally
python main.py

# Run in Docker
docker run --env-file .env -p 8080:8080 la-ban-ai:latest

# Deploy to AgentBase
/agentbase-deploy
```

### Health / Status

```bash
# Local
curl http://localhost:8080/health

# Deployed
curl https://agent-la-ban-ai.agentbase.vng.cloud/health
```

---

## External References

**Sample Agent Repository:**
https://github.com/vngcloud/clawathon-2026-sample-agents

Contains:
- **GreenNode PM Assistant** — Pattern A (no-code, markdown-driven)
- **Interview Assistant** — Pattern B (Python/FastAPI, deterministic pipeline)

Clone this repo for offline reference:
```bash
git clone https://github.com/vngcloud/clawathon-2026-sample-agents
```

Use `interview-assistant/` as architectural reference when implementing features requiring:
- Real-time processing (WebSocket)
- Structured output (Excel generation)
- Multi-step pipelines (transcribe → assess → report)

---

## Troubleshooting

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| `MEMORY_ID required` | `.env` missing `MEMORY_ID` | Use `/agentbase-llm` to provision memory |
| `LLM_API_KEY invalid` | Token expired or wrong endpoint | Refresh via `/agentbase-llm` |
| Health check 500 | Missing required headers | Add `X-GreenNode-AgentBase-User-Id` + `X-GreenNode-AgentBase-Session-Id` to request |
| Memory search returns nothing | Namespace mismatch | Verify `MEMORY_STRATEGY_ID` matches actor scoping |
| Docker build fails | Base image pull error | `docker pull python:3.13-slim` first |
| Port 8080 already in use | Local port conflict | `lsof -i :8080` and kill, or use `--port` flag |

---

**Last updated:** 2026-06-11  
**Next review:** After first deployment to AgentBase
