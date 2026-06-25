"""
LLM Model Tester — pings available Gemini models using your .env API key.

Tests models from the Gemini family (1.5, 2.0, 2.5, 3.0) to help you pick
the best LLM_DEFAULT_MODEL for your use case.

Usage:
    uv run python scripts/test_llm.py

What it tests:
    - Gemini 1.5 Pro, 1.5 Flash      (stable, widely available)
    - Gemini 2.0 Flash, 2.0 Flash-Lite  (fast, cost-effective)
    - Gemini 2.5 Pro, 2.5 Flash      (latest-gen reasoning)
    - Gemini 3 Pro Preview, 3 Flash Preview  (bleeding edge — may need allowlist)

Notes:
    - Gemini 3+ models recommend temperature=1.0 (the API default).
      Setting lower temperatures can cause degraded reasoning.
    - Results are saved to test_results.json for comparison.
"""

import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend/ (same as the real app)
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    print(f"❌ .env not found at {env_path}")
    print("   Create backend/.env with GEMINI_API_KEY first.")
    sys.exit(1)

load_dotenv(env_path)

# ── Models to test ────────────────────────────────────────────────
# Format: "provider/model-name" (LiteLLM standard notation)
# The `gemini/` prefix tells LiteLLM to use the Gemini API (API key).
# Without a prefix, LiteLLM defaults to Vertex AI (GCP auth required).
#
# Gemini 3+ models are listed separately because they have different
# parameter behavior (temperature=1.0 recommended, thinking_level
# instead of thinking_budget).
MODELS_V3 = [
    "gemini/gemini-3-pro-preview",       # Google's latest — may need allowlist access
    "gemini/gemini-3-flash-preview",     # Faster Gemini 3 variant
]

MODELS_V25 = [
    "gemini/gemini-2.5-pro-preview-03-25",  # Primary MVP choice
    "gemini/gemini-2.5-flash-preview-04-17", # Faster 2.5 variant
]

MODELS_V2 = [
    "gemini/gemini-2.0-flash",           # Widely available, good balance
    "gemini/gemini-2.0-flash-lite",      # Fastest/cheapest
]

MODELS_V1 = [
    "gemini/gemini-1.5-pro",             # Legacy high-capability
    "gemini/gemini-1.5-flash",           # Legacy balanced
]

ALL_MODELS = [
    ("Gemini 3 (Preview)", MODELS_V3),
    ("Gemini 2.5", MODELS_V25),
    ("Gemini 2.0", MODELS_V2),
    ("Gemini 1.5", MODELS_V1),
]

RESULTS_FILE = Path(__file__).parent / "test_results.json"


def test_model(model_id: str, is_v3: bool = False) -> dict:
    """Test a single model and return results."""
    try:
        import litellm

        print(f"  ⏳ Testing {model_id}...", end=" ", flush=True)
        start = time.time()

        # Build kwargs common to all models
        kwargs = dict(
            model=model_id,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Respond with ONLY valid JSON (no markdown, no explanation). "
                        'Use this exact format: {"model": "<your name>", "status": "ok", '
                        '"summary": "One sentence about ATS-optimized resumes."}'
                    ),
                }
            ],
            max_tokens=512,
            # No temperature for Gemini 3+ (uses API default of 1.0)
            # Temperature 0.3 for Gemini 2.x and earlier
            **({} if is_v3 else {"temperature": 0.3}),
        )

        response = litellm.completion(**kwargs)

        elapsed = time.time() - start
        content = response.choices[0].message.content.strip()
        usage = response.usage

        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        # Try to parse JSON response
        parsed = None
        parse_ok = False
        try:
            parsed = json.loads(content)
            parse_ok = True
        except json.JSONDecodeError:
            pass

        finish = response.choices[0].finish_reason or "unknown"

        print(f"✅ {elapsed:.1f}s (↑{tokens_in} ↓{tokens_out} [{finish}])")

        return {
            "model": model_id,
            "group": "v3" if is_v3 else "v25/v2/v1",
            "success": True,
            "latency_s": round(elapsed, 2),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "finish_reason": finish,
            "parsed_json": parse_ok,
            "preview": content[:150].replace("\n", " "),
        }

    except Exception as e:
        elapsed = time.time() - start if "start" in dir() else 0
        error_str = str(e)[:120]
        print(f"❌ ({elapsed:.1f}s) — {error_str}")
        return {
            "model": model_id,
            "group": "v3" if is_v3 else "v25/v2/v1",
            "success": False,
            "latency_s": round(elapsed, 2),
            "error": error_str,
        }


