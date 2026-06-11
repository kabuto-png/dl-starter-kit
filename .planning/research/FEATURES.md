# Feature Landscape: AKC — Agent Knowledge Collective

**Domain:** Self-improving knowledge/memory API for AI agents
**Researched:** 2026-06-11
**Scope:** What features do knowledge retrieval and agent memory services provide, and what does AKC's current design cover vs. gap?

---

## Current AKC Feature Inventory

The 5 endpoints map to these functional roles:

| Endpoint | Role |
|---|---|
| `GET /health` | Platform liveness |
| `POST /recall` | Pattern retrieval before a task |
| `POST /remember` | Outcome ingestion + distillation |
| `GET /stats` | KB health snapshot |
| `POST /kb/export` | Human-readable knowledge export |

---

## Table Stakes

Features judges and users of knowledge retrieval APIs expect to find. Missing = product feels incomplete or untrustworthy.

| Feature | Why Expected | AKC Status | Complexity |
|---|---|---|---|
| **Ranked results with score** | Every retrieval system (Mem0, Cloudflare, Azure AI Search) returns relevance scores alongside results — without them the caller can't decide how much to trust each result | Partially present: `confidence` and `tier` returned, but no per-query semantic similarity score | Low — add `relevance_score` field to recall response |
| **Result count + query latency** | `total_found` and `query_ms` are already in the PRD spec — this is baseline production signaling | Already in spec | Done |
| **Async write with 202 Accepted** | All production memory services decouple write latency from the caller. Fire-and-forget is expected. | Already in spec (`/remember` returns 202 immediately) | Done |
| **Tag/filter scoping** | Metadata filtering is called "non-negotiable for multi-tenant RAG workflows" (mem0 docs). Without it, recall degrades to keyword mush as KB grows | Partially: `tags` array and `min_tier` on request; no date or recency filter | Low — recency filter adds value |
| **Structured error responses** | Every production API returns `{"error": "...", "code": "...", "hint": "..."}` not bare 422s. Mem0 doc explicitly calls this out as a gap in naive implementations | Not specified in PRD | Low — FastAPI exception handler |
| **Idempotent pattern identity** | When the same pattern is submitted twice, similar systems prevent duplicate entries. Without deduplication, KB degrades fast | Mentioned: Qwen distillation should match existing patterns, but no explicit dedup strategy in PRD | Medium — similarity threshold in distill.py |
| **KB size / capacity stats** | Production knowledge stores expose size, growth rate, and tier distribution. `/stats` already covers tier counts and avg confidence | Covered by `/stats` | Done |
| **Versioned or timestamped patterns** | Every pattern storage system (Mem0 ADD-only model, confidence_history.jsonl) preserves temporal context. Callers need to know when a pattern was last updated | Partially: append-only JSONL preserves history, but `last_updated` not shown in recall response | Low — include `last_updated` in pattern object |

---

## Recall Response: What Makes Results Actually Useful

Based on Cloudflare Agent Memory, Azure AI Search agentic retrieval, and mem0, a useful `/recall` response goes beyond returning raw patterns. Judges who are familiar with RAG/memory services will notice these gaps:

**What AKC currently returns (per PRD):**
```json
{
  "id": "pat_042",
  "what_worked": "...",
  "confidence": 0.91,
  "tier": "gold",
  "times_applied": 8
}
```

**What production services return (and what improves usefulness):**

| Field | Present in AKC? | Value to Caller |
|---|---|---|
| `what_worked` | Yes | Core knowledge |
| `what_failed` | Not in recall response (only in storage) | Tells agent what to avoid — high value, trivial to add |
| `confidence` (Bayesian) | Yes | Trust signal |
| `tier` | Yes | Quick trust signal |
| `times_applied` | Yes | Evidence base size |
| `relevance_score` | No | How semantically close this pattern is to THIS query — not the same as confidence |
| `tags` | Not in recall response | Lets caller understand why this surfaced |
| `last_updated` | No | Recency signal — stale patterns are a known failure mode |
| `context` (original context field) | Not in recall response | Tells caller the domain this pattern came from |

**Recommendation:** The recall response should include `what_failed`, `tags`, `last_updated`, and `relevance_score` from the semantic similarity search. All are low effort — the data exists, just not exposed.

---

## Remember Payload: What Callers Need

Based on AWS AgentCore, Cloudflare, and Hindsight memory APIs, a useful `/remember` payload from the caller's perspective:

**AKC current spec:**
```json
{
  "task_context": "...",
  "outcome": "success|failure",
  "what_happened": "...",
  "patterns_used": ["pat_042"],
  "tags": ["python", "api"]
}
```

**Assessment:** This is solid. The key elements are present. What's missing or ambiguous:

