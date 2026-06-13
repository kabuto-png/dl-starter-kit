import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from akc.patterns.models import ConfidenceEvent, Pattern


class JsonlStore:
    """JSONL persistence layer for AKC patterns.

    STORE-03: All writes protected by a single asyncio.Lock.
    The ENTIRE read-modify-write cycle is held under the lock.
    """

    def __init__(self, kb_dir: str) -> None:
        self._dir = Path(kb_dir).resolve()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._patterns_path = self._dir / "patterns.jsonl"
        self._history_path = self._dir / "confidence_history.jsonl"

    def _read_patterns_sync(self) -> dict[str, dict]:
        """STORE-01: last-write-wins dedup by id. Corrupt lines are skipped with warning."""
        if not self._patterns_path.exists():
            return {}
        result: dict[str, dict] = {}
        with open(self._patterns_path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    result[record["id"]] = record
                except (json.JSONDecodeError, KeyError) as exc:
                    # H5: defensive — skip corrupt lines so a single bad write
                    # cannot brick the entire store. Already done for history file.
                    import logging
                    logging.getLogger("akc.patterns.store").warning(
                        "Skipping corrupt line %d in patterns.jsonl: %s", lineno, exc
                    )
        return result

    def _write_patterns_atomic_sync(self, records: dict[str, dict]) -> None:
        """STORE-03: tempfile + os.replace (atomic). NEVER call on history file."""
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self._dir, delete=False, suffix=".tmp", encoding="utf-8",
        ) as tmp:
            for record in records.values():
                tmp.write(json.dumps(record) + "\n")
            tmp_path = tmp.name
        os.replace(tmp_path, str(self._patterns_path))

    def _append_history_sync(self, event: dict) -> None:
        """STORE-02: Pure append — NEVER use os.replace on this file."""
        with open(self._history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    async def load_all(self, exclude_demoted: bool = False) -> list[dict]:
        async with self._lock:
            patterns_dict = await asyncio.to_thread(self._read_patterns_sync)
        patterns = list(patterns_dict.values())
        if exclude_demoted:
            patterns = [p for p in patterns if p.get("tier") != "demoted"]
        return sorted(patterns, key=lambda x: x.get("confidence", 0), reverse=True)

    async def record_recall_query(self, result_count: int) -> None:
        event = {
            "type": "recall_query",
            "result_count": result_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(self._append_history_sync, event)

    async def load_stats(self) -> dict:
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
        total = len(patterns)
        by_tier = {"gold": 0, "production": 0, "experimental": 0, "demoted": 0}
        all_confidences = []
        all_tags = []
        for p in patterns.values():
            tier = p.get("tier", "experimental")
            by_tier[tier] = by_tier.get(tier, 0) + 1
            all_confidences.append(p.get("confidence", 0))
            all_tags.extend(p.get("tags", []))
        avg_confidence = (sum(all_confidences) / len(all_confidences) if all_confidences else 0.0)
        tag_counts: dict[str, int] = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = [tag for tag, _ in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]]
        recall_hit_rate, recently_promoted = await asyncio.to_thread(self._scan_history_sync)
        return {
            "total_patterns": total,
            "by_tier": by_tier,
            "avg_confidence": round(avg_confidence, 2),
            "top_tags": top_tags,
            "recall_hit_rate": recall_hit_rate,
            "recently_promoted": recently_promoted,
        }

    def _scan_history_sync(self) -> tuple[float, list]:
        if not self._history_path.exists():
            return 0.0, []
        tier_rank = {"gold": 3, "production": 2, "experimental": 1, "demoted": 0}
        recall_queries = 0
        recall_hits = 0
        promotions = []
        with open(self._history_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Malformed history line, skipping: %s", line[:80])
                    continue
                event_type = event.get("type")
                if event_type == "recall_query":
                    recall_queries += 1
                    if event.get("result_count", 0) > 0:
                        recall_hits += 1
                elif event_type == "confidence_update":
                    old_tier = event.get("old_tier")
                    new_tier = event.get("new_tier")
                    if old_tier and new_tier:
                        if tier_rank.get(new_tier, 0) > tier_rank.get(old_tier, 0):
                            promotions.append({
                                "id": event.get("pattern_id"),
                                "old_tier": old_tier,
                                "new_tier": new_tier,
                                "timestamp": event.get("timestamp"),
                            })
        hit_rate = recall_hits / recall_queries if recall_queries > 0 else 0.0
        recently_promoted = sorted(promotions, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]
        return hit_rate, recently_promoted

    async def load_active(
        self,
        min_tier: str = "production",
        tags: list[str] | None = None,
    ) -> list[dict]:
        tier_rank = {"gold": 3, "production": 2, "experimental": 1, "demoted": 0}
        min_rank = tier_rank.get(min_tier, 2)
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
        results = []
        for p in patterns.values():
            if p.get("tier") == "demoted":
                continue
            if tier_rank.get(p.get("tier", "experimental"), 0) < min_rank:
                continue
            if tags:
                pattern_tags = set(p.get("tags", []))
                if not any(t.lower() in pattern_tags for t in tags):
                    continue
            results.append(p)
        return sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)

    async def update_pattern(self, pattern_id: str, outcome: str) -> None:
        from akc.patterns import engine  # late import avoids circular dep
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
            if pattern_id not in patterns:
                return
            old = dict(patterns[pattern_id])
            patterns[pattern_id] = engine.apply_outcome(old, outcome)
            await asyncio.to_thread(self._write_patterns_atomic_sync, patterns)
            history_event = {
                "type": "confidence_update",  # H7: required by _scan_history_sync
                "pattern_id": pattern_id,
                "outcome": outcome,
                "old_confidence": old["confidence"],
                "new_confidence": patterns[pattern_id]["confidence"],
                "old_tier": old["tier"],
                "new_tier": patterns[pattern_id]["tier"],
                "timestamp": patterns[pattern_id]["last_updated"],
            }
            await asyncio.to_thread(self._append_history_sync, history_event)

    async def insert_pattern(self, pattern: Pattern) -> None:
        """Insert a new pattern into patterns.jsonl.

        STORE-03: Full read-modify-write cycle held under asyncio.Lock.
        Uses atomic write (NamedTemporaryFile + os.replace) — crash safe.
        Last-write-wins dedup on read (STORE-01): if pattern.id already exists,
        this insert will overwrite the existing record (same as update_pattern).
        """
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
            patterns[pattern.id] = json.loads(pattern.model_dump_json())
            await asyncio.to_thread(self._write_patterns_atomic_sync, patterns)

    async def save_pattern(self, pattern: Pattern) -> None:
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
            patterns[pattern.id] = json.loads(pattern.model_dump_json())
            await asyncio.to_thread(self._write_patterns_atomic_sync, patterns)
