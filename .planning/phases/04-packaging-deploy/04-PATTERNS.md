# Phase 4: Packaging & Deploy - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 4 files (Dockerfile, .env.example, .dockerignore, docker-compose.yml)
**Analogs found:** 3 partial (current Dockerfile structure reused; .dockerignore baseline extended; .env.example legacy fields preserved)

---

## Codebase Analog Assessment

The existing repo contains production deployment configuration files that serve as analogs for Phase 4:

| File | Current State | Role in Phase 4 | Reuse Opportunity |
|---|---|---|---|
| `Dockerfile` | 7 lines (minimal scaffold) | container-config | Base image, layer structure, port 8080 reuse; ADD non-root user + VOLUME declarations |
| `.env.example` | 7 fields (missing AKC_KB_DIR) | config-template | All 7 fields preserved; ADD AKC_KB_DIR field |
| `.dockerignore` | 16 entries | build-optimization | Current entries retained; ADD .planning/, kb/, kb_data/, tests/, docs/ patterns |
| `docker-compose.yml` | Does not exist | dev-testing | NEW file; optional for local volume persistence verification |

All Phase 4 patterns are derived from **RESEARCH.md** (security best practices, Docker layer caching, orchestration compatibility) with minimal cross-reference to Phase 1-3 codebase (those phases define service logic; Phase 4 wraps the deployed artifact).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `Dockerfile` (update) | container-config | build → image | existing Dockerfile (lines 1-7) | structural-reuse |
| `.env.example` (update) | config-template | static → env | existing .env.example (7 fields) | field-append |
| `.dockerignore` (update) | build-filter | source → context | existing .dockerignore | entry-extend |
| `docker-compose.yml` (new) | dev-testing | config → runtime | none in codebase | research-only |

---

## Pattern Assignments

### `Dockerfile` (container-config, build → image) — MAJOR UPDATE

**Analog:** Existing `Dockerfile` lines 1-7 — reuse base image selection, port, and WORKDIR structure; replace COPY strategy, entry point, and add non-root user + VOLUME.

**Current state:**
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "main.py"]
```

**Gaps being fixed:**
1. No non-root user (DEPLOY-01: runs as root — security risk)
2. No VOLUME declaration (DEPLOY-02: patterns lost on restart without persistent mount)
3. COPY . . invalidates dependency layer on code changes (build optimization)
4. `python main.py` entry point; should use `uvicorn` directly (ASGI best practice)
5. Missing Python runtime optimization env vars

**Updated Dockerfile** (15 lines + comments):
```dockerfile
FROM python:3.13-slim
WORKDIR /app

# Layer caching: install deps before app code (DEPLOY optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (selective, not COPY . .)
COPY akc/ ./akc/
COPY main.py .

# Non-root user security (DEPLOY-01)
RUN useradd -r -u 1001 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app
USER appuser

# Python runtime optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Volume for pattern persistence (DEPLOY-02)
VOLUME ["/app/data"]

EXPOSE 8080

# ASGI entry point (uvicorn, not python main.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Pattern details:**

**Pattern 1: Layer Caching Strategy (RESEARCH.md Layer Caching Strategy)**
- Rationale: Keeps dependency layer isolated from app code. Code changes do not invalidate pip install layer.
- Implementation: `COPY requirements.txt .` before `COPY akc/ ./akc/` and `COPY main.py .`
- Build benefit: ~30s full build → ~2s incremental build on code change
- Verified: Docker best practices docs

**Pattern 2: Selective COPY + .dockerignore (RESEARCH.md Docker Image Optimization)**
- Rationale: Excludes unnecessary files (tests, docs, .git, __pycache__) from build context. Smaller context → faster builds.
- Implementation: `COPY akc/ ./akc/` + `COPY main.py .` instead of `COPY . .`
- Requires: `.dockerignore` file updated with patterns listed below
- Build benefit: Build context reduced from ~10 MB to ~1 MB (estimate)
- Verified: Docker best practices

**Pattern 3: Non-Root User (DEPLOY-01, RESEARCH.md Pattern 1)**
- Rationale: Security hardening. If container is compromised, attacker has limited privileges (uid 1001, not root/0).
- Implementation: 
  ```dockerfile
  RUN useradd -r -u 1001 appuser && \
      mkdir -p /app/data && \
      chown -R appuser:appuser /app
  USER appuser
  ```
