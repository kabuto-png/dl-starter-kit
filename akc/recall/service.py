"""
RecallService — orchestrates the full recall pipeline.

RCL-01: Accepts RecallRequest (task_context, tags, top_k, min_tier).
RCL-02: Returns RecallResponse with all required fields per pattern.
RCL-04: Delegates semantic search to search.py adapter (Memory Service + fallback).
STATS-02: Records every recall query to confidence_history.jsonl.
"""
from __future__ import annotations
import logging
from typing import Optional

from akc.patterns.store import JsonlStore
from akc.recall.models import RecallRequest, RecallResult, RecallResponse
from akc.recall.engine import filter_and_rank
from akc.recall.search import semantic_search

logger = logging.getLogger("akc.recall.service")


class RecallService:
    def __init__(self, store: JsonlStore, memory_id: Optional[str] = None) -> None:
        self._store = store
        self._memory_id = memory_id

    async def query(self, request: RecallRequest) -> RecallResponse:
        """
        Full recall pipeline:
          1. Load active patterns from store (filtered by min_tier + optional tags)
          2. Semantic search via Memory Service (with fallback)
          3. Filter + rank by confidence/relevance_score
          4. Map to RecallResult models
          5. Record recall query for stats tracking (STATS-02)
        """
        # Step 1: load candidates
        candidates = await self._store.load_active(
            min_tier=request.min_tier,
            tags=request.tags,
        )

        # Step 2: semantic search (Memory Service or local fallback)
        scored = await semantic_search(
            task_context=request.task_context,
            patterns=candidates,
            memory_id=self._memory_id,
            timeout_sec=10.0,
        )

        # Step 3: filter, rank, paginate
        ranked = filter_and_rank(
            patterns=scored,
            min_tier=request.min_tier,
            tags=request.tags,
            top_k=request.top_k,
        )

        # Step 4: map to response models
        results = [
            RecallResult(
                id=p["id"],
                what_worked=p.get("what_worked", ""),
                what_failed=p.get("what_failed", ""),
                confidence=p.get("confidence", 0.0),
                tier=p.get("tier", "experimental"),
                times_applied=p.get("times_applied", 0),
                tags=p.get("tags", []),
                last_updated=p.get("last_updated"),
                relevance_score=p.get("relevance_score"),
            )
            for p in ranked
        ]

        # Step 5: record recall query for stats (STATS-02)
        await self._store.record_recall_query(result_count=len(results))

        logger.info(
            "Recall: %d candidates -> %d results (min_tier=%s, top_k=%d)",
            len(candidates),
            len(results),
            request.min_tier,
            request.top_k,
        )
        return RecallResponse(patterns=results, count=len(results))
