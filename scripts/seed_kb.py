import argparse
import random
import sys
from pathlib import Path
from datetime import datetime, timezone


GOLD_PATTERNS = [
    {
        "context": "Implement async I/O with asyncio in Python",
        "what_worked": "Use asyncio.Lock for thread-safe concurrent access to shared state; always hold lock across full read-modify-write cycle",
        "what_failed": "Using threading.Lock blocks the event loop; try Lock-free designs for very high concurrency",
        "tags": ["python", "async", "concurrency"],
    },
    {
        "context": "Handle FastAPI startup dependencies",
        "what_worked": "Use Depends() for pydantic BaseSettings validation; fail-fast on missing env vars at startup with ValidationError",
        "what_failed": "Lazy env validation fails silently at runtime; do not catch ValidationError in a bare except",
        "tags": ["fastapi", "python", "configuration"],
    },
    {
        "context": "Write atomic file updates in Python",
        "what_worked": "Write to tempfile then os.replace() for crash safety; tempfile on same filesystem as target to avoid cross-device rename",
        "what_failed": "Direct write truncates file on crash; os.rename() fails across filesystems with OSError",
        "tags": ["python", "storage", "crash-safety"],
    },
    {
        "context": "Run background tasks in FastAPI without blocking the response",
        "what_worked": "Use BackgroundTasks.add_task(); wrap task body in try/except Exception with logger.error() to prevent silent failures",
        "what_failed": "Returning from route before task completes silently drops errors; never use asyncio.create_task() without attaching a done callback",
        "tags": ["fastapi", "python", "async"],
    },
    {
        "context": "Parse JSON from LLM output defensively",
        "what_worked": "Strip <think> tokens before json.loads(); check finish_reason == length before parsing; use response_format json_object",
        "what_failed": "Truncated LLM output causes json.JSONDecodeError; thinking tokens break json.loads silently if not stripped",
        "tags": ["llm", "python", "json"],
    },
]

PRODUCTION_PATTERNS = [
    {
        "context": "Deploy Docker containers with persistent state",
        "what_worked": "Mount VOLUME in Dockerfile; use env var for KB path; log mount point at startup for verification",
        "what_failed": "Assuming default paths survive restart; always parameterize storage paths",
        "tags": ["docker", "deployment"],
    },
    {
        "context": "Rank search results by confidence score",
        "what_worked": "Sort descending by confidence field; filter demoted tier before sorting to avoid noise",
        "what_failed": "Including demoted patterns inflates result set; rank by last_updated alone misses high-confidence old patterns",
        "tags": ["search", "ranking"],
    },
    {
        "context": "Implement append-only JSONL storage",
        "what_worked": "Dedup on read using dict[id -> record]; append on write with newline; never overwrite existing lines",
        "what_failed": "In-place JSON edit risks corruption on crash; JSONL dedup must happen at read time not write time",
        "tags": ["storage", "jsonl"],
    },
    {
        "context": "Validate pydantic models from JSON strings",
        "what_worked": "Use model_validate_json() for pydantic v2; call .model_dump() for dicts and pydantic serializers for JSON -- both handle datetime/UUID correctly",
        "what_failed": "json.loads() + Model(**dict) skips pydantic v2 validators; .dict() is removed in pydantic v2",
        "tags": ["python", "pydantic"],
    },
    {
        "context": "Set timeout on async external service calls",
        "what_worked": "Wrap with asyncio.timeout(2.0); catch TimeoutError and fall back to local implementation",
        "what_failed": "Missing timeout hangs the request indefinitely on service unavailability; broad try/except hides real errors",
        "tags": ["python", "async", "reliability"],
    },
    {
        "context": "Structure FastAPI routes with clear error responses",
        "what_worked": "Return structured {error, code} dicts for all 4xx/5xx; use HTTPException with detail dict not string",
        "what_failed": "Bare FastAPI 422 responses expose internal field names; string detail fields are not machine-parseable",
        "tags": ["fastapi", "api-design"],
    },
    {
        "context": "Handle OpenAI-compatible LLM API responses",
        "what_worked": "Use openai SDK directly; check finish_reason before reading content; disable thinking with extra_body parameter",
        "what_failed": "LangChain abstraction adds latency and hides finish_reason; thinking tokens appear in output if not disabled",
        "tags": ["llm", "openai", "python"],
    },
    {
        "context": "Build CLI tools with argparse",
        "what_worked": "Use required=True for mandatory args; provide sensible defaults for optional args; include --help text",
        "what_failed": "Positional-only args break when invoked from scripts; missing defaults cause cryptic error messages",
        "tags": ["python", "cli"],
    },
    {
        "context": "Log structured data in Python services",
        "what_worked": "Use logger.error() with extra={} dict for structured fields; never swallow exceptions silently",
        "what_failed": "print() statements disappear in production; bare except blocks hide stack traces",
        "tags": ["python", "logging"],
    },
    {
        "context": "Test async Python code",
        "what_worked": "Use pytest-asyncio with asyncio_mode=auto; create fresh event loops per test to avoid state leakage",
        "what_failed": "Reusing event loop across tests causes order-dependent failures; sync test functions silently pass without running async code",
        "tags": ["python", "testing", "async"],
    },
]