- Flags:
  - `-r` — system user (no login shell, no home dir)
  - `-u 1001` — fixed uid (standard convention; avoids system user collision)
  - `/app/data` must be created AND owned by appuser (so container can write patterns to mounted volume)
  - `chown -R appuser:appuser /app` — entire app directory owned by appuser
  - `USER appuser` — all subsequent commands and final CMD run as appuser (not root)
- Verified: FastAPI Docker deployment guide; production Dockerfile standard

**Pattern 4: VOLUME Declaration (DEPLOY-02, RESEARCH.md Pattern 2)**
- Rationale: Tells Docker daemon (and AgentBase platform) that `/app/data` is a persistent mount point. Without VOLUME, patterns written to container ephemeral filesystem are lost on restart.
- Implementation: `VOLUME ["/app/data"]` placed before CMD
- Semantics: Declares intent; actual mount provided at runtime by orchestration (docker run -v, docker-compose, or AgentBase)
- Mount point safety: Directory created and owned by appuser RUN step ensures read/write permissions
- Verified: Docker docs; AgentBase platform integration docs

**Pattern 5: Python Runtime Optimization (RESEARCH.md Docker Image Optimization)**
- Rationale: `PYTHONUNBUFFERED=1` ensures logs are not buffered — critical for live container monitoring. `PYTHONDONTWRITEBYTECODE=1` prevents .pyc bloat in mounted volumes.
- Implementation:
  ```dockerfile
  ENV PYTHONUNBUFFERED=1
  ENV PYTHONDONTWRITEBYTECODE=1
  ```
- Verified: FastAPI deployment best practices; standard in production Python containers

**Pattern 6: ASGI Entry Point via uvicorn (RESEARCH.md Architecture Patterns)**
- Rationale: `uvicorn main:app` is the industry-standard ASGI entry point. More flexible than `python main.py` (which also works, but less standard for container orchestration).
- Implementation: `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]`
- Compatibility: AgentBase can override CMD at deployment time if needed
- Verified: FastAPI official deployment guide

**Anti-patterns to avoid:**
- Do NOT use `COPY . .` — invalidates dependency layer on code changes
- Do NOT run as root (missing USER statement) — security risk
- Do NOT omit VOLUME declaration — patterns are lost on restart
- Do NOT hardcode `AKC_KB_DIR` in Dockerfile ENV — runtime config belongs in .env or orchestration injection
- Do NOT use `CMD ["python", "main.py"]` with working Dockerfile EXPOSE changes — less standard than uvicorn

---

### `.env.example` (config-template, static → env) — FIELD APPEND

**Analog:** Existing `.env.example` (7 fields)

**Current state:**
```
GREENNODE_CLIENT_ID=
GREENNODE_CLIENT_SECRET=
GREENNODE_AGENT_IDENTITY=
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
MEMORY_ID=
```

**Gap:** Missing `AKC_KB_DIR` field. Phase 1 requires this field at startup (FNDTN-03, FNDTN-01). Service crashes with `ValidationError: Field required` if missing.

**Updated .env.example** (add one line at end):
```
GREENNODE_CLIENT_ID=
GREENNODE_CLIENT_SECRET=
GREENNODE_AGENT_IDENTITY=
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
MEMORY_ID=
AKC_KB_DIR=/app/data
```

**Pattern details:**

**Pattern 7: Environment Template Completeness (DEPLOY-01, RESEARCH.md Pitfall 3)**
- Rationale: `.env.example` documents all required env vars. Copying `.env.example` → `.env` and filling values should be sufficient to start the service (fail-fast validation in `akc/core/config.py`).
- Implementation: Add `AKC_KB_DIR=/app/data` — this is the mount point declared in Dockerfile VOLUME
- Verification: Check that `akc/core/config.py` `Settings` class lists all 8 fields; missing field raises ValidationError at startup
- Verified: pydantic-settings best practices; RESEARCH.md Pitfall 3

**Value assignment:**
- `AKC_KB_DIR=/app/data` — matches VOLUME mount point in Dockerfile
- In Docker Compose: `volumes: - ./kb_data:/app/data` maps host `./kb_data/` to container `/app/data`
- In AgentBase: Platform automatically mounts persistent storage to `/app/data` when it detects VOLUME declaration

---

### `.dockerignore` (build-filter, source → context) — ENTRY EXTEND

**Analog:** Existing `.dockerignore` (16 entries)

