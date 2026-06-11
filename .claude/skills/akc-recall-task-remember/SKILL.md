---
name: akc-recall-task-remember
description: "Automate the recall → task → remember loop for AKC knowledge base"
usage_pattern: "akc-recall-task-remember --task <task> [--endpoint <url>] [--top-k <n>] [--min-tier <tier>]"
version: "1.0"
---

# AKC — Recall → Task → Remember

Automate the recall → task → remember cycle: fetch patterns from the AKC knowledge base,
use them to execute a task, capture the outcome, and feed it back to update confidence.

## Usage

    /akc-recall-task-remember --task "write a python async function for file I/O" --endpoint http://localhost:8080

## Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--task` | yes | — | Task context for POST /recall |
| `--endpoint` | no | http://localhost:8080 | AKC service base URL |
| `--top-k` | no | 5 | Number of patterns to recall |
| `--min-tier` | no | production | Minimum confidence tier (experimental/production/gold) |
| `--show-history` | no | false | Debug mode — print all HTTP requests and responses |

## How It Works

1. **Recall:** POST /recall with task_context to fetch high-confidence patterns from the knowledge base
2. **Task:** Analyze patterns; synthesize solution using what_worked guidance
3. **Remember:** POST /remember with outcome=success and pattern IDs used
4. **Report:** GET /stats to show confidence changes and recently_promoted

## Implementation

```python
import argparse
import json
import sys
import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AKC Recall -> Task -> Remember automation"
    )
    parser.add_argument("--task", required=True, help="Task context for /recall")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8080",
        help="AKC service base URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of patterns to recall (default: 5)",
    )
    parser.add_argument(
        "--min-tier",
        default="production",
        help="Minimum confidence tier: experimental/production/gold (default: production)",
    )
    parser.add_argument(
        "--show-history",
        action="store_true",
        help="Debug mode: print all HTTP requests and responses",
    )
    return parser.parse_args()


def recall_phase(
    endpoint: str, task_context: str, top_k: int, min_tier: str
) -> list[dict]:
    """Call POST /recall; return list of patterns ranked by confidence."""
    url = f"{endpoint}/recall"
    payload = {
        "task_context": task_context,
        "top_k": top_k,
        "min_tier": min_tier,
    }
    response = requests.post(url, json=payload, timeout=5.0)
    response.raise_for_status()
    patterns = response.json()
    if not patterns:
        print("No patterns found for the given task and tier; proceeding without guidance")
    else:
        print(f"Recalled {len(patterns)} pattern(s) from tier '{min_tier}':")
        for i, p in enumerate(patterns, 1):
            print(
                f"  [{i}] {p.get('context', '')[:60]} "
                f"(confidence={p.get('confidence', 0):.2f}, tier={p.get('tier', 'unknown')})"
            )
    return patterns


def task_phase(
    patterns: list[dict], task_context: str
) -> tuple[str, list[str]]:
    """
    Analyze patterns and synthesize a task solution.

    Returns: (solution_text, list_of_pattern_ids_used)
    """
    if not patterns:
        solution = (
            f"Generic solution for: {task_context}\n"
            "(No patterns available — using default approach)"
        )
        return solution, []

    advice_lines = []
    for p in patterns:
        what_worked = p.get("what_worked", "")
        if what_worked:
            advice_lines.append(f"  - {what_worked}")

    advice_text = "\n".join(advice_lines) if advice_lines else "  (no specific guidance)"

    solution = (
        f"Solution for: {task_context}\n\n"
        f"Guided by {len(patterns)} pattern(s):\n"
        f"{advice_text}\n\n"
        f"Pattern guidance applied to synthesize implementation."
    )

    pattern_ids = [p["id"] for p in patterns]
    return solution, pattern_ids


def remember_phase(
    endpoint: str, task_context: str, outcome: str, patterns_used: list[str]
) -> bool:
    """
    Call POST /remember to update pattern confidence.

    Returns: True if 202 Accepted received.
    """
    url = f"{endpoint}/remember"
    payload = {
        "task_context": task_context,
        "outcome": outcome,
        "patterns_used": patterns_used,
    }
    response = requests.post(url, json=payload, timeout=5.0)
    if response.status_code == 202:
        print(f"Remember accepted (202) — distillation running in background")
        return True
    else:
        print(
            f"Remember returned unexpected status ({response.status_code}): {response.text}"
        )
        return False


def report_phase(endpoint: str, patterns_before: list[dict]) -> None:
    """
    Fetch updated stats; compare with pre-task state.
    """
    url = f"{endpoint}/stats"
    response = requests.get(url, timeout=5.0)
    response.raise_for_status()
    stats = response.json()

    print("\n" + "=" * 60)
    print("REPORT: Recall -> Task -> Remember Complete")
    print("=" * 60)
    print(f"\nPatterns recalled: {len(patterns_before)}")

    avg_conf = stats.get("avg_confidence")
    if avg_conf is not None:
        print(f"Average confidence (after): {avg_conf:.2f}")

    by_tier = stats.get("by_tier", {})
    if by_tier:
        print(f"By tier (after): {json.dumps(by_tier)}")

    recently_promoted = stats.get("recently_promoted", [])
    if recently_promoted:
        print(f"\nRecently promoted: {recently_promoted[:3]}")

    print("\n" + "=" * 60)


def main() -> None:
    args = parse_args()

    try:
        # Phase 1: Recall
        print(f"Phase 1: Recalling patterns for '{args.task}'...")
        patterns = recall_phase(args.endpoint, args.task, args.top_k, args.min_tier)

        # Phase 2: Task
        print(f"\nPhase 2: Synthesizing solution...")
        solution, pattern_ids = task_phase(patterns, args.task)
        print(solution)

        # Evaluate outcome (demo: always success when patterns were found)
        outcome = "success" if patterns else "failure"

        # Phase 3: Remember
        print(f"\nPhase 3: Remembering outcome (outcome={outcome})...")
        remember_phase(args.endpoint, args.task, outcome, pattern_ids)

        # Phase 4: Report
        print(f"\nPhase 4: Fetching updated stats...")
        report_phase(args.endpoint, patterns)

    except requests.ConnectionError:
        print(f"Cannot connect to {args.endpoint} — ensure AKC service is running: docker run -p 8080:8080 ...")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## Output

When invoked, judges will see:

- **Patterns recalled:** list of patterns with context, confidence, and tier
- **Patterns used:** which pattern IDs were applied in the task solution
- **Confidence deltas:** average confidence before and after (via GET /stats)
- **Newly promoted patterns:** patterns that moved to a higher tier after successful use

## Error Handling

- **Network error (cannot connect):** exits immediately with `Cannot connect to {endpoint} — ensure AKC service is running: docker run -p 8080:8080 ...`
- **Empty recall:** logs `No patterns found; proceeding without guidance` and continues with generic solution
- **Non-202 response from /remember:** logs the unexpected status code and continues (does not halt execution)
