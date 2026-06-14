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

ASO_PATTERNS = [
    {
        "context": "Localized keyword research for Japan iOS launch — choosing between romaji and kanji search terms",
        "what_worked": "Pull top-50 keywords via Sensor Tower JP store filter; prioritize kanji compound terms (e.g. 放置RPG) over romaji equivalents — kanji terms show 3-5x higher search volume and lower KD for mid-tier titles",
        "what_failed": "Copying EN keyword list through Google Translate produces unnatural romaji that JP users never type; machine-translated title keywords scored near-zero impressions in first two weeks post-launch",
        "tags": ["aso", "keyword", "jp", "app-store"],
    },
    {
        "context": "Play Store 30-character title cap enforcement — KR market title keyword stuffing",
        "what_worked": "Front-load the highest-volume KR keyword in characters 1-10 of the title (Play Store weights title start); use Short Description (80 chars) to absorb secondary keywords; verified 18% organic impression lift in KR after reorder",
        "what_failed": "Exceeding 30-char title cap causes Play Console to silently truncate; stuffing brand name + genre + hook into title pushed primary keyword past character 15 and dropped ranking for that term by 12 positions",
        "tags": ["aso", "keyword", "kr", "play-store"],
    },
    {
        "context": "Icon A/B test setup on App Store Connect Product Page Optimization for VN casual game",
        "what_worked": "Run 3-variant PPO test (default + 2 treatments) for 90-day window; isolate one variable per test (color scheme vs. character prominence); VN test showed character-forward icon with warm palette lifted CVR impression→install by 14% vs. abstract icon",
        "what_failed": "Testing icon + screenshot simultaneously makes attribution impossible; stopping PPO test before 90 days (at 60%) gave statistically inconclusive results that led to premature winner declaration",
        "tags": ["aso", "creative", "vn", "app-store"],
    },
    {
        "context": "Screenshot ordering strategy for strategy games launching in JP App Store",
        "what_worked": "Place the highest-tension gameplay screenshot (battle/resource crisis moment) as frame 1; second frame shows progression milestone (castle upgrade); JP users respond strongly to depth signals — this sequence drove 11% higher tap-through on search results",
        "what_failed": "Leading with tutorial or onboarding screenshot killed CTR in JP — players perceived it as casual/simple; using render art instead of real gameplay in frame 1 increased install intent but raised 1-star reviews citing bait-and-switch",
        "tags": ["aso", "creative", "jp", "app-store"],
    },
    {
        "context": "Rating prompt timing calibration to maximize 5-star conversion for mobile RPG",
        "what_worked": "Trigger SKStoreReviewRequest / in-app review prompt at first successful guild join or level 10 clear — moment of dopamine peak; measured 4.6 average rating vs. 3.9 baseline when prompt fired at app open session 3",
        "what_failed": "Prompting at session 2 before player invests (< 10 min playtime) yields low response rate and disproportionate negative reviews from churned users; firing on every cold launch violates App Store guidelines and risks prompt suppression",
        "tags": ["aso", "conversion", "app-store"],
    },
    {
        "context": "Localized store listing copy for KR Play Store — avoiding machine-translation pitfalls in description",
        "what_worked": "Hire native KR copywriter with gaming background; use honorific register (합쇼체) for feature bullets; seed description with 5-6 naturally occurring high-volume KR keywords confirmed via data.ai keyword tool — achieved top-10 rank for 3 target terms within 60 days",
        "what_failed": "DeepL + light human review produced grammatically correct but tonally flat Korean that tested poorly with focus group (felt corporate/foreign); keyword density from direct translation rarely matches KR search behavior patterns",
        "tags": ["aso", "localization", "kr", "play-store"],
    },
    {
        "context": "Apple editorial featured placement submission for VN App Store — timing and asset requirements",
        "what_worked": "Submit via App Store Connect editorial form 8 weeks before target feature date; include 1920x1080 artwork (no text overlay) + localized pitch deck citing VN DAU growth; tie submission to national holiday window (Tết) for editorial relevance",
        "what_failed": "Submitting 2 weeks before launch window is too late for editorial review cycle; using global hero art without VN localization signals low market investment and reduces editorial pick probability",
        "tags": ["aso", "creative", "vn", "app-store"],
    },
    {
        "context": "Release cadence impact on Play Store ranking algorithm — update frequency vs. ranking stability",
        "what_worked": "Ship minor updates (bug fix + small content drop) every 3-4 weeks to maintain freshness signal; major content updates timed to within 2 weeks of seasonal peak (Golden Week JP, Lunar New Year KR/VN) to capture surge traffic at high ranking velocity",
        "what_failed": "Releasing major updates daily during first 30 days suppressed ranking due to repeated re-indexing; going 8+ weeks without any update caused progressive ranking decay of 15-20 positions for mid-volume keywords",
        "tags": ["aso", "release", "play-store"],
    },
    {
        "context": "Competitor reverse-engineering via Sensor Tower for JP casual market — pre-launch keyword gap analysis",
        "what_worked": "Pull top-5 competitor keyword lists in Sensor Tower JP App Intelligence; identify keywords where competitors rank 6-20 (contestable) with >10K monthly searches; build title + subtitle + keyword field around these gaps — captured 4 first-page ranks on launch day",
        "what_failed": "Targeting keywords where top competitor ranks 1-3 with 500K+ downloads is near-impossible for new titles; Sensor Tower volume estimates for JP are ±30% — validate against App Annie (data.ai) before committing to keyword strategy",
        "tags": ["aso", "keyword", "jp", "app-store"],
    },
    {
        "context": "Tier-1 country soft-launch sequencing to optimize KR and JP full launch conversion data",
        "what_worked": "Soft-launch in TH/PH (culturally adjacent, lower CPI) for 6 weeks to collect D1/D7 retention benchmarks; use Play Console country targeting to gate KR/JP; fix conversion funnel issues surfaced in soft-launch before entering KR/JP where CPI is 4-6x higher",
        "what_failed": "Soft-launching directly in KR without prior data led to $8 CPI with 18% D1 retention — below breakeven; skipping soft-launch entirely and going global day-one exposed poor onboarding to JP store algorithm before optimization window closed",
        "tags": ["aso", "conversion", "kr", "jp", "play-store"],
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

    # ASO tier assignment by index — HERO (JP keyword, idx 0) intentionally placed in
    # production so Scene 2 of demo can promote it to gold via a single /remember success.
    # Stable universal rules (rating prompt timing, release cadence) go to gold.
    gold_aso = [ASO_PATTERNS[4], ASO_PATTERNS[7]]                    # rating timing + release cadence
    production_aso = [ASO_PATTERNS[0], ASO_PATTERNS[1], ASO_PATTERNS[2], ASO_PATTERNS[3]]  # JP kw (HERO) + KR title + VN icon + JP screenshot
    experimental_aso = [ASO_PATTERNS[5], ASO_PATTERNS[6], ASO_PATTERNS[8], ASO_PATTERNS[9]]

    gold_sources = gold_aso + GOLD_PATTERNS
    production_sources = production_aso + PRODUCTION_PATTERNS
    experimental_sources = experimental_aso + EXPERIMENTAL_PATTERNS

    for i in range(tier_mix.get("gold", 5)):
        base = gold_sources[i % len(gold_sources)]
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
        base = production_sources[i % len(production_sources)]
        # Demo-pin: HERO (JP keyword, first production slot) at 0.76 — Scene 1's
        # /remember bumps it to 0.81 (still production), Scene 2's /remember bumps
        # to 0.86 → crosses Gold threshold cinematically in Scene 2 only.
        confidence = 0.76 if i == 0 else round(random.uniform(0.70, 0.84), 4)
        pattern = {
            **base,
            "confidence": confidence,
            "tier": "production",
            "consecutive_failures": 0,
            "times_applied": random.randint(2, 10),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        patterns.append(pattern)

    for i in range(tier_mix.get("experimental", 15)):
        base = experimental_sources[i % len(experimental_sources)]
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
