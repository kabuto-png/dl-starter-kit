"""One-shot A/B test for LLM distillation quality across 3 GreenNode MaaS models.

Sends the SAME production distill prompt to each model, parses JSON output,
validates against DistilledPattern schema, measures latency + token usage.

Run: PYTHONPATH=. venv/bin/python scripts/ab_test_llms.py
"""
import asyncio
import json
import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import AsyncOpenAI

from akc.remember.models import DistilledPattern

load_dotenv()

MODELS = [
    "minimax/minimax-m2.5",
    "qwen/qwen3-5-27b",
    "google/gemma-4-31b-it",
]

_DISTILL_SYSTEM_PROMPT = """\
Extract the key learning from this task outcome. Respond with ONLY a JSON object \
(no markdown, no code fences, no extra text).

{
  "context": "brief description of the task or scenario",
  "what_worked": "specific thing that succeeded",
  "what_failed": "specific thing that failed, or empty string if purely successful",
  "tags": ["lowercase", "tags", "describing", "this", "outcome"]
}"""

# ASO-flavored test case matching demo persona
TASK_CONTEXT = "Launch Casual game in Japan iOS App Store, optimize for week-1 keyword ranking"
OUTCOME = (
    "Replaced romaji-only title with hiragana long-tail keywords (放置RPG style terms) sourced "
    "from Sensor Tower JP top-50. Swapped EN screenshots for JP-localized renders with hiragana UI overlay. "
    "Submitted metadata update on Tuesday JST. Result: 4 first-page ranks captured within 7 days, "
    "CTR lifted 11% on search results. Did NOT change icon — that test is queued separately. "
    "Lesson: kanji compound terms drove most of the lift; hiragana alone underperformed."
)


@dataclass
class Result:
    model: str
    latency_ms: float
    finish_reason: str
    raw_content: str
    parse_ok: bool
    validate_ok: bool
    distilled: dict | None
    error: str | None
    prompt_tokens: int | None
    completion_tokens: int | None


async def test_model(client: AsyncOpenAI, model: str) -> Result:
    start = time.time()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _DISTILL_SYSTEM_PROMPT},
                {"role": "user", "content": f"Task context: {TASK_CONTEXT}\n\nOutcome: {OUTCOME}"},
            ],
            response_format={"type": "json_object"},
            max_tokens=1024,
            extra_body={"enable_thinking": False},
            temperature=0.3,
        )
        latency = (time.time() - start) * 1000
        finish = response.choices[0].finish_reason
        content = response.choices[0].message.content or ""
        usage = response.usage

        # Try parse + validate
        parse_ok = False
        validate_ok = False
        distilled = None
        err = None
        try:
            distilled_obj = DistilledPattern.model_validate_json(content)
            parse_ok = True
            validate_ok = True
            distilled = distilled_obj.model_dump()
        except Exception as e:
            err = f"validate: {type(e).__name__}: {str(e)[:120]}"
            try:
                json.loads(content)
                parse_ok = True
            except Exception:
                pass

        return Result(
            model=model,
            latency_ms=latency,
            finish_reason=finish,
            raw_content=content[:300],
            parse_ok=parse_ok,
            validate_ok=validate_ok,
            distilled=distilled,
            error=err,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return Result(
            model=model,
            latency_ms=latency,
            finish_reason="error",
            raw_content="",
            parse_ok=False,
            validate_ok=False,
            distilled=None,
            error=f"{type(e).__name__}: {str(e)[:200]}",
            prompt_tokens=None,
            completion_tokens=None,
        )


async def main():
    client = AsyncOpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ["LLM_BASE_URL"],
    )
    print(f"=== A/B test: {len(MODELS)} models ===")
    print(f"Task: {TASK_CONTEXT}")
    print()

    results = await asyncio.gather(*(test_model(client, m) for m in MODELS), return_exceptions=False)

    # Summary table
    print(f"{'Model':<28} {'Latency':>10} {'JSON':>6} {'Valid':>6} {'PromptT':>8} {'CompT':>8} {'Finish':>10}")
    print("-" * 90)
    for r in results:
        print(
            f"{r.model:<28} {r.latency_ms:>8.0f}ms "
            f"{'OK' if r.parse_ok else 'FAIL':>6} "
            f"{'OK' if r.validate_ok else 'FAIL':>6} "
            f"{(r.prompt_tokens or 0):>8} "
            f"{(r.completion_tokens or 0):>8} "
            f"{r.finish_reason:>10}"
        )

    # Detail output
    print()
    for r in results:
        print(f"\n--- {r.model} ---")
        if r.error:
            print(f"  error: {r.error}")
        if r.distilled:
            print(f"  context: {r.distilled.get('context', '')[:120]}")
            print(f"  what_worked: {r.distilled.get('what_worked', '')[:120]}")
            print(f"  what_failed: {r.distilled.get('what_failed', '')[:120]}")
            print(f"  tags: {r.distilled.get('tags', [])}")
        else:
            print(f"  raw (first 300): {r.raw_content!r}")


if __name__ == "__main__":
    asyncio.run(main())
