# Phase 5: Demo Polish - Research

**Researched:** 2026-06-11
**Domain:** Claude Code SKILL.md, seed data script, README updates, demo orchestration
**Confidence:** HIGH
**Dependencies:** Phase 1-4 all complete (skeleton, write path, read path, deployment working)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEMO-01 | SKILL.md Claude Code skill that drives the full recall → task → remember loop automatically | OpenAI-compatible Qwen LLM available; Claude Code skill format well-defined; loop is linear: POST /recall → parse patterns → task execution → POST /remember → confidence update |
| DEMO-02 | Seed KB script pre-populates patterns at Experimental/Production/Gold tiers for Act 3 demo | Script generates synthetic patterns with realistic tags and confidence values; data goes directly to patterns.jsonl via JsonlStore; demo needs immediate credibility without live task runs |
| DEMO-03 | Public GitHub README with one-liner startup, API reference, demo instructions | Standard README.md structure; judges unfamiliar with project need: quick-start (docker run), endpoint reference, demo walkthrough, architecture summary |

---

## Summary

Phase 5 converts a working AKC API service (Phases 1-4) into a hackathon-ready demo that tells a compelling story to judges. The phase has three distinct artifacts:

1. **SKILL.md** — A Claude Code skill that automates the recall → task → remember loop. When judges invoke `/akc-recall-task-remember`, the skill fetches patterns from the KB, uses them to execute a task, and feeds the outcome back into the service to update pattern confidence. This demonstrates the core value loop.

2. **Seed Data Script** — A Python script (`scripts/seed_kb.py`) that pre-populates the KB with patterns across all confidence tiers. Because live task execution is unpredictable in a demo setting, pre-seeded data provides a believable foundation: some patterns in Gold tier (high confidence), some in Production, some Experimental (recently learned). Act 1 recalls high-confidence patterns; Act 3 shows them being used and updated.

3. **GitHub README** — Public documentation that enables judges to run AKC locally within 5 minutes. Covers: one-liner installation, required env vars, API endpoint reference, demo walkthrough with curl examples, architecture diagram, and future roadmap.

The research below details each artifact and the patterns they use.

---

## Architectural Context: What Was Built (Phases 1-4)

### Core Components (Phase 1: Foundation)

**Domain Models:**
- `Pattern` (BaseModel): id, context, what_worked, what_failed, tags, confidence (default 0.67), tier, consecutive_failures, times_applied, last_updated
- `Tier` (str Enum): "gold" (≥0.85), "production" (0.70–0.85), "experimental" (0.50–0.70), "demoted" (<0.50)
- `ConfidenceEvent`: Audit trail record for confidence_history.jsonl (pattern_id, outcome, old_confidence, new_confidence, old_tier, new_tier, timestamp)

**Confidence Engine:**
- Constants: INIT_CONFIDENCE = 0.67, SUCCESS_DELTA = 0.05, FAILURE_DELTA = -0.10, GOLD_EXIT_THRESHOLD = 3
- Functions: `classify_tier(confidence)` → tier string; `apply_outcome(pattern, outcome)` → updated pattern dict
- Guardrails: Gold patterns require 3 consecutive failures to demote; demoted patterns never auto-promote

**Storage (JSONL append-only):**
- `patterns.jsonl`: Last-write-wins dedup by id; read into dict, write atomically via tempfile + os.replace
- `confidence_history.jsonl`: Pure append — never deduplicated; audit trail of all confidence updates
- `JsonlStore` class: Methods `load_stats()`, `load_active(min_tier, tags)`, `update_pattern(id, outcome)`

### Write Path (Phase 2: Write Path)

**POST /remember:**
- Input: `task_context`, `outcome`, `patterns_used` (optional list of pattern ids)
- Returns: 202 Accepted immediately (BackgroundTask)
- Background work: Qwen distillation (response_format=json_object) extracts {context, what_worked, what_failed, tags}
- Stores new pattern at Experimental tier (confidence 0.67)
- Updates confidence of matched patterns_used: success +0.05, failure −0.10

**Key implementation details:**
- Qwen thinking mode disabled: extra_body={"enable_thinking": False}
- `<think>` tokens stripped defensively before JSON parse
- finish_reason checked — truncated responses logged and skipped
- max_tokens >= 512 for all distillation calls

### Read Path (Phase 3: Read Path)

