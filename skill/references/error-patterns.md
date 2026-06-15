# Error Patterns & Recovery

How to handle common AKC failure modes. **Never block the user's task on AKC errors.**

## Network failures

### Timeout / connection refused

```bash
curl: (28) Operation timed out
# or
curl: (7) Failed to connect to ... port 8080
```

**Cause**: AKC service down, network partition, or wrong `AKC_ENDPOINT`.

**Recovery**:
1. Log warning: `"AKC unreachable — proceeding with general best practices"`
2. **Continue the task** without patterns. Do NOT prompt the user.
3. After task done: skip `/remember` (or queue locally if you implement that).

### 5xx server error

```json
{"error": "internal server error"}
```

**Cause**: AKC bug, DB down, LLM provider issue.

**Recovery**: same as timeout — log, continue, skip remember.

### 4xx client error

```json
{"detail": [{"loc": ["body","tags"], "msg": "field required", ...}]}
```

**Cause**: malformed payload — usually missing `task_context` or `tags`.

**Recovery**:
1. Log the actual error
2. Fix the payload (most common: empty tags array, missing task_context)
3. Retry once. If still 4xx → continue without patterns.

---

## Schema validation failures

### Missing required fields

```bash
# /recall requires: task_context, tags
# /remember requires: task_context, outcome, success, what_happened
```

Check payload before sending. If your skill produced an empty `tags` array → use generic fallback `["coding", "general"]` rather than fail.

### Invalid tier value

```json
{"min_tier": "amazing"}  // ERROR — must be one of: experimental, production, gold
```

Stick to the 3 valid tiers. If unsure, omit `min_tier` (defaults to `production`).

---

## Empty recall

### `total_found: 0`

```json
{"patterns": [], "total_found": 0}
```

**Not an error** — just means no past patterns match. Behavior:

1. **Acknowledge** to user: "No past patterns found for this context."
2. **Proceed** with general best practices.
3. **Don't fabricate** pattern IDs to look authoritative.
4. **Do call `/remember`** after — even cold starts contribute to memory.

This is **especially important for production agents**. An agent that hallucinates pattern IDs on empty recall is a production blocker. Test this behavior.

---

## Stale or wrong patterns

### Pattern's `what_worked` no longer applies

E.g., pattern says "use API v1" but v1 deprecated.

**Recovery**:
1. Use updated approach in the task
2. After task: call `/remember` with `success: false` for the stale pattern's `task_context` + describe deprecation in `what_happened`
3. AKC will demote the pattern's confidence over time

### Pattern contradicts itself

`what_worked` says X, `what_failed` says X failed.

**Cause**: pattern aggregated outcomes from different sub-contexts.

**Recovery**: read both fields, use judgment. Note the contradiction in your `/remember` `what_happened` field.

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Block user's task waiting for AKC retry | Time out fast, continue without AKC |
| Show raw curl errors to user | Log silently, fall back gracefully |
| Report `success: true` on cold-start tasks | Only `success: true` after user confirms result |
| Skip `/remember` because `/recall` returned empty | Always `/remember`, even with `patterns_used: []` |
| Hardcode `AKC_ENDPOINT` in skill | Read from env: `${AKC_ENDPOINT:-http://localhost:8080}` |

---

## When to surface AKC issues to user

**Surface ONLY when**:
- User explicitly asks "is AKC working?"
- User attempts a pattern-dependent action and AKC has been down for the whole session
- The task fundamentally requires memory (e.g., "what did we learn from last JP launch?") and AKC is down

**Don't surface** for normal task flow. AKC is a memory layer — agent should work fine without it, just less informed.
