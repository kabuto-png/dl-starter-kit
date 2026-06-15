# Examples — Good vs Bad

Concrete `task_context` and payload samples. Read before drafting your first AKC call.

## `task_context` — good vs bad

### ✅ Good (concrete + specific)

```
"Plan week-1 keyword strategy for casual game launching in Japan App Store"
"Debug intermittent 500 error in /api/v1/signup endpoint, fails ~5% of requests"
"Migrate users table id from int auto-increment to uuid v4, online migration with zero downtime"
"Optimize Next.js product list page TTFB from 1.2s to under 300ms"
"Set up GitHub Actions to push Docker image to AWS ECR on tag release"
```

Why good:
- One sentence
- Names the domain + the specific outcome
- Concrete enough that AKC can match relevant patterns

### ❌ Bad (too vague / too long / wrong frame)

```
"fix"                           ← too vague, useless for matching
"task"                          ← what task?
"help me code"                  ← what code?
"Plan keyword strategy for app launch and screenshot design and pricing strategy and release timing and all other things needed for a successful launch in multiple countries"   ← too long, conflates many tasks
```

Why bad:
- No domain anchor
- Either no signal or too many signals
- AKC's tag matching can't distinguish from N other similar requests

---

## `tags` — good vs bad

### ✅ Good

```json
["aso", "jp", "casual", "keyword"]
["backend", "python", "fastapi", "debugging"]
["db", "postgres", "migration", "zero-downtime"]
["frontend", "nextjs", "react", "performance"]
```

3-5 tags. Domain + tech + scope. Lowercase kebab-case.

### ❌ Bad

```json
["code"]                          // 1 tag, too broad
["fix-bug-asap"]                  // CamelCase + urgency, both wrong
["python","py","python3"]         // synonyms, redundant
["urgent","important","help"]     // meta tags, no substance
["aso","app-store-optimization"]  // duplicate concept
```

---

## Full `/recall` request — good

```bash
curl -sf -X POST "$AKC/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "Plan week-1 keyword strategy for casual game in Japan App Store",
    "tags": ["aso", "jp", "casual", "keyword"],
    "top_k": 5,
    "min_tier": "production"
  }'
```

---

## Full `/remember` request — good (success)

```bash
curl -sf -X POST "$AKC/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "Plan week-1 keyword strategy for casual game in Japan App Store",
    "outcome": "Generated 12-keyword plan emphasizing kanji compounds, user approved",
    "what_happened": "Recalled HERO d25f02b1 (kanji vs romaji, gold). Applied to casual game context: pulled top-50 keywords via Sensor Tower JP filter, prioritized kanji compound terms (放置, パズル). Generated keyword string under 100 chars. User confirmed plan addresses week-1 ranking goal.",
    "patterns_used": ["d25f02b1-52dd-4a23-a8de-070e0fd8a74c", "e91d8ec1-c8cf-4b2d-bf29-7c7a8ba970cc"],
    "success": true,
    "tags": ["aso", "jp", "casual", "keyword", "kanji-compounds"]
  }'
```

Notice:
- Full UUIDs in `patterns_used` (not shortened)
- `what_happened` explains **steps + reasoning + evidence**
- Tags include 1-2 result-specific tags (`kanji-compounds`) beyond recall tags
- `success: true` because user CONFIRMED

---

## Full `/remember` request — good (failure)

```bash
curl -sf -X POST "$AKC/remember" \
  -H "Content-Type: application/json" \
  -d '{
    "task_context": "Plan week-1 keyword strategy for hyper-casual game in Mongolia",
    "outcome": "Could not generate informed plan — no MN patterns in AKC",
    "what_happened": "Recall returned patterns:[] for tags [aso,mn,hyper-casual,keyword]. Fell back to general ASO best practices (Sensor Tower MN store, baseline localization). User acknowledged this is exploratory territory and will iterate based on week-1 data.",
    "patterns_used": [],
    "success": false,
    "tags": ["aso", "mn", "hyper-casual", "keyword", "cold-start"]
  }'
```

Why good:
- `success: false` is honest — no pattern guided this
- Empty `patterns_used` array (not made up IDs)
- Adds `cold-start` tag so future MN tasks find this entry
- Records the GAP so future seeds can fill it

---

## Bad `/remember` examples — DON'T

```bash
# ❌ Hallucinated pattern ID
"patterns_used": ["fake-id-i-made-up"]

# ❌ Premature success
"success": true,
"what_happened": "I generated a plan, user hasn't tested yet"

# ❌ Empty what_happened
"what_happened": "did task"

# ❌ Reused task_context that doesn't match what actually happened
"task_context": "JP launch plan",
"what_happened": "Actually I helped them with KR launch instead"
```

---

## Tip: match `task_context` between `/recall` and `/remember`

The `/remember` `task_context` MUST be a close match to the `/recall` `task_context`. AKC uses this string to build the pattern's identity over time.

```
✓ Recall:    "Plan week-1 keyword strategy for casual game in Japan App Store"
  Remember: "Plan week-1 keyword strategy for casual game in Japan App Store"
            (or close paraphrase)

✗ Recall:    "Plan JP launch"
  Remember: "Helped with Korean app store stuff"
            ← unrelated, AKC can't link evidence to the pattern
```