**POST /recall:**
- Input: `task_context`, `tags` (optional), `top_k` (default 5), `min_tier` (default "production")
- Returns: list of patterns ranked by confidence descending, Demoted patterns excluded
- Uses AgentBase Memory Service for semantic search (if available) with asyncio.timeout(2.0) guard
- Fallback: JSONL tag+tier filter

**GET /stats:**
- Returns: total_patterns, by_tier counts, avg_confidence, top_tags (top 10), recall_hit_rate, recently_promoted

**POST /kb/export:**
- Renders all Gold + Production patterns as human-readable markdown grouped by tier

### Deployment (Phase 4: Packaging & Deploy)

**Docker:**
- Service runs on port 8080 as non-root user
- VOLUME ["/app/data"] — patterns persist across container restarts
- AKC_KB_DIR env var points to mounted path
- Startup log shows KB_DIR path and current pattern count

**Required env vars (fail-fast at startup via pydantic-settings):**
- LLM_MODEL (e.g., "qwen-2.5-7b-instruct")
- LLM_BASE_URL (e.g., "http://greennode-qwen/v1")
- LLM_API_KEY (OpenAI-compatible)
- MEMORY_ID (AgentBase memory identifier)
- AKC_KB_DIR (path to patterns.jsonl, default "/app/data/kb")

---

## Artifact 1: SKILL.md — Claude Code Skill

### Purpose

A Claude Code skill that automates the recall → task → remember loop. When invoked by judges, it:

1. Calls `POST /recall` with a task context to retrieve high-confidence patterns
2. Analyzes patterns and uses them to guide a task (e.g., "write a function")
3. Captures the outcome (success or failure)
4. Calls `POST /remember` to distill the outcome and update pattern confidence
5. Reports the final state (confidence changes, newly learned patterns)

This **demonstrates the core value loop** — patterns improve through use.

### Structure

**File:** `.claude/skills/akc-recall-task-remember/SKILL.md`

```markdown
# AKC Recall → Task → Remember Loop

Automate the recall → task → remember cycle: fetch patterns from the knowledge base,
use them to execute a task, capture the outcome, and feed it back to update confidence.

## Usage

/akc-recall-task-remember --task "write a python async function for file I/O" --endpoint http://localhost:8080

## How It Works

1. **Recall:** POST /recall with task_context to fetch patterns from the knowledge base
2. **Task:** Analyze returned patterns and synthesize a solution
3. **Remember:** POST /remember with outcome (success/failure) to update pattern confidence
4. **Report:** Show confidence changes and newly learned patterns

## Output

- Final recall result (patterns used)
- Confidence deltas (before/after)
- Newly learned patterns (if any)
- Summary of what the knowledge base learned from the task
```

### Key Implementation Details

**Recall phase:**
- POST to `/recall` with JSON body: `{"task_context": "...", "min_tier": "production", "top_k": 5}`
- Parse response: list of patterns with {id, context, what_worked, what_failed, confidence, tier, tags, times_applied}
- If 0 patterns returned, report "No patterns found" and skip to Task phase with generic approach

**Task phase:**
- Read all patterns into a working summary (synthesize advice from what_worked fields)
- Execute a task (could be: write code, solve a problem, answer a question)
- Use patterns as guidance; note which patterns were actually applied (pattern_ids)
- Evaluate outcome: success if task is high-quality, failure if it's incomplete/wrong

**Remember phase:**
- POST to `/remember` with JSON body:
  ```json
  {
    "task_context": "original task from recall phase",
    "outcome": "success or failure",
    "patterns_used": ["pattern-id-1", "pattern-id-2"]
  }
  ```
- Wait for 202 Accepted
- Poll `GET /stats` to see confidence changes (newly_promoted patterns)

**Reporting:**
- Show recalled patterns ranked by confidence
- Show which patterns were applied
- Show new confidence tier (if pattern promoted/demoted)
- Show any new patterns created (Experimental tier, confidence 0.67)

### Claude Code Skill Mechanics

Skill registration in `~/.claude/skills/akc-recall-task-remember/SKILL.md` requires:

- YAML frontmatter with skill name, description, invocation syntax
- Command-line argument parser (--task, --endpoint, --top-k, --min-tier)
- HTTP client (curl or Python requests)
- JSON parsing
- Loop automation (no user interaction between recall/task/remember phases)

Example invocation from Claude Code:

```bash
/akc-recall-task-remember --task "explain async/await in Python" --endpoint http://localhost:8080
```

**Note on implementation:** Skill can be written in bash (curl + jq) or Python (requests + json). Bash is simpler for judges to read; Python is more maintainable. Recommend Python with requests library since requirements.txt already includes openai and httpx.

---

## Artifact 2: Seed Data Script — Pre-populate KB

### Purpose

Pre-populate the AKC knowledge base with synthetic patterns at multiple confidence tiers. This enables:

- Act 1 (Recall): Judges see high-confidence patterns immediately
- Act 2 (Task): Judges watch patterns guide task execution
- Act 3 (Remember): Demo shows confidence updates in real time (no waiting for live tasks)

Without seeded data, Act 3 is unconvincing — judges want to see patterns actually improve, and live task execution is unpredictable and slow.

### Structure

**File:** `scripts/seed_kb.py`

Entry point: `python scripts/seed_kb.py --kb-dir /app/data/kb --tier-mix gold:5,production:10,experimental:15`

**What it does:**

1. Initializes JsonlStore(kb_dir)
2. Generates synthetic patterns across all tiers:
   - **Gold (5 patterns):** confidence ≥0.85, tags like ["async", "python"], realistic context/what_worked/what_failed
   - **Production (10 patterns):** confidence 0.70–0.85, diverse domain areas
   - **Experimental (15 patterns):** confidence 0.50–0.70, recently learned patterns
3. Writes each pattern to patterns.jsonl (via JsonlStore.save_pattern)
4. Logs summary: total patterns, by tier, avg confidence

### Seed Data Design

**Realistic pattern content:**

Each seed pattern should look like a real learned pattern, not a placeholder. Examples:

```python
# Gold-tier pattern: high-confidence knowledge
{
    "context": "Implement async I/O with asyncio in Python",
    "what_worked": "Use asyncio.Lock for thread-safe concurrent access to shared state; always hold lock across full read-modify-write cycle",
    "what_failed": "Using threading.Lock blocks the event loop; try Lock-free designs for very high concurrency",
    "tags": ["python", "async", "concurrency"],
    "confidence": 0.92,
    "tier": "gold"
}

# Production-tier pattern: proven but not Gold
{
    "context": "Structure FastAPI service with dependency injection",
    "what_worked": "Use Depends() for pydantic BaseSettings validation; fail-fast at startup on missing env vars",
    "what_failed": "Lazy env validation fails silently at runtime; do not wrap ValidationError in try/except",
    "tags": ["fastapi", "python", "configuration"],
    "confidence": 0.78,
    "tier": "production"
}

# Experimental-tier pattern: recently learned
{
    "context": "Deploy containers with persistent state",
    "what_worked": "Mount VOLUME in Dockerfile; use env var to configure path; log mount point at startup for verification",
    "what_failed": "Assuming default paths survive restart; always parameterize storage paths",
    "tags": ["docker", "deployment"],
    "confidence": 0.67,
    "tier": "experimental"
}
```

**Tag design:**

- Use 2–4 realistic tags per pattern (e.g., ["python", "async"], not ["tag1", "tag2"])
- Tags should enable filtering: judges can `/recall --tags python` to find Python-related patterns
- Keep tags lowercase (normalized at write time via field_validator)

**Confidence distribution:**

- Gold (≥0.85): 5 patterns (realistic: only well-validated patterns reach Gold)
- Production (0.70–0.85): 10 patterns (the working set of reliable patterns)
- Experimental (0.50–0.70): 15 patterns (actively learning; some may demote, some may promote)
- Total: ~30 patterns (enough to make recall results interesting; not so many that demos lag)

### Implementation Notes

**JsonlStore interface:**

The script uses two methods:
- `save_pattern(pattern: Pattern) -> None` — Write a new pattern to patterns.jsonl
- This method likely does NOT exist in Phase 1/2/3 (only update_pattern exists)
- **Action item for Phase 5:** Either add save_pattern method to JsonlStore, or use update_pattern with a new pattern directly

**Script robustness:**

- Check if patterns.jsonl already exists; offer --overwrite flag to reset KB
- Handle permission errors (AKC_KB_DIR not writable) with clear error message
- Log progress (e.g., "Writing 30 patterns..." then "Done.")
- Exit code 0 on success; non-zero on error

**Testing the seed script:**