| Field | Status | Notes |
|---|---|---|
| `task_context` | Present | What the agent was doing — good |
| `outcome` | Present | Success/failure signal — core to confidence update |
| `what_happened` | Present | Raw text for Qwen distillation — correct |
| `patterns_used` | Present | Enables attribution tracking for those specific patterns |
| `session_id` / `run_id` | Missing | Every production system (AgentCore, Cloudflare, mem0) scopes memories to a session. Enables "what happened in this run" queries later. Low effort to add. |
| `error_detail` | Missing | For failure outcomes, a structured error helps Qwen extract a better `what_failed` field. Currently relies on free-text `what_happened`. |
| `duration_ms` | Missing | Useful for patterns that apply to performance-sensitive tasks. Minor — skip for MVP. |

---

## Differentiators

Features that distinguish AKC from generic memory stores and would score well with hackathon judges evaluating self-improving agents.

| Feature | Value Proposition | AKC Status | Complexity |
|---|---|---|---|
| **Beta distribution confidence model** | Mathematically grounded trust scoring — not an arbitrary ±0.05 heuristic. New patterns are volatile; mature patterns are stable. Judges with ML backgrounds will notice this is real | Fully specified in PRD (Section 9) | Done — implement correctly |
| **Tier system with Gold exit guardrail** | 3 consecutive failures required to demote a Gold pattern — prevents a single bad data point destroying earned knowledge. No other surveyed system has this explicit guardrail | Fully specified | Done — implement correctly |
| **LLM distillation of raw outcomes** | Raw text → structured pattern via Qwen. Comparable systems (Mem0, agentmemory) compress conversational context but don't extract `what_worked`/`what_failed` as distinct fields | Core AKC differentiator — no surveyed system does this exactly | Medium — distill.py quality matters |
| **Demoted-never-auto-promotes guardrail** | Preserves audit trail without ever accidentally re-trusting a discredited pattern | Specified | Done |
| **`/kb/export` as human-readable knowledge** | Bridges AI-native knowledge store to human reviewers. Judges can read the actual accumulated knowledge, not just metrics | Specified | Low |
| **`SKILL.md` Claude Code integration** | The recall→task→remember loop runs automatically via a skill — zero manual API calls from the agent. This is a clean demo story. No surveyed system ships a ready-to-use Claude Code skill | Specified as MVP integration | Low |
| **Confidence progression as visible demo arc** | Demo shows pattern graduating Cold Start → Experimental → Production → Gold. This is a narrative arc that hackathon judges can follow in 3 minutes | Demo script in PRD Section 10 is well-designed | Medium — requires seeded demo data |

---

## /stats: What Observability Judges Expect

Based on mem0, agentmemory, and Braintrust agent observability guide, production memory services expose:

**AKC current `/stats`:**
```json
{
  "total_patterns": 47,
  "by_tier": {"gold": 12, "production": 18, "experimental": 11, "demoted": 6},
  "top_tags": ["python", "debugging", "api"],
  "avg_confidence": 0.74,
  "total_queries": 203,
  "total_outcomes_recorded": 187
}
```

**Assessment:** This is good for a hackathon demo. What would strengthen it:

| Metric | Present? | Value |
|---|---|---|
| Total patterns by tier | Yes | KB health at a glance |
| Avg confidence | Yes | Overall KB quality signal |
| Top tags | Yes | Domain coverage |
| Total queries / outcomes | Yes | Usage proof |
| **Recall hit rate** (queries that returned >= 1 pattern) | No | Shows KB is actually useful, not just storing things |
| **Avg patterns per query** | No | Shows retrieval density |
| **Recently promoted patterns** | No | Makes self-improvement visible — high demo value |
| **KB growth rate** (patterns added per day) | No | Shows active learning — demo value |

**Recommended addition:** Add `recall_hit_rate` (queries returning >=1 result / total queries) and `recently_promoted` (last N patterns that tier-upgraded). These are cheap to compute and make the self-improvement story concrete in the stats endpoint.

---

## Anti-Features

