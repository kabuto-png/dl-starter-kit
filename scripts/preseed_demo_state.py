"""Pre-seed AKC demo state for Scene 2 cinematic tier promotion.

After running `seed_kb.py`, the demo storyboard's Scene 2 needs
`pat_aso_jp_001` (the JP hiragana keyword pattern) to be at confidence ~0.84
(production tier, near-gold threshold) so that one more /remember success
during Scene 2 will visibly promote it to gold.

This script applies 3 success outcomes off-camera to bump confidence from
the freshly-seeded value (~0.74) to ~0.84.

Run: PYTHONPATH=. venv/bin/python scripts/preseed_demo_state.py --kb-dir ./data/kb
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


async def main():
    parser = argparse.ArgumentParser(description="Apply 3 off-camera success outcomes to demo pattern")
    parser.add_argument("--kb-dir", default="./data/kb", help="KB directory containing patterns.jsonl")
    parser.add_argument("--target-pattern", default=None, help="Pattern ID to bump (default: first ASO JP keyword pattern)")
    parser.add_argument("--bumps", type=int, default=3, help="Number of success outcomes to apply")
    args = parser.parse_args()

    kb_path = Path(args.kb_dir).resolve()
    patterns_file = kb_path / "patterns.jsonl"
    if not patterns_file.exists():
        print(f"Error: {patterns_file} not found. Run seed_kb.py first.", file=sys.stderr)
        sys.exit(1)

    # Need PYTHONPATH=. set externally; import akc store + engine
    from akc.patterns.store import JsonlStore
    from akc.patterns import engine

    store = JsonlStore(kb_dir=str(kb_path))

    # Find target pattern
    patterns = await store.load_active(min_tier="experimental", tags=None)
    target_id = args.target_pattern
    if target_id is None:
        # Auto-pick first pattern tagged "aso" + "jp" + "keyword"
        for p in patterns:
            tags = set(p.get("tags", []))
            if {"aso", "jp", "keyword"}.issubset(tags):
                target_id = p["id"]
                break
        if target_id is None:
            # Fallback: first ASO-tagged pattern
            for p in patterns:
                if "aso" in p.get("tags", []):
                    target_id = p["id"]
                    break

    if target_id is None:
        print("Error: No ASO pattern found in KB. Did seed_kb.py include ASO_PATTERNS?", file=sys.stderr)
        sys.exit(1)

    # Get current state
    before = next((p for p in patterns if p["id"] == target_id), None)
    if before is None:
        print(f"Error: Pattern {target_id} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Target pattern: {target_id}")
    print(f"  tags: {before.get('tags', [])}")
    print(f"  context: {before.get('context', '')[:80]}")
    print(f"  before: confidence={before['confidence']:.4f}, tier={before['tier']}, times_applied={before.get('times_applied', 0)}")

    # Apply N successes via store.update_pattern
    for i in range(args.bumps):
        await store.update_pattern(target_id, "success")

    # Re-load and show after state
    patterns_after = await store.load_active(min_tier="experimental", tags=None)
    after = next((p for p in patterns_after if p["id"] == target_id), None)
    if after is None:
        print("Error: Pattern disappeared after update", file=sys.stderr)
        sys.exit(1)

    print(f"  after:  confidence={after['confidence']:.4f}, tier={after['tier']}, times_applied={after.get('times_applied', 0)}")
    print()
    if after["confidence"] >= 0.85:
        print(f"[!]  Pattern already crossed Gold (≥0.85). Scene 2 promotion moment will not be live.")
        print(f"[!]  Consider reducing --bumps or starting from a fresh seed.")
    elif after["confidence"] >= 0.80:
        print(f"[OK] Pattern at confidence={after['confidence']:.4f} — ready for Scene 2 demo (one more success will likely promote to Gold).")
    else:
        print(f"[?]  Pattern at confidence={after['confidence']:.4f} — may need more bumps to be near Gold threshold.")


if __name__ == "__main__":
    asyncio.run(main())
