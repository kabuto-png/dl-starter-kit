# Writing Good Outcomes for AKC `/remember`

The quality of patterns stored in AKC depends on how callers describe outcomes. Generic descriptions produce generic patterns; specific descriptions produce actionable patterns.

This guide shows 5 GOOD examples and 5 BAD examples drawn from real VNG Publishing use cases.

---

## What makes an outcome description good?

1. **Specific causal claim** — "X worked because Y" (not "X went well")
2. **Quantified result** where possible — "CTR lifted 14%" (not "improved")
3. **Counterfactual context** — "vs Y which failed" or "after rolling back Z"
4. **Action artifacts** — name specific tools, files, commands, parameters
5. **Honest failure mode** — `what_failed` is not always empty even on success

---

## 5 GOOD examples

### Example 1: ASO Keyword Strategy (JP launch)

**Outcome description:**
```
task_context: "Launching game in Japan. Need primary keyword strategy for Play Console."

what_happened: "Tested 2 approaches: (1) katakana keywords (ゲーム, パズル) vs (2) romaji long-tail (pazu-ru ge-mu). 
Monitored via Sensor Tower top-50 rankings over 48h. Katakana (primary) + romaji (secondary, long-tail) split strategy 
landed 3 keywords on first page (position 8-15), CTR 2.3% vs baseline 0.8%. Romaji alone underperformed (rank 20+). 
Kanji avoided (low search volume for this category)."

outcome: "success"
what_worked: "Katagana-first with romaji long-tail secondary. Katagana grabs brand intent; romaji captures discovery."
what_failed: "Pure romaji underperformed (position 20+). Pure kanji impossible (studio name too specific)."
tags: ["aso", "japan", "keyword-strategy", "play-console"]
```

Why good: Specific tools (Sensor Tower), measurable result (CTR 2.3%), counterfactual (vs romaji alone), action (split strategy). AKC will distill a high-quality pattern about JP keyword localization.

---

### Example 2: Creative A/B Test (KR icon design)

**Outcome description:**
```
task_context: "KR market launch. App icon designs: option A (bold red, character face) vs option B (minimalist blue)."

what_happened: "A/B tested via Google Play store 24h, 10K impressions split. 
Option A: 1,240 installs, CTR 12.4% (conversion from browse to install). 
Option B: 890 installs, CTR 8.9%. 
Difference significant (chi-square p<0.01). A won on impulse appeal (characters resonate in KR). 
B failed on discoverability (minimal icon didn't stand out vs 3 competing titles in search results)."

outcome: "success"
what_worked: "Character-forward icon design for KR market. Bold primary color (red/orange) outperforms muted. Emotional hook > minimalism."
what_failed: "Minimalist blue approach underperformed (8.9% CTR vs 12.4%). Blends with competitor thumbnails."
tags: ["aso", "korea", "creative-testing", "icon-design", "a-b-test"]
```

Why good: Quantified results (CTR %, installs, p-value), specific design parameters (character, bold red), counterfactual, A/B methodology named. Pattern will be production-tier immediately.

---

### Example 3: Soft Launch Sequencing (TH market)

**Outcome description:**
```
task_context: "Thailand soft launch planning. Timing and regional scope options for week 1."

what_happened: "Sequenced launch in 3 phases: 
  Phase 1 (48h, Bangkok metro only): 1,200 installs, feedback = 'game too hard'; crash rate 3.2%. 
  Phase 2 (72h, add Chiang Mai): expanded to 4,800 cumulative, difficulty patches applied, crash to 0.8%. 
  Phase 3 (4d, all TH): 18K cumulative. Soft launch metrics stable.
Lesson: hard stop after phase 1 to patch, then expand. Jumping to national launch day 1 would have shipped with crash bug."

outcome: "success"
what_worked: "Metro-first soft launch with 48-72h gates per region. Catch quality issues before scale."
what_failed: "National day-1 approach (rejected plan) would have shipped 3.2% crash rate to all TH (estimated 50K+ users)."
tags: ["aso", "thailand", "soft-launch", "quality-gates", "rollout-strategy"]
```

Why good: Specific phases with timelines, counterfactual (what NOT to do), measurable quality gate (crash rate 3.2% → 0.8%), action (patches applied between phases).

---

### Example 4: Competitive Intelligence (VN market)

**Outcome description:**
```
task_context: "VN launch. Researching top 3 competitor strategies to differentiate."

what_happened: "Reverse-engineered 3 competitors via App Annie (now Sensor Tower): top 100 keywords, review mining, ASO trends.
  Competitor A: focused on casual-game keywords (boa ga, choi game). Rating 4.2, 50K reviews.
  Competitor B: long-tail streaming keywords (xem phim, choi online). Rating 3.8, 120K reviews.
  Our app positioned as 'cooperative party game' — none of top 3 own that keyword cluster.
Applied strategy: primary keyword 'tro choi hop tac' (cooperative game), secondary 'choi online voi ban be' (play online with friends).
First week: rank 12 on 'tro choi hop tac', rank 5 on secondary. 1.8K installs from organic."

outcome: "success"
what_worked: "Position in white-space keyword cluster where competitors don't compete. Cooperative-game keywords underserved."
what_failed: "Chasing competitor A's 'casual game' keywords would have ranked position 40+ (over-saturated)."
tags: ["aso", "vietnam", "competitive-intelligence", "keyword-gap-analysis", "market-positioning"]
```

