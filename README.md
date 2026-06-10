# dl-starter-kit

GreenNode AgentBase agent — Team DL Starter Kit (Claw-a-thon 2026, Nhóm 1).

LangChain + Memory agent: short-term conversation persistence via `AgentBaseMemoryEvents` checkpointer + long-term semantic memory via `remember`/`recall` tools.

## Prerequisites

- Python 3.10+
- GreenNode IAM Service Account (already configured in `.greennode.json`)

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, MEMORY_ID
```

## Configure LLM

Use `/agentbase-llm` to create an API key + browse models.

```
LLM_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
LLM_API_KEY=<from /agentbase-llm api-keys create>
LLM_MODEL=<chosen ENABLED model>
```

## Run Locally

```bash
python3 main.py
# http://127.0.0.1:8080
curl -X POST http://127.0.0.1:8080/invocations \
  -H "Content-Type: application/json" \
  -H "X-GreenNode-AgentBase-User-Id: test-user" \
  -H "X-GreenNode-AgentBase-Session-Id: test-session-1" \
  -d '{"message": "Hello, agent!"}'
```

## Deploy

Use `/agentbase-deploy` for build + push vCR + create runtime.

## Project Structure

- `main.py` — LangChain agent with memory tools
- `Dockerfile` — Python 3.13-slim base
- `requirements.txt` — LangChain + AgentBase SDK
- `.env.example` — env template
- `.greennode.json` — IAM credentials (gitignored)
