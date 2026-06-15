# Tier Semantics

AKC promotes patterns across 3 tiers based on outcome confidence. Tiers tell you **how much to trust a pattern**.

## Tier ladder

```
experimental → production → gold
   0-50%        50-85%       85%+
```

**Confidence** = Beta-distribution posterior over success outcomes. Each `/remember success: true` bumps it up; `success: false` bumps it down.

### `experimental` (0-50% confidence)

- Newly seeded or recently demoted patterns
- Sparse evidence — maybe 1-2 outcomes recorded
- **Use as hypothesis** — try the approach, but expect to learn
- Cite cautiously: "Pattern X (experimental) suggests Y — we should validate"

### `production` (50-85% confidence)

- Proven across several outcomes (5-15 applications typical)
- Reliable for the contexts where it was tested
- **Default safe choice** for most tasks
- Cite confidently: "Per pattern X, use approach Y"

### `gold` (85%+ confidence)

- Battle-tested across many outcomes (10+ applications)
- Robust across edge cases observed
- **Cite as authoritative** — but still note context
- Example: "Pattern `d25f02b1` (gold, 0.91 confidence, applied 11×): kanji compounds outperform romaji 3-5×"

## How tier affects `/recall`

Set `min_tier` to filter:

```json
{ "min_tier": "production" }   // returns production + gold (default)
{ "min_tier": "gold" }          // returns gold only (high-confidence only)
{ "min_tier": "experimental" }  // returns everything (exploratory)
```

**Recommended defaults**:
- Production tasks (real launches, prod migrations): `"min_tier": "production"`
- Exploratory work, brainstorming: `"min_tier": "experimental"`
- Pitch slides, customer-facing claims: `"min_tier": "gold"` (avoid weak evidence)

## Promotion / demotion rules

Patterns move based on `/remember` outcomes:

| Event | Effect |
|---|---|
| `success: true` | Confidence += proportional bump (Bayesian update) |
| `success: false` | Confidence -= proportional bump |
| Cross 85% threshold up | Promoted to `gold` (visible in `recently_promoted` in /stats) |
| Cross 50% threshold up | Promoted to `production` |
| Cross 50% threshold down | Demoted to `experimental` |
| Cross 85% threshold down | Demoted to `production` |

**Implication**: agents that report honest outcomes (including failures) keep the catalog calibrated. Cheating with `success: true` when task actually failed → catalog degrades, future planning suffers.

## Reading patterns

Each pattern returned by `/recall` has:

```json
{
  "id": "d25f02b1-52dd-4a23-a8de-070e0fd8a74c",
  "what_worked": "Specific approach that delivered the result",
  "what_failed": "Approach that was tried and failed — avoid this",
  "confidence": 0.91,
  "tier": "gold",
  "times_applied": 11,
  "tags": ["aso", "keyword", "jp", "app-store"],
  "last_updated": "2026-06-15T04:26:10.546036Z",
  "relevance_score": 0.6714
}
```

**Read `what_failed` FIRST** — avoiding known failures is higher signal than reusing successes. Many failures share root causes; many successes are context-dependent.

`relevance_score` = how well tags matched current task. Use to rank, not as truth.

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Cite `experimental` patterns as authoritative | Note tier in citation: "(experimental — needs validation)" |
| Skip `what_failed` field | Read both `what_worked` AND `what_failed` |
| `min_tier: "gold"` for cold-start tasks | `"production"` default, narrow only when confident |
| Report `success: true` automatically | Wait for user confirmation before optimistic reporting |
