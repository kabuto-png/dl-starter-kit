import hashlib
import logging
import re
from datetime import datetime, timezone

from openai import AsyncOpenAI, APIError

from akc.core.config import settings
from akc.patterns import engine
from akc.patterns.models import Pattern
from akc.remember.models import DistillRequest, DistilledPattern

logger = logging.getLogger("akc.remember")

# Module-level semaphore — caps concurrent LLM distillation calls to prevent cost attacks
_DISTILL_SEM = None


def _get_distill_sem():
    global _DISTILL_SEM
    if _DISTILL_SEM is None:
        import asyncio
        _DISTILL_SEM = asyncio.Semaphore(5)
    return _DISTILL_SEM

# System prompt for Qwen distillation
_DISTILL_SYSTEM_PROMPT = """\
Extract the key learning from this task outcome. Respond with ONLY a JSON object \
(no markdown, no code fences, no extra text).

{
  "context": "brief description of the task or scenario",
  "what_worked": "specific thing that succeeded",
  "what_failed": "specific thing that failed, or empty string if purely successful",
  "tags": ["lowercase", "tags", "describing", "this", "outcome"]
}"""


async def distill_task_outcome(task_context: str, outcome_text: str) -> dict | None:
    """Call Qwen to extract structured pattern from raw outcome text.

    RMB-03: Uses response_format={"type": "json_object"} + model_validate_json().
    RMB-04: Disables thinking via extra_body + defensive <think> strip.
    RMB-05: Checks finish_reason == "length" before parsing.
    RMB-06: max_tokens=512 minimum.

    Returns dict {context, what_worked, what_failed, tags} or None on any error.
    """
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    user_prompt = f"Task context: {task_context}\n\nOutcome: {outcome_text}"

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _DISTILL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},   # RMB-03: JSON enforcement
            max_tokens=512,                             # RMB-06: >= 512 minimum
            extra_body={"enable_thinking": False},      # RMB-04: disable thinking tokens
            temperature=0.3,                            # Low temperature for structured extraction
        )

        # RMB-05: Check finish_reason BEFORE attempting to parse content
        finish_reason = response.choices[0].finish_reason
        if finish_reason == "length":
            logger.warning(
                "Qwen distillation truncated (finish_reason=length); skipping store",
                extra={"task_context_len": len(task_context), "finish_reason": finish_reason},
            )
            return None

        content = response.choices[0].message.content
        if not content:
            logger.warning("Qwen returned empty content")
            return None

        # RMB-04: Defensively strip <think>...</think> tokens (second safety layer)
        # This catches the case where extra_body parameter name is wrong or unsupported
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        content = content.strip()

        if not content:
            logger.warning("Qwen response empty after <think> stripping")
            return None

        # RMB-03: Use model_validate_json (NOT completions.parse, NOT raw json.loads)
        try:
            distilled = DistilledPattern.model_validate_json(content)
        except Exception as e:
            logger.error(
                "Qwen response failed DistilledPattern validation",
                extra={"error": str(e), "content_sample": content[:200]},
            )
            return None

        return distilled.model_dump()

    except APIError as e:
        logger.error("Qwen API error during distillation", extra={"error": str(e)})
        return None
    except Exception as e:
        logger.error("Unexpected error during distillation", exc_info=True, extra={"error": str(e)})
        return None


def _hash_pattern(context: str, what_worked: str, what_failed: str) -> str:
    """Compute deterministic SHA-256 hash of pattern core content for deduplication."""
    combined = f"{context}|||{what_worked}|||{what_failed}".lower().strip()
    return hashlib.sha256(combined.encode()).hexdigest()


async def _check_duplicate_hash(store, pattern_hash: str) -> dict | None:
    """Return existing pattern with matching hash, or None if no duplicate."""
    patterns = await store.load_active(min_tier="experimental", tags=None)
    for pattern in patterns:
        existing_hash = _hash_pattern(
            pattern.get("context", ""),
            pattern.get("what_worked", ""),
            pattern.get("what_failed", ""),
        )
        if existing_hash == pattern_hash:
            return pattern
    return None


def _get_memory_client():
    """Return shared MemoryClient so OAuth2 token is cached across calls."""
    from akc.recall.search import get_memory_client
    return get_memory_client()