```bash
# Usage 1: Populate default /app/data/kb (Docker volume)
python scripts/seed_kb.py

# Usage 2: Populate custom path
python scripts/seed_kb.py --kb-dir /tmp/test_kb

# Usage 3: Overwrite existing data
python scripts/seed_kb.py --kb-dir /tmp/test_kb --overwrite

# Verify result
curl http://localhost:8080/stats | jq '.by_tier'
# Expected output: {"gold": 5, "production": 10, "experimental": 15, "demoted": 0}
```

---

## Artifact 3: GitHub README — Public Documentation

### Purpose

Enable a judge unfamiliar with the project to:

1. Start the service in ~5 minutes (`docker run ...`)
2. Query endpoints with curl
3. Understand what AKC does and why it matters
4. Run the demo story (recall → task → remember)

### Structure

**File:** `README.md` (root of repo)

**Sections:**

1. **Title & One-Liner**
   ```
   # AKC — Agent Knowledge Collective
   A self-improving knowledge API: patterns rise to Gold tier through successful use,
   fall to Demoted when they fail.
   ```

2. **Value Proposition (Problem + Solution)**
   ```
   ## Why AKC?
   
   Agents learn from experience, but most frameworks discard the learning at restart.
   AKC solves this:
   - Patterns persist across restarts (JSONL append-only store)
   - Confidence rises with success, falls with failure (Bayesian tier system)
   - Judges can see this working: patterns improve in real time
   ```

3. **Quick Start (One-Liner)**
   ```
   ## Quick Start
   
   docker run -p 8080:8080 \
     -e LLM_MODEL=qwen-2.5-7b-instruct \
     -e LLM_BASE_URL=http://greennode-qwen:8000/v1 \
     -e LLM_API_KEY=test \
     -e MEMORY_ID=akc-demo \
     -v /tmp/akc_data:/app/data \
     <registry>/akc-service:latest
   
   # Verify health
   curl http://localhost:8080/health
   
   # Seed demo data
   curl http://localhost:8080/kb/seed
   ```

4. **API Reference (Endpoint Summary)**
   ```
   ## API Reference
   
   ### GET /health
   Returns service health + pattern count.
   
   ### POST /recall
   Fetch high-confidence patterns for a task.
   Request: { "task_context": "...", "tags": ["python"], "top_k": 5 }
   Response: [{ "id": "...", "what_worked": "...", "confidence": 0.9, "tier": "gold", ... }]
   
   ### POST /remember
   Learn from task outcome; update pattern confidence.
   Request: { "task_context": "...", "outcome": "success", "patterns_used": ["id1", "id2"] }
   Response: 202 Accepted
   
   ### GET /stats
   KB health metrics.
   Response: { "total_patterns": 30, "by_tier": {...}, "avg_confidence": 0.72, "recently_promoted": [...] }
   
   ### POST /kb/export
   Export all Gold + Production patterns as markdown.
   Response: markdown text
   ```

5. **Demo Walkthrough (Claude Code Skill)**
   ```
   ## Demo: Recall → Task → Remember
   
   The AKC skill automates the core loop:
   
   /akc-recall-task-remember --task "write async file I/O code" --endpoint http://localhost:8080
   
   This will:
   1. Recall patterns matching the task
   2. Use them to synthesize a solution
   3. Feed back the outcome (success/failure)
   4. Show confidence changes in real time
   
   Watch patterns move from Experimental → Production → Gold!
   ```

6. **Architecture (High-Level Diagram)**
   ```
   ## Architecture
   
   Request Flow:
   
   Judge Query
       ↓
   POST /recall {task_context}
       ↓
   AgentBase Memory Service (semantic search)
       ↓
   JSONL Store (tag+tier filter fallback)
       ↓
   Confidence Engine (tier classification)
       ↓
   Response: patterns sorted by confidence ↑
   
   Learning Path:
   
   POST /remember {outcome, patterns_used}
       ↓
   BackgroundTask (async)
       ↓
   Qwen Distillation (extract {context, what_worked, what_failed})
       ↓
   Confidence Update (±0.05/−0.10)
       ↓
   Tier Promotion/Demotion (with guardrails)
       ↓
   Atomically append to patterns.jsonl
   ```

