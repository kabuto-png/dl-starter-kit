import asyncio
import json
import os
import tempfile
from pathlib import Path

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
        """STORE-01: last-write-wins dedup by id."""
        if not self._patterns_path.exists():
            return {}
        result: dict[str, dict] = {}
        with open(self._patterns_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    result[record["id"]] = record
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

    async def load_stats(self) -> dict:
        async with self._lock:
            patterns = await asyncio.to_thread(self._read_patterns_sync)
        by_tier: dict[str, int] = {"gold": 0, "production": 0, "experimental": 0, "demoted": 0}
        for p in patterns.values():
            tier = p.get("tier", "experimental")
            by_tier[tier] = by_tier.get(tier, 0) + 1
        return {"total": len(patterns), "by_tier": by_tier}

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
