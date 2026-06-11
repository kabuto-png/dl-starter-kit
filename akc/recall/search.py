"""
semantic_search — AgentBase Memory Service adapter with asyncio.timeout fallback.

RCL-04: asyncio.timeout(2.0) guard; local pattern list returned on any failure.
RCL-05: relevance_score from Memory Service threaded through on success path.
"""
from __future__ import annotations
import asyncio
import logging
import math
from typing import Optional

logger = logging.getLogger("akc.recall.search")


async def semantic_search(
    task_context: str,
    patterns: list[dict],
    memory_service_url: Optional[str] = None,
    timeout_sec: float = 2.0,
) -> list[dict]:
    """
    Attempt semantic search via AgentBase Memory Service.
    Returns patterns with relevance_score attached on success.
    Returns original patterns (no relevance_score) on timeout, error, or unavailability.

    RCL-04: asyncio.timeout guard; graceful fallback to local patterns.
    RCL-05: relevance_score threaded through from Memory Service response.
    """
    if not memory_service_url or not patterns:
        logger.debug("Memory Service URL not configured or no patterns; using local fallback")
        return patterns

    try:
        async with asyncio.timeout(timeout_sec):
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    memory_service_url,
                    json={
                        "query": task_context,
                        "candidates": [{"id": p.get("id")} for p in patterns],
                        "top_k": len(patterns),
                    },
                    timeout=timeout_sec,
                )
                response.raise_for_status()
                result = response.json()

        # Thread relevance_score through — RCL-05
        results_by_id: dict = {
            r["id"]: r
            for r in result.get("results", [])
            if isinstance(r, dict) and "id" in r
        }
        scored: list[dict] = []
        for p in patterns:
            p_copy = p.copy()
            hit = results_by_id.get(p.get("id"))
            if hit:
                raw_score = hit.get("relevance_score")
                # Guard against NaN/Infinity
                if isinstance(raw_score, (int, float)) and math.isfinite(raw_score):
                    p_copy["relevance_score"] = float(raw_score)
            scored.append(p_copy)

        logger.info("Memory Service: %d patterns scored", len(scored))
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