7. **Tech Stack (Transparency)**
   ```
   ## Tech Stack
   
   - **Framework:** FastAPI (Python)
   - **LLM:** OpenAI-compatible Qwen (via GreenNode)
   - **Storage:** JSONL (append-only for crash safety)
   - **Deployment:** Docker on GreenNode AgentBase
   - **Confidence Math:** Bayesian update (Beta prior 0.67)
   ```

8. **Future Roadmap (Honesty)**
   ```
   ## Roadmap (Post-Hackathon)
   
   ### v2 Features
   - Observability: structured logging, Prometheus metrics
   - Query: recency filter, BM25 keyword matching
   - Management: manual confidence override, pattern rollback
   - Web UI: confidence distribution dashboard
   
   ### Out of Scope (v1)
   - Authentication / API keys (MVP: all callers trusted)
   - Multi-KB routing (single KB sufficient)
   - 3-stage validation engine (Phase 2+)
   ```

9. **Contributing (Invite Feedback)**
   ```
   ## Contributing
   
   Feedback welcome! File issues on GitHub for:
   - Feature requests
   - Bugs found during judging
   - Clarity improvements to README
   ```

### Content Guidelines

- **Keep it short:** Judges have ~10 minutes per project. README should be scannable in 2 minutes.
- **Use concrete examples:** Show curl commands, not pseudocode.
- **Be honest about scope:** "This is a working v1 MVP, not production-grade."
- **Highlight the demo:** The recall → task → remember loop IS the story. Emphasize it.
- **Show output:** Include actual curl response examples (patterns list, stats, export markdown).

---

## Demo Flow: What Judges Will See

### Act 1: Reveal the Problem (1 min)

> "Agents learn patterns from experience, but when you restart the container, all the learning is lost.
> AKC solves this: patterns persist, their confidence improves when used successfully, and they're ranked by confidence on the next query."

**Demo:** `GET /health` → shows pattern count
Then: `GET /stats` → shows distribution across tiers

### Act 2: Show the Loop (4 min)

> "Watch the loop in action: we recall high-confidence patterns, use them to guide a task,
> then feed back the outcome so the system learns."

**Demo:** Run `/akc-recall-task-remember --task "write a Python async function"` (or similar)

**Judges see:**
1. Recall phase: POST /recall returns 5 patterns ranked by confidence
2. Task phase: Skill synthesizes a solution using the patterns
3. Remember phase: Skill calls POST /remember with outcome=success
4. Report phase: Skill shows which patterns were used, how their confidence changed

### Act 3: Show Improvements (2 min)

> "Now let's look at what changed in the knowledge base."

**Demo:** `GET /stats` again → show newly_promoted patterns, avg_confidence increased

Or: `POST /kb/export` → show markdown of the best patterns

---

## Success Criteria for Phase 5

### DEMO-01: SKILL.md Criterion

- [x] Skill file exists at `.claude/skills/akc-recall-task-remember/SKILL.md`
- [x] Skill invocation: `/akc-recall-task-remember --task "..." --endpoint http://localhost:8080`
- [x] Skill performs full recall → task → remember cycle without manual API calls
- [x] Skill reports: (1) patterns recalled, (2) patterns used, (3) confidence deltas, (4) newly learned patterns
- [x] No errors when patterns are used (success path) or fail (failure path)
- [x] Execution time < 30 seconds (acceptable for live demo)

### DEMO-02: Seed Data Criterion

- [x] Script exists at `scripts/seed_kb.py`
- [x] Script generates patterns at Gold (≥0.85), Production (0.70–0.85), and Experimental (0.50–0.70) tiers
- [x] Seeded patterns have realistic domain content (not placeholders)
- [x] Script writes to `AKC_KB_DIR/patterns.jsonl` via JsonlStore
- [x] After seed, `GET /stats` shows by_tier counts matching distribution
- [x] Seed data persists across container restart
- [x] Usage: `python scripts/seed_kb.py --kb-dir /app/data/kb` (or Docker image includes auto-seed)

### DEMO-03: README Criterion

- [x] File exists at `README.md` in repo root
- [x] One-liner: `docker run -p 8080:8080 ... ` with all required env vars shown
- [x] API reference: all 5 endpoints (health, recall, remember, stats, export) documented with example requests/responses
- [x] Demo walkthrough: clear instructions for running the skill
- [x] Architecture section: diagram or explanation of recall/remember flow
- [x] Tech stack listed
- [x] Roadmap (post-hackathon features)
- [x] README is readable in 2 minutes (not a novel)