Features to deliberately not build. Includes items already in PRD Out of Scope plus additions based on research.

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| **Authentication / API keys** | Out of scope in PRD. Adding auth in 6 days introduces CORS, token management, and error handling complexity that will distract from the core demo. Hackathon judges don't expect auth. | Accept all requests; document "add auth before production" in README |
| **Hybrid search (BM25 + vector fusion)** | agentmemory builds triple-stream fusion (BM25 + vector + graph). It requires running a local BM25 index alongside embeddings. For AKC's use case, semantic similarity via AgentBase Memory is sufficient. The AKC differentiator is confidence scoring, not retrieval ranking sophistication. | Use AgentBase Memory semantic search; apply tier and tag filtering on top |
| **Memory staleness / TTL expiry** | Some systems auto-expire memories. For AKC, the tier system + Demoted state handles low-confidence patterns. Adding TTL introduces a second deprecation path that conflicts with the confidence narrative. | Demoted tier serves this purpose |
| **Multi-KB routing** | Already in PRD Out of Scope. Would require namespace management, routing logic, and a completely different data model. | Single KB, focus on depth not breadth |
| **Vector re-embedding on update** | When a pattern's text changes (e.g., `what_worked` revised after distillation), some systems re-embed and re-index. For AKC's append-only JSONL model, this would require a full re-index. | Store new pattern version as new record; don't mutate existing entries |
| **Answer synthesis / RAG-over-KB** | Azure AI Search agentic retrieval synthesizes a natural-language answer from retrieved results. For AKC, recall returns structured patterns — the calling agent synthesizes. Adding LLM synthesis to `/recall` adds latency and cost and competes with what the agent does natively. | Return structured patterns; let the calling agent use them as context |
| **Web UI / dashboard** | Already in PRD Out of Scope. Building a frontend in 6 days burns all remaining time on a non-differentiating feature. | `/stats` + `/kb/export` is the "dashboard" for the demo |
| **KB sync between nodes** | Already in PRD Out of Scope. | Single instance; document federation as Phase 2 |
| **Cross-session identity resolution** | mem0 identifies this as one of the hardest unsolved problems in agent memory. Not attempting it in a 6-day hackathon. | Tag-based scoping provides enough context isolation |

---

## Feature Dependencies

```
AgentBase Memory Service
    └── POST /recall (semantic similarity search)
    └── POST /remember → distill.py → Memory Service write

JSONL storage (patterns.jsonl)
    └── Confidence scoring (alpha/beta per pattern)
    └── GET /stats (aggregation over all patterns)
    └── POST /kb/export (filter Gold + Production)
    └── confidence_history.jsonl (audit trail per update)

Qwen distillation (distill.py)
    └── POST /remember background task
    └── Depends on GreenNode MaaS availability

Tier system
    └── All recall filtering (min_tier parameter)
    └── Gold exit guardrail (consecutive_failures counter)
    └── /stats by_tier counts
```

---

## MVP Recommendation

**Must have for demo to land:**

1. `what_failed` in recall response — callers need both sides of the pattern
2. `tags` and `last_updated` in recall response — zero extra computation, improves trust
3. `recall_hit_rate` in `/stats` — makes KB usefulness measurable
4. `recently_promoted` list in `/stats` — makes self-improvement visible in 1 field
5. `session_id` optional field on `/remember` — future-proofs for multi-session use without requiring it now
6. Structured error responses (`{"error": "...", "code": "..."}`) — basic production quality signal

**Can defer (post-hackathon):**
- Recency filter on `/recall`
- `duration_ms` on `/remember`
- Full hybrid search (BM25 + vector)
- Pattern deduplication beyond Qwen matching

---

## Gaps Research Could Not Resolve

- No public documentation found for the exact AgentBase Memory Service query/response format — the `relevance_score` field name may differ from what the platform returns. Verify against GreenNode docs or test calls before hardcoding field names in `memory.py`.
- Qwen structured extraction quality for the `what_worked`/`what_failed` split is unknown until tested. If Qwen fails to split reliably, falling back to storing `what_happened` as `what_worked` with empty `what_failed` is a safe default.
- No clear prior art for the exact `/recall` → task → `/remember` loop pattern with Bayesian confidence — AKC appears genuinely novel in this specific combination. Confidence: MEDIUM (absence of evidence, not evidence of absence).

---

## Sources

- [State of AI Agent Memory 2026 — mem0.ai](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Cloudflare Agent Memory HTTP API](https://developers.cloudflare.com/agent-memory/api/http-api/)
- [agentmemory — #1 persistent memory for AI coding agents](https://github.com/rohitg00/agentmemory)
- [Azure AI Search Agentic Retrieval Overview](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview)
- [Agent Observability: Complete Guide 2026 — Braintrust](https://www.braintrust.dev/articles/agent-observability-complete-guide-2026)
- [RAG Is Not Dead: Advanced Retrieval Patterns 2026 — DEV Community](https://dev.to/young_gao/rag-is-not-dead-advanced-retrieval-patterns-that-actually-work-in-2026-2gbo)
- [Best AI Agent Memory Frameworks 2026 — Atlan](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/)
- [RAG Best Practices — Redwerk](https://redwerk.com/blog/rag-best-practices/)
- [mem0 Universal Memory Layer — GitHub](https://github.com/mem0ai/mem0)
