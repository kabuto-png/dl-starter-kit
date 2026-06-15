"""AKC MCP server — exposes the Agent Knowledge Catalyst as portable MCP tools.

One server, every client: Claude Code, Claude Desktop, Codex, Gemini CLI all speak
MCP, so this wraps the AKC REST API once and works everywhere.

Run:  AKC_ENDPOINT=https://... python mcp/server.py   (stdio transport)
Deps: pip install "mcp[cli]" httpx
"""
from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

AKC_ENDPOINT = os.environ.get("AKC_ENDPOINT", "").rstrip("/")
try:
    TIMEOUT = float(os.environ.get("AKC_TIMEOUT", "30"))
except ValueError:
    TIMEOUT = 30.0

# Hosted behind the AgentBase gateway → disable the localhost-only DNS-rebinding
# guard so the public endpoint's Host header is accepted. No effect on stdio.
mcp = FastMCP(
    "akc",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _require_endpoint() -> str | None:
    if not AKC_ENDPOINT:
        return "ERROR: AKC_ENDPOINT env var is not set. Point it at your AKC runtime URL."
    return None


async def _post(path: str, payload: dict) -> tuple[bool, object]:
    """POST JSON. Returns (ok, parsed_json_or_text). Never raises."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{AKC_ENDPOINT}{path}", json=payload)
        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}: {r.text[:300]}"
        ctype = r.headers.get("content-type", "")
        return True, (r.json() if "application/json" in ctype else r.text)
    except Exception as exc:  # network / timeout / parse — surface to agent, don't crash
        return False, f"{type(exc).__name__}: {exc}"


async def _get(path: str) -> tuple[bool, object]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{AKC_ENDPOINT}{path}")
        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}: {r.text[:300]}"
        ctype = r.headers.get("content-type", "")
        return True, (r.json() if "application/json" in ctype else r.text)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


@mcp.tool()
async def akc_recall(
    task_context: str,
    tags: list[str] | None = None,
    top_k: int = 5,
    min_tier: str = "production",
) -> str:
    """Recall confidence-ranked patterns from team memory BEFORE starting a task.

    Always call this first. Cite the returned pattern IDs in your plan, then pass
    them to akc_remember(patterns_used=[...]) afterward.

    Args:
        task_context: One-sentence summary of what you are about to do.
        tags: Optional lowercase tags to bias retrieval (e.g. ["aso","jp","keyword"]).
        top_k: Max patterns to return (1-100, default 5).
        min_tier: Lowest tier to include: gold|production|experimental|demoted.
    """
    if err := _require_endpoint():
        return err
    payload: dict = {"task_context": task_context, "top_k": top_k, "min_tier": min_tier}
    if tags:
        payload["tags"] = tags
    ok, data = await _post("/recall", payload)
    if not ok:
        return f"recall failed — {data}"
    patterns = data.get("patterns", []) if isinstance(data, dict) else []
    if not patterns:
        return "No patterns found (empty recall). Proceed with general best practices."
    lines = [f"{data.get('total_found', len(patterns))} pattern(s):"]
    for p in patterns:
        rel = p.get("relevance_score")
        rel_s = f", rel={rel:.2f}" if isinstance(rel, (int, float)) else ""
        lines.append(
            f"- [{p.get('id')}] tier={p.get('tier')} conf={p.get('confidence')}{rel_s}\n"
            f"    worked: {p.get('what_worked')}\n"
            f"    failed: {p.get('what_failed') or '—'}\n"
            f"    tags: {', '.join(p.get('tags', []))}"
        )
    return "\n".join(lines)


@mcp.tool()
async def akc_remember(
    task_context: str,
    outcome: str,
    what_happened: str | None = None,
    patterns_used: list[str] | None = None,
    success: bool | None = None,
    tags: list[str] | None = None,
) -> str:
    """Record a task outcome AFTER completing it, so the KB learns.

    Distillation runs asynchronously server-side (returns immediately). Pass the
    pattern IDs you actually used in patterns_used so their confidence updates.

    Args:
        task_context: Same one-sentence summary used in akc_recall.
        outcome: Raw outcome text to distill into a pattern.
        what_happened: Optional richer detail (what you planned, what resulted).
        patterns_used: IDs returned by akc_recall that you applied.
        success: True if the approach worked, False if it failed.
        tags: Optional lowercase tags for the new pattern.
    """
    if err := _require_endpoint():
        return err
    payload: dict = {"task_context": task_context, "outcome": outcome}
    if what_happened is not None:
        payload["what_happened"] = what_happened
    if patterns_used:
        payload["patterns_used"] = patterns_used
    if success is not None:
        payload["success"] = success
    if tags:
        payload["tags"] = tags
    ok, data = await _post("/remember", payload)
    if not ok:
        return f"remember failed — {data}"
    return "Outcome recorded — async distillation queued (HTTP 202)."


@mcp.tool()
async def akc_stats() -> str:
    """Get knowledge-base health: total patterns, tier distribution, recall hit-rate."""
    if err := _require_endpoint():
        return err
    ok, d = await _get("/stats")
    if not ok:
        return f"stats failed — {d}"
    by_tier = d.get("by_tier", {})
    return (
        f"patterns={d.get('total_patterns')} avg_conf={d.get('avg_confidence')}\n"
        f"by_tier: gold={by_tier.get('gold')} production={by_tier.get('production')} "
        f"experimental={by_tier.get('experimental')} demoted={by_tier.get('demoted')}\n"
        f"recall_hit_rate={d.get('recall_hit_rate')} queries={d.get('total_queries')} "
        f"outcomes={d.get('total_outcomes_recorded')}\n"
        f"top_tags: {', '.join(d.get('top_tags', []))}"
    )


@mcp.tool()
async def akc_export() -> str:
    """Export all Gold + Production patterns as a markdown knowledge sheet."""
    if err := _require_endpoint():
        return err
    ok, data = await _post("/kb/export", {})
    if not ok:
        return f"export failed — {data}"
    return data if isinstance(data, str) else str(data)


@mcp.tool()
async def akc_health() -> str:
    """Liveness check — confirms the AKC backend is up and returns pattern count."""
    if err := _require_endpoint():
        return err
    ok, d = await _get("/health")
    if not ok:
        return f"health failed — {d}"
    return f"status={d.get('status')} pattern_count={d.get('pattern_count')}"


@mcp.tool()
async def akc_patterns(tier: str | None = None, tag: str | None = None, limit: int = 50) -> str:
    """Inspect the knowledge base — list patterns (all tiers) for review.

    Read-only view. Curation (promote/demote) is the AKC Steward's job, not exposed here.

    Args:
        tier: Optional filter: gold|production|experimental|demoted.
        tag: Optional single tag filter.
        limit: Max patterns to return (default 50).
    """
    if err := _require_endpoint():
        return err
    qs = f"?limit={limit}"
    if tier:
        qs += f"&tier={tier}"
    if tag:
        qs += f"&tag={tag}"
    ok, d = await _get(f"/patterns{qs}")
    if not ok:
        return f"patterns failed — {d}"
    pats = d.get("patterns", []) if isinstance(d, dict) else []
    lines = [f"{d.get('total', len(pats))} pattern(s):"]
    for p in pats:
        lines.append(
            f"- [{p.get('id')}] {p.get('tier')} conf={p.get('confidence')} — {(p.get('context') or '')[:80]}"
        )
    return "\n".join(lines)


@mcp.tool()
async def akc_gaps() -> str:
    """Show knowledge gaps — queries users searched for but the KB had no answer to."""
    if err := _require_endpoint():
        return err
    ok, d = await _get("/gaps")
    if not ok:
        return f"gaps failed — {d}"
    gaps = d.get("gaps", []) if isinstance(d, dict) else []
    if not gaps:
        return "No coverage gaps recorded."
    return "\n".join(
        f"- ({g.get('count')}x) {g.get('task_context')} [{', '.join(g.get('tags', []))}]"
        for g in gaps
    )


if __name__ == "__main__":
    mcp.run()