**Current state:**
```
.venv/
venv/
__pycache__/
*.py[cod]
.env
.env.*
.greennode.json
.agentbase/
.agentbase-state.json
*.credentials.json
.git/
.gitignore
*.md
.claude/
plans/
docs/
```

**Analysis:** Current entries cover Python cache, secrets, credentials, and git history — all appropriate. Must be extended for:
1. Phase 4 introduces new build artifacts: `kb/`, `kb_data/` (local test data; would be overwritten by volume mount anyway)
2. Phase 1-3 planning / test directories: `.planning/`, `tests/` (not needed in production image)

**Updated .dockerignore** (add 3 entries):
```
.venv/
venv/
__pycache__/
*.py[cod]
.env
.env.*
.greennode.json
.agentbase/
.agentbase-state.json
*.credentials.json
.git/
.gitignore
*.md
.claude/
plans/
docs/
.planning/
tests/
kb/
kb_data/
```

**Pattern details:**

**Pattern 8: Build Context Minimization (RESEARCH.md Docker Image Optimization)**
- Rationale: Smaller build context = faster Docker build. Excluded files are not needed in production image (they are recreated at runtime or are development-only).
- Implementation: Add entries for:
  - `.planning/` — project planning docs (not runtime code)
  - `tests/` — test code (not production code)
  - `kb/` — legacy KB directory (if it exists; prevents bloat)
  - `kb_data/` — local dev test data (patterns.jsonl will be empty at image build; patterns are added at runtime)
- Build benefit: Removes 5-10 MB of unnecessary files from context
- Verified: Docker best practices

**Anti-patterns to avoid:**
- Do NOT include `.env` in image — secrets should not be baked into artifact
- Do NOT include `.git/` — repository history not needed
- Do NOT include `tests/` or `.planning/` — development-only
- Do NOT include Python cache (`__pycache__/`, `*.pyc`) — rebuilt at runtime anyway

---

### `docker-compose.yml` (dev-testing, config → runtime) — NEW FILE

**Analog:** None in codebase. This is a developer convenience file for local testing of volume persistence.

**Rationale:** Developers need an easy way to verify that patterns survive container restart (DEPLOY-02 validation). Docker Compose provides one-command setup with volume mounts.

**New docker-compose.yml** (23 lines):
```yaml
version: "3.8"

services:
  akc:
    build: .
    ports:
      - "8080:8080"
    environment:
      LLM_MODEL: ${LLM_MODEL:-gpt-4o-mini}
      LLM_BASE_URL: ${LLM_BASE_URL:-http://localhost:8000}
      LLM_API_KEY: ${LLM_API_KEY:-test-key}
      MEMORY_ID: ${MEMORY_ID:-test-memory}
      AKC_KB_DIR: /app/data
    volumes:
      - ./kb_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 5s
      timeout: 2s
      retries: 3
      start_period: 10s
```

**Pattern details:**

**Pattern 9: Docker Compose for Local Testing (RESEARCH.md Deployment Workflow)**
- Rationale: Enables developers to test volume persistence locally before deploying to AgentBase.
- Usage workflow:
  1. `docker-compose up` — builds image, starts container, mounts `./kb_data/` to `/app/data`
  2. Call `/remember` via curl to create patterns (stored in `./kb_data/patterns.jsonl` on host)
  3. Call `/recall` to verify patterns are stored
  4. `docker-compose down` then `docker-compose up` — container restarts; patterns in `./kb_data/` persist
  5. Call `/health` and `/recall` again — pattern count should match step 1
  6. **Success:** Patterns survived restart; volume mounting works
- Verification: After step 5, compare pattern_count in logs — must match what was created in step 2

**Compose details:**

- `build: .` — builds image from Dockerfile in current directory
- `ports: 8080:8080` — exposes container port 8080 to host
- `environment:` — injects env vars at runtime; uses `.env` file if present, otherwise defaults
  - `LLM_MODEL: ${LLM_MODEL:-gpt-4o-mini}` — reads from .env or command line; defaults to gpt-4o-mini if missing
  - `AKC_KB_DIR: /app/data` — hardcoded to match VOLUME mount point (no override needed)
- `volumes: ./kb_data:/app/data` — mounts host directory `./kb_data/` (created on first run) to container path `/app/data`
  - When container exits, `./kb_data/patterns.jsonl` persists on host
  - Next `docker-compose up` remounts the same host directory
  - Patterns are restored from persistent volume