Why good: Named specific competitors, specific keyword analysis, metric (rank 12, 1.8K organic), counterfactual.

---

### Example 5: Localization Testing (Multi-geo)

**Outcome description:**
```
task_context: "All geo launches (JP/KR/TH/VN/PH). Store listing localization: template vs per-geo custom."

what_happened: "Tested 2 approaches: 
  Template approach (same subtitle translated, minimal customization): JP 11% CTR, KR 9.8%, TH 7.2%.
  Custom per-geo (localized tone, cultural references, local influencer mention where applicable):
  JP 11% (no cultural ref needed, template worked), KR 13.2% (K-pop reference resonated), TH 10.1% (TikTok trend mention).
  Cost: custom = 3 hours per geo vs template 30 min per geo.
  ROI: +3.4% KR (350 extra installs/day x 30 days x higher LTV) justified 2.5 extra hours for that geo."

outcome: "success"
what_worked: "Selective per-geo customization (prioritize high-upside markets like KR). Template sufficient for mature geos (JP)."
what_failed: "Full template (same translations) left 3.4% CTR on table in KR. Full custom (all 5 geos) cost > benefit for geos with template adequacy."
tags: ["aso", "localization", "multi-geo", "cultural-adaptation", "cost-benefit"]
```

Why good: Compared two approaches with metrics per geo, ROI calculation, selective recommendation (JP vs KR difference). Pattern captures nuance.

---

## 5 BAD examples

### Bad Example 1: Too vague

**Outcome description:**
```
task_context: "KR launch"
what_happened: "The keyword strategy worked well. Good engagement."
outcome: "success"
what_worked: "Keyword strategy"
```

**Why bad**: No specifics. What keywords? Engagement = CTR or installs? Which approach vs what baseline? No causal claim. Distilled pattern would be near-empty.

---

### Bad Example 2: Marketing language (no substance)

**Outcome description:**
```
task_context: "Game launch planning"
what_happened: "Successfully delivered a high-impact user acquisition strategy that drove significant engagement."
outcome: "success"
what_worked: "Strategic targeting and optimization"
what_failed: ""
```

**Why bad**: Pure jargon. Zero technical content. "High-impact", "significant", "strategic optimization" are empty. AKC distiller will struggle to extract actionable content.

---

### Bad Example 3: Raw error log (no reflection)

**Outcome description:**
```
task_context: "Debug keyword ranking issue"
what_happened: "
Error: ValueError at line 156 of keyword_analyzer.py
Traceback:
  File 'keyword_analyzer.py', line 156, in extract_keywords
    top_keywords = sorted_list[0:50]
IndexError: list index out of range
Fixed by checking list length.
"
outcome: "success"
what_worked: "Fixed bug"
```

**Why bad**: Raw error dump, no context about WHY the list was empty (query returned 0 results? API timeout?), what guard was added. Pattern distilled will be "check list length before access" — true but meaningless without the context (when should you check?).

---

### Bad Example 4: Missing failure context

**Outcome description:**
```
task_context: "TH launch"
what_happened: "Executed soft launch"
outcome: "success"
what_worked: ""
```

**Why bad**: Even on success, WHY did it succeed? Empty `what_worked` means AKC has no learning signal. Pattern will be demotion-tier (experimental at best).

---

### Bad Example 5: Conflated patterns (multi-task)

**Outcome description:**
```
task_context: "Game launch execution"
what_happened: "Refactored ASO tracking code, tested 5 keyword variants, updated app store listing, fixed crash in login flow, deployed to staging."
outcome: "success"
what_worked: "Comprehensive launch prep"
```

**Why bad**: 5 different tasks crammed into one outcome. AKC will distill a confused multi-pattern. Should split into 5 `/remember` calls:
1. Refactored ASO tracking (code change)
2. Keyword variants testing (A/B test result)
3. Store listing update (content change)
4. Login crash fix (bug fix)
5. Staging deploy (deployment process)

Each deserves its own pattern with specific context.

---

## Quick checklist

Before calling `/remember`, ask:

- [ ] Is `task_context` one sentence describing what I tried to do?
- [ ] Does `what_happened` (or `outcome`) name specific tools (Sensor Tower, Play Console), numbers (CTR %, rank position, install count), or parameters?
- [ ] Did I include WHY it worked / WHY it failed, not just THAT it did?
- [ ] Is this a SINGLE pattern, or should I split into multiple `/remember` calls?
- [ ] Are `tags` lowercase and specific to the domain (not "good", not "launch")?

---

## How AKC handles bad outcomes

- LLM distillation on vague outcome → experimental tier (low initial confidence, low surface area)
- If pattern surfaces in `/recall` and fails 3+ times → demoted automatically
- Hash dedup prevents identical-content patterns from accumulating duplicate "successes"
- `/kb/export` shows current Gold + Production patterns for periodic human review — catch low-quality patterns early
- Caller can manually `/remember` with `success: false` to correct a bad pattern (demotion accelerator)

---

**Good outcome descriptions = high-confidence patterns = helpful AKC.**
