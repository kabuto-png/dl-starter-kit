# Technology Stack

**Project:** AKC — Agent Knowledge Collective
**Researched:** 2026-06-11
**Scope:** FastAPI + Pydantic v2 + structured LLM output, JSONL storage, Docker packaging

---

## Verified Current Versions (as of 2026-06-11)

Versions confirmed via live PyPI index on this machine. Pin these in requirements.txt.

| Package | Latest | Pin to |
|---------|--------|--------|
| fastapi | 0.136.3 | `>=0.130.0` |
| uvicorn[standard] | 0.49.0 | `>=0.30.0` |
| pydantic | 2.13.4 | `>=2.7.0` |
| pydantic-settings | 2.14.1 | `>=2.7.0` |
| openai | 2.41.1 | `>=2.0.0` |
| portalocker | 3.2.0 | `>=3.0.0` |
| httpx | (pulled by fastapi[standard]) | (transitive) |

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | `>=0.130.0` | HTTP framework, request validation, OpenAPI docs | Native Pydantic v2 integration since 0.100.0; dropped Pydantic v1 support at 0.130.0; async-native; `lifespan` pattern is current standard |
| uvicorn[standard] | `>=0.30.0` | ASGI server | Ships with `uvloop` + `httptools` via `[standard]` extra; significantly faster than plain uvicorn |
| Python | 3.11 | Runtime | Faster than 3.10; type hints mature; matches platform requirement and existing scaffold |

### Config Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pydantic-settings | `>=2.7.0` | `BaseSettings` + env + `.env` file loading | Validated at startup — bad env vars crash immediately with clear errors instead of failing silently at first call. Reference codebase uses raw `os.environ` — this is the upgrade. |

**Pattern to use:**

```python
# akc/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    llm_model: str
    llm_base_url: str
    llm_api_key: str
    memory_id: str
    akc_kb_dir: str = "./kb"
    akc_kb_export_dir: str = "./kb_export"

# Module-level singleton — import this everywhere
settings = Settings()
```

Do NOT use raw `os.environ.get()` scattered across modules. Do NOT use `python-dotenv` directly — pydantic-settings already handles `.env` loading.

### LLM Client (Distillation)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openai | `>=2.0.0` | OpenAI-compatible API client for Qwen distillation | GreenNode MaaS exposes OpenAI-compatible endpoint; openai SDK v2 is the current stable series (v1.x is legacy, the 2.x series started shipping ~Jan 2026) |

**IMPORTANT — openai v2 vs v1:**

The machine has openai 2.41.1 available. The `1.x` series is legacy. Use v2.

**Structured output pattern for Qwen via custom base_url:**

Qwen supports OpenAI-compatible `chat/completions` endpoint. Use `response_format={"type": "json_object"}` with a schema prompt, NOT `client.chat.completions.parse()` with a Pydantic model directly.

Reason: `chat.completions.parse()` with Pydantic relies on OpenAI's strict JSON Schema mode (`strict: true`), which requires the upstream model to support it. Qwen/GreenNode compatibility with strict structured output mode is unverified. The safe fallback — and what the reference codebase pattern implies — is:

1. Prompt the model to return JSON matching a specific schema
2. Receive the completion as a string
3. Parse with `Pattern.model_validate_json(response.choices[0].message.content)`

```python
# akc/remember/distiller.py
from openai import OpenAI
from akc.patterns.models import DistilledPattern
from akc.core.config import settings

_client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

async def extract(task_context: str, what_happened: str, outcome: str) -> DistilledPattern:
    system_prompt = """Extract a structured pattern from the outcome description.
    Return valid JSON matching exactly this schema:
    {"context": str, "what_worked": str, "what_failed": str, "tags": [str]}"""

    response = _client.chat.completions.create(
        model=settings.llm_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task_context}\nOutcome: {outcome}\nWhat happened: {what_happened}"},
        ],
        temperature=0.2,
    )
    raw_json = response.choices[0].message.content
    return DistilledPattern.model_validate_json(raw_json)
```