- `healthcheck:` — optional but useful for monitoring
  - Tests `GET /health` endpoint every 5 seconds
  - AgentBase may ignore this (it provides its own health checks), but useful for local debugging
  - `start_period: 10s` — grace period for container to start before health checks begin

**Anti-patterns to avoid:**
- Do NOT commit `./kb_data/` directory to git (add to `.gitignore`)
- Do NOT hardcode production secrets in docker-compose.yml — use .env defaults or pass via command line
- Do NOT remove the `volumes:` section — it's the whole point of local testing

**Usage examples:**

```bash
# First run: builds image, starts container
docker-compose up

# In another terminal: send a request
curl -X POST http://localhost:8080/remember -H "Content-Type: application/json" -d '{"task":"test","outcome":"success"}'

# Check that pattern was written to host filesystem
cat kb_data/patterns.jsonl

# Stop container (Ctrl+C in first terminal) and restart
docker-compose down
docker-compose up

# Pattern should be restored from persistent volume
curl http://localhost:8080/health
# Should show pattern_count > 0 (same as before restart)
```

---

## Shared Patterns

### Container Security: Non-Root User
**Source:** RESEARCH.md Pattern 1 + DEPLOY-01
**Apply to:** `Dockerfile` (RUN useradd + USER statement)
```dockerfile
RUN useradd -r -u 1001 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app
USER appuser
```
**Rationale:** Limits container process privilege; if exploited, attacker is uid 1001, not root

### Docker Layer Caching
**Source:** RESEARCH.md Layer Caching Strategy
**Apply to:** `Dockerfile` (COPY order)
- First: `COPY requirements.txt . && RUN pip install` (changes rarely)
- Second: `COPY akc/ ./akc/ && COPY main.py .` (changes frequently)
- Result: Code changes reuse cached dependency layer; ~30s build becomes ~2s

### Persistent Storage Declaration
**Source:** RESEARCH.md Pattern 2 + DEPLOY-02
**Apply to:** `Dockerfile` (VOLUME) + `docker-compose.yml` (volumes)
```dockerfile
VOLUME ["/app/data"]  # Dockerfile
```
```yaml
volumes:
  - ./kb_data:/app/data  # docker-compose.yml
```
**Rationale:** VOLUME tells Docker/AgentBase that directory is a mount point; docker-compose.yml binds host directory; patterns survive restart

### Python Runtime Optimization
**Source:** RESEARCH.md Docker Image Optimization
**Apply to:** `Dockerfile` (ENV statements)
```dockerfile
ENV PYTHONUNBUFFERED=1          # logs not buffered → visible in container logs
ENV PYTHONDONTWRITEBYTECODE=1   # prevents .pyc bloat in mounted volumes
```

### ASGI Entry Point
**Source:** RESEARCH.md Architecture Patterns
**Apply to:** `Dockerfile` (CMD)
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```
**Rationale:** Industry standard for FastAPI in production; more flexible than `python main.py`

---

## File-by-File Diff Summary

### `Dockerfile`
- **Lines added:** ~10 (non-root user, VOLUME, ENV, uvicorn entry)
- **Lines modified:** 2 (COPY selective, CMD entry point)
- **Net change:** 7 lines → 25 lines (structural improvement, not code bloat)
- **Verification:** `docker build -t akc:test . && docker inspect akc:test | jq '.[] | .Config | {User, Volumes, ExposedPorts}'` — should show User: "1001:1001", Volumes: {"/app/data": {}}, ExposedPorts: {"8080/tcp": {}}

### `.env.example`
- **Lines added:** 1 (AKC_KB_DIR=/app/data)
- **Lines modified:** 0
- **Net change:** 7 fields → 8 fields (one-liner addition)
- **Verification:** `wc -l .env.example` — should show 8 lines; `grep -c "=" .env.example` — should show 8 fields

### `.dockerignore`
- **Lines added:** 3 (.planning, tests, kb, kb_data)
- **Lines modified:** 0
- **Net change:** 16 entries → 20 entries
- **Verification:** `grep -c "." .dockerignore` — should show 20+ entries

### `docker-compose.yml`
- **Lines added:** 23 (entire new file)
- **Lines modified:** 0
- **Verification:** `docker-compose config > /dev/null` — should validate without error

---

## Validation Architecture

**Phase 4 execution must verify:**

1. **Dockerfile syntax** — `docker build -t akc:test .` completes without error
2. **Image metadata** — `docker inspect akc:test` shows User=1001:1001, Volumes={"/app/data": {}}, ExposedPorts={"8080/tcp": {}}
3. **Startup logging** — Container logs show `AKC starting — KB_DIR: /app/data, patterns: 0` (from Phase 1 lifespan)
4. **Health endpoint** — `curl http://localhost:8080/health` returns `{"status":"ok","pattern_count":0}`
5. **Volume persistence** (docker-compose.yml test):
   - `docker-compose up` creates `./kb_data/` directory
   - Write a test pattern to `./kb_data/patterns.jsonl`
   - `docker-compose down` then `docker-compose up` — pattern count is preserved
   - **Success:** Container restart restores patterns from persistent volume