async def _sync_pattern_to_memory(pattern: Pattern) -> None:
    """Insert a pattern into GreenNode Memory Service for semantic search. Best-effort — never raises."""
    try:
        from greennode_agentbase.memory.models import MemoryRecordInsertDirectlyRequest

        memory_id = settings.memory_id
        if not memory_id:
            return

        # Format: "[{id}] {context}: {what_worked}" — parsed by recall/search.py
        text = f"[{pattern.id}] {pattern.context}: {pattern.what_worked}"
        client = _get_memory_client()
        request = MemoryRecordInsertDirectlyRequest(memoryRecords=[text])
        await client.insert_memory_records_directly_async(
            id=memory_id, request=request, namespace="akc-patterns"
        )
        logger.debug("Synced pattern to Memory Service", extra={"pattern_id": pattern.id})
    except Exception as exc:
        logger.warning(
            "Failed to sync pattern to Memory Service (non-fatal): %s",
            repr(exc),
            extra={"pattern_id": pattern.id},
        )


async def distill_and_store(request: DistillRequest, store) -> None:
    """Background task: distill outcome via Qwen, deduplicate, store new pattern, update feedback.

    RMB-02: Entire body wrapped in try/except Exception — never re-raises.
    RMB-07: patterns_used IDs trigger confidence feedback on existing patterns.
    RMB-08: New patterns created at confidence=0.67 (experimental tier).
    """
    try:
        # Step 1: Distill outcome via Qwen — prefer what_happened if provided, fall back to outcome
        outcome_text = request.what_happened or request.outcome
        async with _get_distill_sem():
            distilled = await distill_task_outcome(request.task_context, outcome_text)
        if distilled is None:
            # Already logged inside distill_task_outcome
            return

        # Step 2: Deduplicate by content hash
        pattern_hash = _hash_pattern(
            distilled["context"],
            distilled["what_worked"],
            distilled["what_failed"],
        )
        existing = await _check_duplicate_hash(store, pattern_hash)
        if existing:
            logger.debug(
                "Pattern duplicate found, skipping insert",
                extra={"existing_id": existing.get("id")},
            )
        else:
            # Step 3: Create new pattern at experimental tier — RMB-08
            # Merge distilled tags with caller-supplied tags (deduplicated)
            merged_tags = list({*distilled.get("tags", []), *(request.tags or [])})
            new_pattern = Pattern(
                context=distilled["context"],
                what_worked=distilled["what_worked"],
                what_failed=distilled.get("what_failed", ""),
                tags=merged_tags,
                confidence=engine.INIT_CONFIDENCE,  # RMB-08: 0.67 (experimental)
                tier="experimental",
                last_updated=datetime.now(timezone.utc),
            )

            # Step 4: Persist new pattern
            await store.insert_pattern(new_pattern)
            logger.info(
                "Distilled and stored new pattern",
                extra={"pattern_id": new_pattern.id, "tags": new_pattern.tags},
            )

            # Step 4b: Sync to Memory Service for semantic search (best-effort)
            await _sync_pattern_to_memory(new_pattern)

        # Step 5: Update confidence of patterns_used — RMB-07
        if request.patterns_used:
            outcome_type = "success" if request.success else "failure"
            for pattern_id in request.patterns_used:
                try:
                    await store.update_pattern(pattern_id, outcome_type)
                    logger.debug(
                        "Updated confidence for patterns_used entry",
                        extra={"pattern_id": pattern_id, "outcome": outcome_type},
                    )
                except Exception as inner_e:
                    # Log per-pattern failure but continue processing remaining IDs
                    logger.error(
                        "Failed to update pattern confidence",
                        extra={"pattern_id": pattern_id, "error": str(inner_e)},
                    )

    except Exception as e:
        # RMB-02: Catch-all at boundary — log with full context, never re-raise
        logger.error(
            "distill_and_store failed; KB remains consistent",
            exc_info=True,
            extra={
                "task_context_len": len(request.task_context) if request.task_context else 0,
                "exception": type(e).__name__,
                "message": str(e),
            },
        )
        # DO NOT re-raise — service must continue running