**What NOT to use:**
- `langchain_openai.ChatOpenAI` — adds ~15 deps, abstraction overhead not needed for a single structured call. The reference codebase does not use LangChain for distillation; don't introduce it.
- `openai` `1.x` series — the 2.x API is current; `1.x` version pin would cap at `<2.0.0` and miss current stability.
- `client.chat.completions.parse()` with Pydantic class as `response_format` — requires strict structured output support from the model provider; unverified for GreenNode Qwen endpoint. Only use this if GreenNode confirms `json_schema` response format support.

**Confidence:** MEDIUM — The json_object approach is universally supported; Qwen OpenAI-compatible endpoints confirm chat completions support. The Pydantic `.parse()` shortcut has model-side requirements that need provider verification.

### JSONL Storage + File Locking

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| portalocker | `>=3.0.0` | Cross-platform file locking for concurrent JSONL appends | Wraps `fcntl.flock()` on Linux and `msvcrt` on Windows with context manager API; v3.x is current stable. The architecture spec explicitly requires concurrent write protection on JSONL files. |

**Why not raw `fcntl`:** `fcntl` is Linux-only. `portalocker` is identical in behavior on Linux but won't break if someone runs tests on macOS/Windows. For a hackathon this is minor, but portalocker costs nothing extra and is cleaner.

**Append pattern:**

```python
# akc/patterns/store.py
import json
import portalocker
from pathlib import Path

def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        try:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
        finally:
            portalocker.unlock(f)
```

**What NOT to use:**
- Plain `open("a") + write()` without locking — concurrent `/remember` calls from the same agent can interleave writes and corrupt JSONL lines.
- `filelock` — uses a separate `.lock` file rather than locking the target file directly; fine for lock-then-write patterns but portalocker on the actual file is simpler for append-only JSONL.

### FastAPI Structural Patterns

**App factory + lifespan:**

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from akc.recall.router import router as recall_router
from akc.remember.router import router as remember_router
from akc.stats.router import router as stats_router
from akc.export.router import router as export_router
from akc.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: validate KB dir exists, warn if LLM unreachable
    yield
    # shutdown: flush any pending state if needed

def create_app() -> FastAPI:
    app = FastAPI(title="AKC", version="0.1.0", lifespan=lifespan)
    app.include_router(recall_router)
    app.include_router(remember_router)
    app.include_router(stats_router)
    app.include_router(export_router)
    return app

app = create_app()
```

**What NOT to use:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")` — deprecated since FastAPI 0.93.0. Use `lifespan` context manager only.
- Global mutable state outside lifespan — any store or LLM client that needs cleanup belongs in `lifespan` or `Depends()`.

**BackgroundTasks for /remember:**

```python
# akc/remember/router.py
from fastapi import APIRouter, BackgroundTasks
from akc.remember.schemas import RememberRequest

router = APIRouter(prefix="/remember", tags=["remember"])

@router.post("/", status_code=202)
async def remember(req: RememberRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_remember, req)
    return {"status": "accepted"}
```

This is the correct pattern. `BackgroundTasks` is sufficient for AKC because:
- Tasks are lightweight (one Qwen call + one JSONL write)
- Loss on worker crash is acceptable for a hackathon
- No queue infrastructure needed

Only escalate to Celery/Redis if tasks become heavy or the demo requires guaranteed delivery.

**Pydantic v2 models:**

Use `model_config = ConfigDict(...)` syntax, NOT the `class Config:` inner class (that was Pydantic v1 style and produces deprecation warnings in Pydantic v2).

```python
# akc/patterns/models.py
from pydantic import BaseModel, ConfigDict
from enum import Enum

class Tier(str, Enum):
    GOLD = "gold"
    PRODUCTION = "production"
    EXPERIMENTAL = "experimental"
    DEMOTED = "demoted"

class Pattern(BaseModel):
    model_config = ConfigDict(frozen=True)  # immutable after creation
    id: str
    context: str
    what_worked: str
    what_failed: str
    tags: list[str]
    confidence: float
    tier: Tier
    alpha: int = 1
    beta: int = 1
    consecutive_failures: int = 0
    times_applied: int = 0
    times_succeeded: int = 0
```

### Docker Packaging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python:3.11-slim | (current) | Base image | Minimal footprint (~45 MB vs ~900 MB full), no compilers/dev tools needed |

**Recommended Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Layer caching: install deps before copying app code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY akc/ ./akc/
COPY main.py .

