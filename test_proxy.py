#!/usr/bin/env python3
"""
Quick test: hit the LiteLLM proxy and verify routing works.
Run this AFTER starting: litellm --config config.yaml --port 4000
"""

import openai
import time
import sys

PROXY_URL = "http://localhost:4000"
MASTER_KEY = "sk-litellm-master"

client = openai.OpenAI(base_url=PROXY_URL, api_key=MASTER_KEY)


def test_model(model_name: str, prompt: str = "Say 'hello' in one word."):
    print(f"\n{'='*50}")
    print(f"Testing: {model_name}")
    print(f"{'='*50}")
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.1,
        )
        elapsed = time.time() - start
        text = resp.choices[0].message.content.strip()
        actual_model = resp.model
        print(f"  Response: {text[:100]}")
        print(f"  Routed to: {actual_model}")
        print(f"  Latency: {elapsed:.2f}s")
        print(f"  Status: OK")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  Error: {e}")
        print(f"  Latency: {elapsed:.2f}s")
        print(f"  Status: FAILED")
        return False


def main():
    print("NVIDIA LiteLLM Router - Test Suite")
    print(f"Proxy: {PROXY_URL}")
    print()

    models_to_test = [
        "nvidia-auto",
        "nvidia-coding",
        "nvidia-reasoning",
        "nvidia-fast",
    ]

    results = {}
    for model in models_to_test:
        ok = test_model(model)
        results[model] = ok

    print(f"\n\n{'='*50}")
    print("RESULTS")
    print(f"{'='*50}")
    for model, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {model:25s} {status}")

    passed = sum(1 for v in results.values() if v)
    print(f"\n  {passed}/{len(results)} passed")

    if passed == 0:
        print("\n  All tests failed. Check:")
        print("  1. Is litellm proxy running? (litellm --config config.yaml)")
        print("  2. Is NVIDIA_API_KEY set?")
        print("  3. Check litellm logs for errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
