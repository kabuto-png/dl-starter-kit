"""
ExportService — renders Gold and Production patterns as markdown.

EXPORT-01: All Gold + Production patterns rendered as human-readable markdown.
EXPORT-02: Grouped by tier; each pattern shows context, what_worked, what_failed, confidence, tags.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from akc.patterns.store import JsonlStore

logger = logging.getLogger("akc.export.service")


class ExportService:
    def __init__(self, store: JsonlStore) -> None:
        self._store = store

    async def export_markdown(self) -> str:
        """
        Load all patterns, filter to Gold + Production, render as markdown.

        EXPORT-01: Only gold and production tiers included.
        EXPORT-02: Grouped by tier; per-pattern: context, what_worked, what_failed, confidence, tags.
        """
        # Load all patterns from store (unfiltered)
        patterns = await self._store.load_all(exclude_demoted=False)

        # EXPORT-01: filter to gold and production only
        gold = [p for p in patterns if p.get("tier") == "gold"]
        production = [p for p in patterns if p.get("tier") == "production"]

        total_exported = len(gold) + len(production)
        timestamp = datetime.now(timezone.utc).isoformat()

        lines: list[str] = [
            "# AKC Knowledge Base Export",
            "",
            f"**Generated:** {timestamp}",
            f"**Total patterns:** {total_exported}",
            "",
        ]

        # Tier sections: "## Gold (Highest Confidence)" and "## Production"
        for tier_label, tier_patterns in [
            ("Gold (Highest Confidence)", gold),
            ("Production", production),
        ]:
            lines.append(f"## {tier_label}")
            lines.append("")

            if not tier_patterns:
                lines.append("*(no patterns in this tier)*")
                lines.append("")
                continue

            for p in tier_patterns:
                lines.append(f"### Pattern: {p.get('id', 'unknown')}")
                lines.append("")
                lines.append(f"- **Context:** {p.get('context', '')}")
                lines.append(f"- **What Worked:** {p.get('what_worked', '')}")
                lines.append(f"- **What Failed:** {p.get('what_failed', '')}")
                lines.append(f"- **Confidence:** {p.get('confidence', 0):.2f}")
                lines.append(f"- **Tags:** {', '.join(p.get('tags', []))}")
                lines.append("")

        markdown = "\n".join(lines)
        logger.info(
            "Export: %d patterns (%d gold, %d production), %d bytes",
            total_exported,
            len(gold),
            len(production),
            len(markdown),
        )
        return markdown