# Non-root user (security best practice)
RUN useradd -r -u 1001 appuser && \
    mkdir -p /app/kb /app/kb_export && \
    chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**What NOT to do:**
- Do NOT use multi-stage builds here — no compilation step, nothing to separate. Single stage is simpler for a hackathon.
- Do NOT use `python:3.11` (full image) — adds ~850 MB for nothing.
- Do NOT run as root (default) — creates security issue if container is breached.
- Do NOT copy entire repo into container — use `.dockerignore` to exclude `kb/`, `*.jsonl`, `.env`, `.git`, `__pycache__`, tests.
- Do NOT set `PYTHONPATH` hacks — use a flat structure with `main.py` at root so imports resolve naturally.

**Required .dockerignore:**
```
.git/
.env
kb/
kb_export/
__pycache__/
*.pyc
tests/
.planning/
docs/
```

---

## What the Reference Codebase Gets Wrong (Don't Port These)

The reference at `/home/brewuser/akc-service` is a prior Godot-specific implementation. Its config module uses raw `os.environ.get()` scattered across files — replace this wholesale with pydantic-settings. It has no file locking on JSONL writes. It has no LLM distillation (uses `requests` library without an LLM client). Port the confidence/tier logic and exporter structure; discard the config pattern and absence of locking.

---

## Full requirements.txt

```
fastapi>=0.130.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.7.0
openai>=2.0.0
portalocker>=3.0.0
httpx>=0.27.0
```

No other runtime dependencies needed. `httpx` is a transitive dependency of fastapi[standard] but worth pinning explicitly since the AgentBase Memory client will need it.

---

## Alternatives Considered and Rejected

| Category | Recommended | Rejected | Reason |
|----------|-------------|----------|--------|
| LLM client | `openai` SDK v2 | `langchain_openai` | +15 transitive deps, abstraction not needed for a single structured call |
| LLM client | `openai` SDK v2 | `httpx` raw calls | SDK handles retry, error types, type hints — not worth reinventing |
| File locking | `portalocker` | `fcntl` direct | Linux-only; portalocker same behavior, cross-platform |
| File locking | `portalocker` | `filelock` | `filelock` uses separate lock file; portalocker locks the data file directly |
| Config | `pydantic-settings` | `python-dotenv` + raw `os.environ` | No validation, errors surface at call time not startup |
| Config | `pydantic-settings` | `dynaconf` | Overkill; pydantic-settings is already on the pydantic dependency |
| Background tasks | `BackgroundTasks` | `celery` | Task overhead is tiny; Celery requires Redis broker, unneeded infra |
| Base image | `python:3.11-slim` | `python:3.11-alpine` | Alpine uses musl libc which causes binary compatibility issues with some pip packages; slim is safer |
| ASGI server | `uvicorn[standard]` | `gunicorn` | Single-container hackathon deployment; gunicorn adds process management complexity not needed here |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Library versions | HIGH | Confirmed via live PyPI index |
| FastAPI lifespan / BackgroundTasks patterns | HIGH | Verified via Context7 / official FastAPI docs |
| pydantic-settings BaseSettings pattern | HIGH | Verified via Context7 official docs |
| openai v2 SDK with custom base_url | MEDIUM | OpenAI-compatible endpoint behavior confirmed conceptually; json_object mode is the safe choice over parse() until GreenNode Qwen support for strict JSON schema mode is verified |
| portalocker for JSONL | HIGH | Widely used, cross-platform, docs confirm Linux flock behavior |
| Docker python:3.11-slim | HIGH | FastAPI official Docker guide recommends this base image |

---

## Sources

- FastAPI official docs — lifespan, BackgroundTasks: https://fastapi.tiangolo.com/advanced/events/ and https://fastapi.tiangolo.com/tutorial/background-tasks/
- FastAPI GitHub Context7 snippets: /fastapi/fastapi
- pydantic-settings Context7 docs: /pydantic/pydantic-settings
- OpenAI structured outputs guide: https://developers.openai.com/api/docs/guides/structured-outputs
- portalocker docs: https://portalocker.readthedocs.io/
- FastAPI Docker guide: https://fastapi.tiangolo.com/deployment/docker/
- PyPI live index for version confirmation (2026-06-11)
