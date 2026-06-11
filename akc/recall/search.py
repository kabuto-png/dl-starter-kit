"""
semantic_search — GreenNode AgentBase Memory Service adapter with asyncio.timeout fallback.

RCL-04: asyncio.timeout(2.0) guard; local pattern list returned on any failure.
RCL-05: relevance_score from Memory Service threaded through on success path.

Memory records are stored as "[{pattern_id}] {context}: {what_worked}" so we can
map relevance scores back to local patterns by parsing the ID prefix.
"""
from __future__ import annotations
import asyncio
import logging
import math
import re
from typing import Optional

logger = logging.getLogger("akc.recall.search")

_PATTERN_ID_RE = re.compile(r"^\[([a-f0-9\-]{36})\]")

# Module-level singleton so OAuth2 token is cached across requests
_memory_client = None


def get_memory_client():
    global _memory_client
    if _memory_client is None:
        from greennode_agentbase.memory import MemoryClient
        _memory_client = MemoryClient()
    return _memory_client


async def semantic_search(
    task_context: str,
    patterns: list[dict],
    memory_id: Optional[str] = None,
    timeout_sec: float = 2.0,
) -> list[dict]:
    """
    Attempt semantic search via GreenNode AgentBase Memory Service.
    Returns patterns with relevance_score attached on success.
    Returns original patterns (no relevance_score) on timeout, error, or unavailability.

    RCL-04: asyncio.timeout guard; graceful fallback to local patterns.
    RCL-05: relevance_score threaded through from Memory Service response.
    """
    if not memory_id or not patterns:
        logger.debug("Memory ID not configured or no patterns; using local fallback")
        return patterns

    try:
        async with asyncio.timeout(timeout_sec):
            from greennode_agentbase.memory.models import MemoryRecordSearchRequest

            client = get_memory_client()
            request = MemoryRecordSearchRequest(query=task_context, limit=len(patterns))
            result = await client.search_memory_records_async(
                id=memory_id, request=request, namespace="akc-patterns"
            )

        # Build score map: pattern_id -> relevance score
        records = result if isinstance(result, list) else (result.get("listData") or result.get("list_data") or [])
        score_map: dict[str, float] = {}
        for rec in records:
            memory_text = rec.memory if hasattr(rec, "memory") else rec.get("memory", "")
            score = rec.score if hasattr(rec, "score") else rec.get("score")
            if not memory_text or score is None:
                continue
            if not isinstance(score, (int, float)) or not math.isfinite(score):
                continue
            m = _PATTERN_ID_RE.match(memory_text)
            if m:
                score_map[m.group(1)] = float(score)

        if not score_map:
            logger.debug("Memory Service returned no parseable scores; using local fallback")
            return patterns

        # Attach relevance_score to matching patterns
        scored = []
        for p in patterns:
            p_copy = p.copy()
            pid = p.get("id")
            if pid and pid in score_map:
                p_copy["relevance_score"] = score_map[pid]
            scored.append(p_copy)

        logger.info("Memory Service: %d/%d patterns scored", len(score_map), len(patterns))
        return scored

    except asyncio.TimeoutError:
        logger.warning(
            "Memory Service timeout (%.1fs), falling back to confidence-based ranking",
            timeout_sec,
        )
        return patterns
    except Exception as exc:
        logger.warning(
            "Memory Service error: %s: %s, falling back to local ranking",
            type(exc).__name__,
            exc,
        )
        return patterns
