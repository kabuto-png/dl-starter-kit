# AKC — Security Posture

## Trust boundary — two planes, two trust levels
- **Data plane (open ingestion):** `recall · remember · stats · export · patterns · gaps` — public, no auth. Anyone can read patterns and submit outcomes; **new patterns enter at `experimental` tier only**. Intentional: low-friction adoption; the KB self-corrects via curation + confidence feedback.
- **Control plane (authenticated):** `POST /curate` (tier promote/demote) **requires `X-Curator-Key`** (constant-time `hmac.compare_digest`). Only the Steward/operator holding the key can change a pattern's tier.

## Enforced today (verified live)
- `/curate` without key → **401**; with key → 200. Reads need no key.
- Key is **never in the repo** (gitignored; runtime env only). Repo secret-audit: clean — no secret ever committed, no secret file tracked.
- Input validation: tier allowlist → 400, pydantic field constraints → 422, unknown id → 404.

## Defense-in-depth
| Layer | Control |
|---|---|
| Auth | `/curate` `X-Curator-Key`, constant-time compare (`hmac.compare_digest`) |
| Integrity | tier↔confidence invariant — curate clamps confidence into the target tier band |
| Quality | anti-hallucination evals (`skill/evals`) + confidence-gated auto-promotion |
| Recovery | deterministic image seed → any tampering reset by redeploy (~2 min) |
| Atomicity | JSONL writes under `asyncio.Lock` + tempfile + `os.replace` (crash-safe) |

## Tamper-resilience
Demo state is baked into the **image seed**, not the (ephemeral) volume. If the KB is tampered or the container resets, `redeploy → fresh container → seed` restores the exact 30-pattern state. Monitor: `GET /stats` should read `30 · {gold:5, production:10, experimental:15}`.

## Roadmap — production access control
1. **Per-user gate via platform MCP Gateway → Policy Group.** Register `akc-mcp` behind the gateway; policy = principal `jwt` + **Condition on the `email` claim ⇒ restrict to `@vng.com.vn`**. Native to AgentBase — **no custom OAuth code**. (Needs Workspace/SSO admin to wire the IdP that issues the JWT.)
2. **Network isolation.** Deploy AKC as a private `agent-runtime-vpc`; MCP reaches it internally; only the gateway is public → "single exposed surface".
3. **Least-privilege IAM.** Scope the service account from `AgentBaseFullAccess` to a group with only `runtime` + `vCR` policies.
4. **Per-tool policy.** Gateway action rules (`akc__<tool>`) to gate individual MCP tools.

## Current demo posture (explicit)
Data plane open for judges to test · control-plane curation key-gated · tamper-recoverable. Full `@vng.com.vn` access control is the Policy-Group + SSO roadmap above, deferred because it requires IdP/admin setup (not available within the event window).

## Note — what MCP cannot do
The MCP client (Claude Desktop/Code) does **not** forward the user's Claude-account identity to the server/gateway. Access control therefore cannot key off "the Claude account"; it must come from an auth layer the user authenticates against (the Policy-Group + JWT path above).
