"""
filter_and_rank — pure function, no I/O.
RCL-03: Demoted patterns excluded before any confidence threshold check.
"""
from __future__ import annotations


TIER_RANK: dict[str, int] = {
    "gold": 3,
    "production": 2,
    "experimental": 1,
    "demoted": 0,
}


def filter_and_rank(
    patterns: list[dict],
    min_tier: str = "production",
    tags: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Filter patterns by tier and tags; rank by relevance_score (if present) or confidence descending.

    RCL-03: Demoted patterns NEVER returned — checked first, before min_tier.
    Tag matching is OR logic: pattern needs ANY of the request tags.
    """
    VALID_TIERS = {"gold", "production", "experimental", "demoted"}
    if min_tier not in VALID_TIERS:
        min_tier = "production"

    min_rank = TIER_RANK.get(min_tier, 2)  # unknown tier defaults to production rank
    request_tags: set[str] | None = {t.lower() for t in tags} if tags else None

    filtered: list[dict] = []
    for p in patterns:
        # RCL-03: demoted is a lock, not a score — check BEFORE anything else
        if p.get("tier") == "demoted":
            continue

        # min_tier threshold
        if TIER_RANK.get(p.get("tier", "experimental"), 0) < min_rank:
            continue

        # tag filter — OR logic (pattern needs ANY request tag)
        if request_tags:
            pattern_tags = {t.lower() for t in p.get("tags", [])}
            if not pattern_tags.intersection(request_tags):
                continue

        filtered.append(p)

    # Sort — prefer relevance_score from Memory Service; fall back to confidence
    if filtered and filtered[0].get("relevance_score") is not None:
        filtered.sort(key=lambda p: p.get("relevance_score") or 0, reverse=True)
    else:
        filtered.sort(key=lambda p: p.get("confidence", 0), reverse=True)

    return filtered[:top_k]