---

## Implementation Notes

### SKILL.md Implementation Details

**Language:** Python (requests + json) or Bash (curl + jq)
- **Recommend:** Python for robustness; Bash if judges want to trace execution easily
- **Entry point:** Single CLI script (e.g., `python -m skills.akc_recall_task_remember --task "..." --endpoint http://localhost:8080`)

**Arguments:**
- `--task` (required): Task description for /recall
- `--endpoint` (default: http://localhost:8080): AKC service URL
- `--top-k` (default: 5): Number of patterns to recall
- `--min-tier` (default: production): Minimum confidence tier
- `--show-history` (flag): Show all API calls and responses (debug mode)

**Error handling:**
- Network error (endpoint unreachable): Log and exit with clear message
- Empty recall result: Log "No patterns found; proceeding without guidance"
- Qwen distillation timeout: Log and exit (don't hang)
- Malformed response from /remember: Log and continue (202 is expected)

**Output format:**
- Print human-readable summary to stdout
- Optional JSON output (--json flag) for scripting

### seed_kb.py Implementation Details

**Pattern generation strategy:**

Use a fixed seed (or allow --seed for reproducibility) so judges see the same data across runs:

```python
import random
random.seed(12345)

# Generate Gold patterns (high confidence)
for i in range(5):
    pattern = {
        "context": GOLD_PATTERNS[i]["context"],
        "what_worked": GOLD_PATTERNS[i]["what_worked"],
        "what_failed": GOLD_PATTERNS[i]["what_failed"],
        "tags": GOLD_PATTERNS[i]["tags"],
        "confidence": random.uniform(0.85, 0.95),
        "tier": "gold"
    }
    store.save_pattern(pattern)
```

**Data source:**

Define `GOLD_PATTERNS`, `PRODUCTION_PATTERNS`, `EXPERIMENTAL_PATTERNS` as module-level lists of dicts:

```python
GOLD_PATTERNS = [
    {
        "context": "Async I/O concurrency in Python",
        "what_worked": "Use asyncio.Lock for critical sections; hold across full read-modify-write",
        "what_failed": "threading.Lock blocks event loop; avoid in async code",
        "tags": ["python", "async", "concurrency"]
    },
    # ... 4 more
]

PRODUCTION_PATTERNS = [
    # ... 10 patterns
]

EXPERIMENTAL_PATTERNS = [
    # ... 15 patterns
]
```

**Invocation:**

```bash
# Default: populate /app/data/kb
python scripts/seed_kb.py

# Custom path
python scripts/seed_kb.py --kb-dir /tmp/akc_kb

# Overwrite
python scripts/seed_kb.py --kb-dir /tmp/akc_kb --overwrite

# Reproducible seed (same data each run)
python scripts/seed_kb.py --seed 12345
```

**Output example:**

```
AKC Seed Script
===============

Using KB directory: /app/data/kb
Tier distribution: gold=5, production=10, experimental=15

Writing patterns...
  [████████████████████] 30/30 (100%)

Summary:
  Total patterns: 30
  By tier:
    Gold: 5 (17%)
    Production: 10 (33%)
    Experimental: 15 (50%)
  Average confidence: 0.71

Done! Patterns persisted.
```

### README.md Integration

**Location:** Root of repo at `README.md`

**Existing content preservation:**

If README.md already exists (e.g., from starter kit), the Phase 5 update should:
- Preserve any existing "What is this repo?" section
- Replace "How to run" with the new one-liner
- Add "Demo Walkthrough" section
- Update "Architecture" section if it exists

**Key URLs to include:**

- GitHub repo link (once public)
- Hackathon landing page (if applicable)
- Links to REQUIREMENTS.md and ROADMAP.md for judges who want details

**Markdown best practices:**

- Use backticks for code: `` `POST /recall` ``
- Use bold for emphasis: **AKC learns from experience**
- Use code blocks with syntax highlighting:
  ```bash
  curl -X POST http://localhost:8080/recall \
    -H "Content-Type: application/json" \
    -d '{"task_context": "..."}'
  ```
- Use tables for endpoint reference (easier to scan)
- Use GIFs or screenshots if available (show `/health` response)

---

## Common Pitfalls & Mitigations

| Pitfall | Why It Happens | Mitigation |
|---------|---|---|
| Seed data doesn't persist across restart | Script writes to temp dir instead of AKC_KB_DIR | Verify script uses `JsonlStore(settings.akc_kb_dir)` and mounts `-v` in docker run |
| SKILL.md has syntax errors | Written in unfamiliar language or missing error handling | Test locally: `/akc-recall-task-remember --help` should work |
| README is too long for judges to read | Trying to document v2 features and edge cases | Keep to 1 page; link to full docs elsewhere; judges have 10 minutes max |
| Demo takes >30 seconds (skill execution) | Qwen distillation or AgentBase Memory Service timeouts | Add asyncio.timeout(5.0) on external calls; log if timeout hit |
| Patterns don't look realistic | Used placeholder text like "pattern_1", "success" | Use actual domain knowledge: async/await, FastAPI, Docker, etc. |

---

## Testing Phase 5 Before Handoff

### Manual Checklist

1. **SKILL.md:**
   - [ ] `/akc-recall-task-remember --help` shows usage
   - [ ] `/akc-recall-task-remember --task "test" --endpoint http://localhost:8080` completes without error
   - [ ] Output includes: patterns recalled, patterns used, confidence deltas
   - [ ] Execution time < 30 seconds

2. **Seed Data:**
   - [ ] `python scripts/seed_kb.py --kb-dir /tmp/test_kb` creates patterns.jsonl
   - [ ] `curl http://localhost:8080/stats` shows by_tier: {gold: 5, production: 10, experimental: 15}
   - [ ] Kill container; restart with same `/tmp/test_kb` mount; patterns still present
   - [ ] `curl http://localhost:8080/kb/export` shows markdown with all tiers

3. **README:**
   - [ ] Render on GitHub; all headings visible
   - [ ] One-liner docker run command copies cleanly to terminal
   - [ ] All endpoints have example request+response
   - [ ] Architecture section is clear to someone unfamiliar with AKC

4. **Integration:**
   - [ ] Seed script runs before demo; judges see 30 patterns immediately
   - [ ] Skill reads from seeded patterns; uses them in task execution
   - [ ] Task execution succeeds; /remember updates confidence
   - [ ] /stats afterward shows updated avg_confidence (slightly higher)

---

## Dependencies on Phases 1-4

| Phase | Requirement | Phase 5 Usage |
|-------|---|---|
| Phase 1 (Foundation) | JsonlStore, engine, models, /health | Seed script uses JsonlStore; SKILL uses /health to verify service up |
| Phase 2 (Write Path) | POST /remember, Qwen distillation | SKILL calls /remember to update patterns after task |
| Phase 3 (Read Path) | POST /recall, GET /stats, POST /kb/export | SKILL's core loop depends on /recall; README documents all three |
| Phase 4 (Deploy) | Docker container, volume mount, env vars | Seed script and SKILL assume running container with -e and -v flags |

All are used; no Phase 5 work is blocked.

---

## Confidence Assessment

**HIGH confidence** in this research:
- Phases 1-4 are locked (REQUIREMENTS.md is source of truth)
- SKILL.md pattern is straightforward (HTTP client + JSON)
- Seed data design is proven (other systems use similar pre-seeded knowledge bases)
- README structure is standard (GitHub best practice)
- No new external dependencies required (SKILL uses openai SDK or requests; both in requirements.txt)
- No LLM calls in Phase 5 itself (only seed data is synthetic; SKILL calls Qwen indirectly via /remember)

**Remaining uncertainties (acceptable risks):**
- Exact SKILL invocation syntax (depends on Claude Code skill framework) — resolved at implementation
- Qwen distillation latency in Phase 2 affects SKILL execution time — Phase 5 just calls /remember
- AgentBase Memory Service availability for /recall — Phase 3 handles graceful fallback; SKILL will work either way

---

## Metadata

**Research date:** 2026-06-11
**Based on:** REQUIREMENTS.md (v1, 39 reqs), ROADMAP.md (5 phases), Phase 1-4 research + plans
**Confidence level:** HIGH
**Valid until:** 2026-07-11 (Phases 1-4 stable; Phase 5 design depends only on locked interfaces)

**Key dependencies:**
- All v1 requirement IDs (FNDTN, STORE, ENG, RMB, RCL, STATS, EXPORT, DEPLOY, DEMO)
- Phases 1-4 must be complete and functional before Phase 5 begins
- No blocking unknowns; Phase 5 is purely integration + documentation