def print_summary(results: list[dict]):
    """Print a formatted summary table."""
    print("\n" + "=" * 76)
    print("  MODEL TEST RESULTS  ".center(76, "─"))
    print("=" * 76)

    working = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    if working:
        print(f"\n  ✅ Working models ({len(working)}):")
        print(f"  {'Model':<44} {'Latency':<10} {'Tokens':<14} {'JSON':<6}")
        print(f"  {'─'*44} {'─'*10} {'─'*14} {'─'*6}")
        for r in sorted(working, key=lambda x: x["latency_s"]):
            tokens = f"{r['tokens_in']}↑{r['tokens_out']}↓"
            json_ok = "✓" if r.get("parsed_json") else "✗"
            model_short = r["model"].replace("gemini/gemini-", "")
            print(f"  gemini-{model_short:<38} {r['latency_s']:<8.1f}s {tokens:<14} {json_ok:<6}")

    if failed:
        print(f"\n  ❌ Failed models ({len(failed)}):")
        for r in failed:
            model_short = r["model"].replace("gemini/gemini-", "")
            print(f"  - gemini-{model_short}: {r.get('error', 'Unknown')[:100]}")

    # Recommendation
    print("\n" + "─" * 76)
    if working:
        # Filter to preferred groups (v25 first, then fastest overall)
        v25_working = [r for r in working if "2.5" in r["model"]]
        v3_working = [r for r in working if "3-" in r["model"]]
        fastest = min(working, key=lambda x: x["latency_s"])

        print(f"  💡 Recommendations for LLM_DEFAULT_MODEL:")

        if v25_working:
            best_v25 = min(v25_working, key=lambda x: x["latency_s"])
            print(f"     • Best Gemini 2.5:  {best_v25['model']} ({best_v25['latency_s']}s)")
        if v3_working:
            best_v3 = min(v3_working, key=lambda x: x["latency_s"])
            print(f"     • Best Gemini 3:    {best_v3['model']} ({best_v3['latency_s']}s)")
        print(f"     • Fastest overall:  {fastest['model']} ({fastest['latency_s']}s)")

        plan_default = "gemini/gemini-2.5-pro-preview-03-25"
        default_working = any(r["model"] == plan_default and r["success"] for r in working)
        if default_working:
            print(f"\n     ✓ Plan default ({plan_default}) is WORKING.")
        else:
            print(f"\n     ⚠ Plan default ({plan_default}) is NOT working.")
            print(f"        Update LLM_DEFAULT_MODEL in backend/.env with a working model above.")

        print(f"\n  📋 Set in backend/.env:")
        print(f"     LLM_DEFAULT_MODEL=\"{working[0]['model']}\"")
    else:
        print("  ❌ No models working. Check your GEMINI_API_KEY in backend/.env")

    print("─" * 76)


if __name__ == "__main__":
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your-gemini-api-key-here":
        print("❌ GEMINI_API_KEY is not set in backend/.env")
        print("   Edit backend/.env and set your actual Gemini API key.")
        print("   Get one at: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    print(f"\n  🔑 API key found: {api_key[:8]}...{api_key[-4:]}")
    print(f"  📋 Testing {sum(len(m) for _, m in ALL_MODELS)} models across 4 generations...\n")

    results = []
    for group_name, models in ALL_MODELS:
        print(f"  ── {group_name} ──")
        is_v3 = "Gemini 3" in group_name
        for model in models:
            result = test_model(model, is_v3=is_v3)
            results.append(result)
        print()

    # Save raw results
    RESULTS_FILE.write_text(json.dumps(results, indent=2))
    print(f"  📁 Raw results saved to: {RESULTS_FILE}")

    print_summary(results)