EXPERIMENTAL_PATTERNS = [
    {
        "context": "Implement semantic search with vector embeddings",
        "what_worked": "Use cosine similarity on normalized embeddings; cache embeddings for frequently-queried documents",
        "what_failed": "Euclidean distance on unnormalized vectors gives wrong similarity; recomputing embeddings per query is too slow",
        "tags": ["search", "embeddings", "ml"],
    },
    {
        "context": "Run multiple async tasks with gather",
        "what_worked": "Use asyncio.gather(*tasks, return_exceptions=True) to avoid one failure cancelling others",
        "what_failed": "asyncio.gather without return_exceptions raises on first failure and cancels remaining tasks",
        "tags": ["python", "async"],
    },
    {
        "context": "Build Dockerfile for Python services",
        "what_worked": "Use python:3.11-slim base; run as non-root USER; set WORKDIR /app; copy requirements before code for layer caching",
        "what_failed": "Running as root fails on restricted cluster policies; copying all files before requirements defeats layer cache",
        "tags": ["docker", "deployment"],
    },
    {
        "context": "Cache HTTP responses in Python",
        "what_worked": "Use functools.lru_cache for deterministic inputs; set maxsize to bound memory usage",
        "what_failed": "Caching mutable arguments causes stale data; unbounded cache grows until OOM",
        "tags": ["python", "caching"],
    },
    {
        "context": "Parse command-line arguments from Claude Code skills",
        "what_worked": "Use argparse with sys.argv[1:]; provide --help; exit 1 on parse error with clear message",
        "what_failed": "Manual string splitting misses quoted arguments; sys.exit(0) after --help is expected behavior not an error",
        "tags": ["python", "cli", "skills"],
    },
    {
        "context": "Handle datetime serialization in pydantic",
        "what_worked": "Use datetime with timezone.utc default; pydantic v2 serializes to ISO 8601 automatically",
        "what_failed": "Naive datetime objects serialize without timezone; comparing tz-aware and tz-naive datetimes raises TypeError",
        "tags": ["python", "pydantic", "datetime"],
    },
    {
        "context": "Write idempotent seed scripts",
        "what_worked": "Check if output file exists before writing; require explicit --overwrite flag to replace; use a deterministic RNG seed for reproducibility",
        "what_failed": "Silent overwrite destroys existing data; non-deterministic seeds make debugging harder",
        "tags": ["python", "data", "scripts"],
    },
    {
        "context": "Implement retry logic for flaky services",
        "what_worked": "Exponential backoff with jitter; max 3 retries; log each attempt with attempt number",
        "what_failed": "Fixed sleep between retries thundering-herds on service recovery; unlimited retries hang indefinitely",
        "tags": ["python", "reliability"],
    },
    {
        "context": "Use environment variables in Docker containers",
        "what_worked": "Read via os.environ.get() with explicit defaults; fail-fast on missing required vars at startup",
        "what_failed": "Missing env var raises KeyError at first use, not startup; silent None default causes downstream failures",
        "tags": ["docker", "configuration"],
    },
    {
        "context": "Structure Python packages with __init__.py",
        "what_worked": "Place __init__.py in each package directory; use relative imports within package; expose public API from top-level __init__",
        "what_failed": "Missing __init__.py makes directory unimportable; absolute imports break when package is moved",
        "tags": ["python", "packaging"],
    },
    {
        "context": "Profile async Python services under load",
        "what_worked": "Use py-spy for sampling profiler; identify blocking calls in async code with asyncio debug mode",
        "what_failed": "cProfile blocks event loop; identifying sync-in-async bottlenecks requires asyncio.get_event_loop().set_debug(True)",
        "tags": ["python", "async", "performance"],
    },
    {
        "context": "Write integration tests for FastAPI endpoints",
        "what_worked": "Use httpx.AsyncClient with ASGITransport; parametrize test cases; assert status codes before body",
        "what_failed": "Using requests against live server requires server startup; skipping status code assertion hides routing errors",
        "tags": ["fastapi", "testing", "python"],
    },
    {
        "context": "Handle concurrent writes to shared JSONL file",
        "what_worked": "Use asyncio.Lock(); hold lock for entire read-modify-write cycle; release only after os.replace()",
        "what_failed": "Fine-grained locking (lock per record) allows interleaved writes and corrupts file; releasing before os.replace() loses writes on crash",
        "tags": ["python", "concurrency", "storage"],
    },
    {
        "context": "Expose service health endpoint for orchestration",
        "what_worked": "Return {status: ok, pattern_count: N} from GET /health; check readiness by counting KB patterns at startup",
        "what_failed": "Returning HTTP 200 without body fails orchestrators expecting JSON; empty KB is valid (0 patterns) but must not return error",
        "tags": ["fastapi", "deployment", "api-design"],
    },
    {
        "context": "Generate reproducible synthetic data for demos",
        "what_worked": "Set a fixed RNG seed before any random call; document the seed value in help text; use fixed tier distributions",
        "what_failed": "Unseeded random produces different data each run; judges cannot reproduce demo results; floating-point ranges need min < max check",
        "tags": ["python", "data", "testing"],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-populate AKC knowledge base with realistic patterns for demo"
    )
    parser.add_argument(
        "--kb-dir",
        default="/app/data/kb",
        help="Path to KB directory containing patterns.jsonl (default: /app/data/kb)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing patterns.jsonl if present",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Random seed for reproducibility (default: 12345)",
    )
    parser.add_argument(
        "--tier-mix",
        default="gold:5,production:10,experimental:15",
        help="Tier distribution (default: gold:5,production:10,experimental:15)",
    )
    return parser.parse_args()


def parse_tier_mix(tier_mix_str: str) -> dict[str, int]:
    result = {}
    for part in tier_mix_str.split(","):
        tier, count = part.split(":")
        result[tier.strip()] = int(count.strip())
    return result


def generate_patterns(tier_mix: dict, seed: int) -> list[dict]:
    random.seed(seed)

    patterns = []

    # Source lists: GOLD_PATTERNS (5 entries), PRODUCTION_PATTERNS (10 entries), EXPERIMENTAL_PATTERNS (15 entries)
    for i in range(tier_mix.get("gold", 5)):
        base = GOLD_PATTERNS[i % len(GOLD_PATTERNS)]
        pattern = {
            **base,
            "confidence": round(random.uniform(0.85, 0.95), 4),
            "tier": "gold",
            "consecutive_failures": 0,
            "times_applied": random.randint(5, 20),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        patterns.append(pattern)

    for i in range(tier_mix.get("production", 10)):
        base = PRODUCTION_PATTERNS[i % len(PRODUCTION_PATTERNS)]
        pattern = {
            **base,
            "confidence": round(random.uniform(0.70, 0.84), 4),
            "tier": "production",
            "consecutive_failures": 0,
            "times_applied": random.randint(2, 10),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        patterns.append(pattern)

    for i in range(tier_mix.get("experimental", 15)):
        base = EXPERIMENTAL_PATTERNS[i % len(EXPERIMENTAL_PATTERNS)]
        pattern = {
            **base,
            "confidence": round(random.uniform(0.50, 0.69), 4),
            "tier": "experimental",
            "consecutive_failures": 0,
            "times_applied": random.randint(0, 3),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        patterns.append(pattern)

    return patterns


def seed_kb(kb_dir: str, patterns: list[dict], overwrite: bool) -> None:
    path = Path(kb_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    patterns_file = path / "patterns.jsonl"
    if patterns_file.exists() and not overwrite:
        raise FileExistsError(
            f"patterns.jsonl already exists at {patterns_file}. Use --overwrite to replace."
        )
    if overwrite and patterns_file.exists():
        patterns_file.unlink()
    try:
        with open(str(patterns_file), "a", encoding="utf-8") as f:
            for i, pattern_dict in enumerate(patterns, 1):
                # Validate via Pattern model (catches missing fields)
                from akc.patterns.models import Pattern
                pattern = Pattern(**pattern_dict)
                f.write(pattern.model_dump_json() + "\n")
                if i % 10 == 0 or i == len(patterns):
                    print(f"  [{i:3d}/{len(patterns):3d}] patterns written")
    except OSError as exc:
        if exc.errno == 13:  # Permission denied
            raise PermissionError(f"Cannot write to {patterns_file} — ensure directory is writable") from exc
        raise


def main() -> None:
    args = parse_args()
    tier_mix = parse_tier_mix(args.tier_mix)

    print("AKC Seed Script\n" + "=" * 40)
    print(f"KB Directory: {args.kb_dir}")
    print(f"Tier Mix:     {tier_mix}")
    print(f"Random Seed:  {args.seed}")

    patterns = generate_patterns(tier_mix, args.seed)

    print("Writing patterns...")
    try:
        seed_kb(args.kb_dir, patterns, args.overwrite)
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    by_tier: dict[str, int] = {}
    for p in patterns:
        t = p.get("tier", "experimental")
        by_tier[t] = by_tier.get(t, 0) + 1

    total = len(patterns)
    avg_confidence = sum(p["confidence"] for p in patterns) / total if total > 0 else 0.0

    print("\nSummary:")
    print(f"  Total patterns: {total}")
    for tier_name in ["gold", "production", "experimental", "demoted"]:
        count = by_tier.get(tier_name, 0)
        pct = (count / total * 100) if total > 0 else 0
        print(f"    {tier_name:13s}: {count:3d} ({pct:5.1f}%)")
    print(f"  Average confidence: {avg_confidence:.4f}")
    print("\nDone! Patterns persisted to patterns.jsonl")


if __name__ == "__main__":
    main()