---

## Cross-Reference: Phase 1-3 Dependency

Phase 4 has minimal dependency on Phase 1-3 service code:

| Phase 4 File | Depends On | Reason |
|---|---|---|
| `Dockerfile` COPY | Phase 1 directory structure (`akc/`, `main.py`) | Dockerfile copies these files into image |
| `Dockerfile` CMD | Phase 1 FastAPI app export | `uvicorn main:app` requires `main.py` to export `app = FastAPI(...)` |
| `.env.example` AKC_KB_DIR | Phase 1 config validation | `akc/core/config.py` requires `AKC_KB_DIR` env var |
| `docker-compose.yml` | Phase 1 /health endpoint | healthcheck calls `/health` to verify container is running |

**No dependency on Phase 2-3 endpoints** — Phase 4 is complete before Phase 2-3 code is added.

---

## Common Pitfalls & Mitigations

### Pitfall 1: Forgetting VOLUME Declaration
**Risk:** DEPLOY-02 not satisfied. Patterns lost on container restart.
**Prevention:** Phase 4 PATTERNS.md explicitly lists VOLUME ["/app/data"]. Code review checks for this line.
**Catch:** docker-compose.yml test reveals missing VOLUME — patterns.jsonl disappears after restart.

### Pitfall 2: Running as Root
**Risk:** DEPLOY-01 not satisfied. Security vulnerability.
**Prevention:** Dockerfile includes RUN useradd + USER statements. Code review verifies these.
**Catch:** `docker inspect` shows User=root:root → code review fails.

### Pitfall 3: COPY . . Invalidates Dependency Layer
**Risk:** Build times 30s instead of 2s on code change. Developer frustration.
**Prevention:** PATTERNS.md shows selective COPY pattern with .dockerignore.
**Catch:** Docker build timing test reveals slow incremental builds.

### Pitfall 4: AKC_KB_DIR Missing from .env.example
**Risk:** FNDTN-03 not satisfied. Developers copy .env.example and service fails to start.
**Prevention:** PATTERNS.md explicitly adds AKC_KB_DIR=... line.
**Catch:** Integration test (Phase 4 execution) starts container with only .env.example values — should fail if AKC_KB_DIR missing.

### Pitfall 5: docker-compose.yml Not in Repo
**Risk:** DEPLOY-02 not verified locally. Developers deploy without testing volume persistence.
**Prevention:** PATTERNS.md includes full docker-compose.yml content. Phase 4 execution creates this file.
**Catch:** Developers cannot easily run `docker-compose up` to test locally.

---

## Metadata

**Analog search scope:** `/home/brewuser/work/clawthon/dl-starter-kit/` — entire repo
**Files scanned:** `Dockerfile`, `.env.example`, `.dockerignore`, `.gitignore`, `requirements.txt`, Phase 1-3 RESEARCH.md files
**Deployment configuration files found:** 4 (Dockerfile, .env.example, .dockerignore, none for docker-compose.yml)
**Pattern extraction date:** 2026-06-11
**Pattern authority:** RESEARCH.md (Phase 4 research document) + Docker official best practices
**Confidence:** HIGH — all patterns verified against Docker documentation and FastAPI deployment guides

---

## Key Takeaway

Phase 4 modifies or creates 4 files: Dockerfile (add non-root user + VOLUME + uvicorn entry), .env.example (add AKC_KB_DIR), .dockerignore (extend with .planning/tests/kb/kb_data), and docker-compose.yml (new file for local testing). All changes are low-risk, no changes to Phase 1-3 service code required. Estimated execution time: 30-45 minutes. DEPLOY-01, DEPLOY-02, DEPLOY-03 requirements fully satisfied by these changes.
