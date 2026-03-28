#!/usr/bin/env python3
"""
nvidia-litellm-router: Auto-discover all NVIDIA NIM free models and generate
a LiteLLM proxy config with latency-based routing + automatic failover.

Usage:
    1. export NVIDIA_API_KEY=nvapi-xxxx
    2. python setup.py          # discovers models, writes config
    3. litellm --config config.yaml  # starts the proxy
    4. Hit http://localhost:4000/v1/chat/completions with model: "nvidia-auto"
"""

import json
import os
import sys
import requests
import yaml

NVIDIA_API_BASE = "https://integrate.api.nvidia.com/v1"

# --- Known good free LLM models on NVIDIA NIM (as of March 2026) ---
# We hardcode the known-working chat models because NVIDIA's /models endpoint
# returns ALL models (embedding, vision, audio, etc.) and many don't support
# /chat/completions. This list is the curated LLM subset.
#
# The script will also try to auto-discover from the API and merge.

KNOWN_FREE_CHAT_MODELS = [
    # === Top Tier (Frontier-class) ===
    {"id": "deepseek-ai/deepseek-r1", "name": "DeepSeek R1", "tier": "reasoning", "ctx": 128000},
    {"id": "deepseek-ai/deepseek-v3-0324", "name": "DeepSeek V3", "tier": "general", "ctx": 128000},
    {"id": "nvidia/llama-3.1-nemotron-ultra-253b-v1", "name": "Nemotron Ultra 253B", "tier": "reasoning", "ctx": 131072},
    {"id": "nvidia/llama-3.3-nemotron-super-49b-v1", "name": "Nemotron Super 49B", "tier": "general", "ctx": 131072},
    {"id": "nvidia/llama-3.1-nemotron-nano-8b-v1", "name": "Nemotron Nano 8B", "tier": "fast", "ctx": 131072},

    # === Strong Open Models ===
    {"id": "meta/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "tier": "general", "ctx": 131072},
    {"id": "meta/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "tier": "fast", "ctx": 131072},
    {"id": "meta/llama-3.1-70b-instruct", "name": "Llama 3.1 70B", "tier": "general", "ctx": 131072},
    {"id": "meta/llama-3.1-405b-instruct", "name": "Llama 3.1 405B", "tier": "reasoning", "ctx": 131072},

    # === Coding Specialists ===
    {"id": "moonshotai/kimi-k2-instruct", "name": "Kimi K2.5", "tier": "coding", "ctx": 131072},
    {"id": "qwen/qwen3-235b-instruct", "name": "Qwen3 235B", "tier": "reasoning", "ctx": 131072},
    {"id": "qwen/qwen2.5-coder-32b-instruct", "name": "Qwen 2.5 Coder 32B", "tier": "coding", "ctx": 32768},
    {"id": "qwen/qwen2.5-72b-instruct", "name": "Qwen 2.5 72B", "tier": "general", "ctx": 131072},

    # === Fast / Efficient ===
    {"id": "mistralai/mistral-large-2-instruct", "name": "Mistral Large 2", "tier": "general", "ctx": 131072},
    {"id": "mistralai/mixtral-8x22b-instruct-v0.1", "name": "Mixtral 8x22B", "tier": "general", "ctx": 65536},
    {"id": "mistralai/mistral-small-24b-instruct-2501", "name": "Mistral Small 24B", "tier": "fast", "ctx": 32768},
    {"id": "google/gemma-2-27b-it", "name": "Gemma 2 27B", "tier": "fast", "ctx": 8192},
    {"id": "microsoft/phi-4", "name": "Phi 4", "tier": "fast", "ctx": 16384},

    # === Reasoning ===
    {"id": "nvidia/deepseek-r1-fp4", "name": "DeepSeek R1 FP4 (NVIDIA)", "tier": "reasoning", "ctx": 128000},

    # === MiniMax / GLM ===
    {"id": "thudm/glm-4-9b-chat", "name": "GLM-4 9B", "tier": "fast", "ctx": 131072},
]


def discover_nvidia_models(api_key: str) -> list[dict]:
    """Try to fetch model list from NVIDIA API."""
    print("[*] Attempting to discover models from NVIDIA API...")
    try:
        resp = requests.get(
            f"{NVIDIA_API_BASE}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            print(f"[+] Discovered {len(models)} total models from API")
            return models
        else:
            print(f"[!] API returned {resp.status_code}, using hardcoded list")
            return []
    except Exception as e:
        print(f"[!] Discovery failed ({e}), using hardcoded list")
        return []


def filter_chat_models(api_models: list[dict]) -> list[str]:
    """Filter API models to only chat-capable LLMs."""
    chat_ids = set()
    for m in api_models:
        mid = m.get("id", "")
        skip_keywords = ["embed", "rerank", "vlm", "audio", "image", "video",
                         "neva", "fuyu", "kosmos", "sdxl", "stable-diffusion",
                         "grounding", "nv-rerankqa", "parakeet", "canary"]
        if any(kw in mid.lower() for kw in skip_keywords):
            continue
        chat_ids.add(mid)
    return list(chat_ids)


def build_litellm_config(models: list[dict], api_key_env: str = "NVIDIA_API_KEY") -> dict:
    """Generate LiteLLM config YAML structure."""

    model_list = []

    # --- Group 1: "nvidia-auto" — all models, latency-based routing picks best ---
    for m in models:
        model_list.append({
            "model_name": "nvidia-auto",
            "litellm_params": {
                "model": f"nvidia_nim/{m['id']}",
                "api_key": f"os.environ/{api_key_env}",
                "api_base": NVIDIA_API_BASE,
                "timeout": 30,
                "stream_timeout": 60,
            },
        })

    # --- Group 2: Tier-based groups for smart routing ---
    tier_groups = {}
    for m in models:
        tier = m.get("tier", "general")
        if tier not in tier_groups:
            tier_groups[tier] = []
        tier_groups[tier].append(m)

    for tier, tier_models in tier_groups.items():
        for m in tier_models:
            model_list.append({
                "model_name": f"nvidia-{tier}",
                "litellm_params": {
                    "model": f"nvidia_nim/{m['id']}",
                    "api_key": f"os.environ/{api_key_env}",
                    "api_base": NVIDIA_API_BASE,
                    "timeout": 30,
                    "stream_timeout": 60,
                },
            })

    # --- Group 3: Individual model access ---
    for m in models:
        short_name = m["id"].split("/")[-1]
        model_list.append({
            "model_name": short_name,
            "litellm_params": {
                "model": f"nvidia_nim/{m['id']}",
                "api_key": f"os.environ/{api_key_env}",
                "api_base": NVIDIA_API_BASE,
            },
        })

    # Build fallback chains: tier-based fallbacks
    fallbacks = [
        {"nvidia-coding": ["nvidia-reasoning", "nvidia-general"]},
        {"nvidia-reasoning": ["nvidia-general", "nvidia-coding"]},
        {"nvidia-general": ["nvidia-fast", "nvidia-reasoning"]},
        {"nvidia-fast": ["nvidia-general"]},
    ]

    config = {
        "model_list": model_list,
        "litellm_settings": {
            "num_retries": 3,
            "request_timeout": 30,
            "fallbacks": fallbacks,
            "set_verbose": False,
            "drop_params": True,
        },
        "router_settings": {
            "routing_strategy": "latency-based-routing",
            "num_retries": 3,
            "cooldown_time": 60,
            "retry_after": 5,
            "allowed_fails": 2,
            "enable_pre_call_checks": True,
        },
        "general_settings": {
            "master_key": "sk-litellm-master",
            "alerting": ["slack"] if os.environ.get("SLACK_WEBHOOK_URL") else [],
        },
    }

    return config


def build_bonus_providers_config() -> list[dict]:
    """Optional: Add other free providers for even more failover coverage."""
    extras = []

    # OpenCode Zen free models
    if os.environ.get("OPENCODE_API_KEY"):
        zen_models = [
            "big-pickle", "minimax-m2.5-free", "mimo-v2-pro-free",
            "nemotron-3-super-free",
        ]
        for m in zen_models:
            extras.append({
                "model_name": "nvidia-auto",
                "litellm_params": {
                    "model": f"openai/{m}",
                    "api_key": "os.environ/OPENCODE_API_KEY",
                    "api_base": "https://opencode.ai/zen/v1",
                    "timeout": 30,
                },
            })
        print(f"[+] Added {len(zen_models)} OpenCode Zen free models")

    # Groq free tier
    if os.environ.get("GROQ_API_KEY"):
        groq_models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
        for m in groq_models:
            extras.append({
                "model_name": "nvidia-auto",
                "litellm_params": {
                    "model": f"groq/{m}",
                    "api_key": "os.environ/GROQ_API_KEY",
                },
            })
        print(f"[+] Added {len(groq_models)} Groq free models")

    # Cerebras free tier
    if os.environ.get("CEREBRAS_API_KEY"):
        extras.append({
            "model_name": "nvidia-auto",
            "litellm_params": {
                "model": "cerebras/llama-3.3-70b",
                "api_key": "os.environ/CEREBRAS_API_KEY",
            },
        })
        print("[+] Added Cerebras Llama 3.3 70B")

    return extras


def main():
    api_key = os.environ.get("NVIDIA_API_KEY", "")

    if not api_key:
        print("=" * 60)
        print("NVIDIA_API_KEY not set. That's fine — generating config")
        print("with hardcoded model list. Set the key before running LiteLLM.")
        print()
        print("Get your free key: https://build.nvidia.com/settings/api-keys")
        print("=" * 60)

    # Discover models
    api_models = discover_nvidia_models(api_key) if api_key else []
    discovered_ids = filter_chat_models(api_models) if api_models else []

    # Merge discovered with known
    known_ids = {m["id"] for m in KNOWN_FREE_CHAT_MODELS}
    final_models = list(KNOWN_FREE_CHAT_MODELS)

    new_count = 0
    for mid in discovered_ids:
        if mid not in known_ids:
            final_models.append({
                "id": mid,
                "name": mid.split("/")[-1],
                "tier": "general",
                "ctx": 131072,
            })
            new_count += 1

    if new_count:
        print(f"[+] Discovered {new_count} additional models not in hardcoded list")

    print(f"\n[*] Total models in config: {len(final_models)}")
    print(f"    Tiers: { {t: sum(1 for m in final_models if m.get('tier') == t) for t in set(m.get('tier', 'general') for m in final_models)} }")

    # Build config
    config = build_litellm_config(final_models)

    # Add bonus providers if keys present
    extras = build_bonus_providers_config()
    if extras:
        config["model_list"].extend(extras)

    # Write config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=120)

    print(f"\n[+] Config written to {config_path}")
    print(f"    Total deployments: {len(config['model_list'])}")
    print()

    # Print usage
    print("=" * 60)
    print("USAGE:")
    print("=" * 60)
    print()
    print("  # 1. Set your API key(s)")
    print("  export NVIDIA_API_KEY=nvapi-xxxx")
    print("  export OPENCODE_API_KEY=xxx    # optional, for Zen free models")
    print("  export GROQ_API_KEY=xxx        # optional, for Groq free tier")
    print("  export CEREBRAS_API_KEY=xxx    # optional, for Cerebras free tier")
    print()
    print("  # 2. Start the proxy")
    print("  litellm --config config.yaml --port 4000")
    print()
    print("  # 3. Use it (OpenAI-compatible)")
    print('  curl http://localhost:4000/v1/chat/completions \\')
    print('    -H "Authorization: Bearer sk-litellm-master" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"model": "nvidia-auto", "messages": [{"role": "user", "content": "hello"}]}\'')
    print()
    print("  MODELS AVAILABLE:")
    print("    nvidia-auto      → routes to fastest across ALL models")
    print("    nvidia-coding    → routes to fastest coding model")
    print("    nvidia-reasoning → routes to fastest reasoning model")
    print("    nvidia-general   → routes to fastest general model")
    print("    nvidia-fast      → routes to fastest small/efficient model")
    print("    <model-name>     → direct access (e.g. 'deepseek-r1', 'kimi-k2-instruct')")
    print()
    print("  WHAT HAPPENS AUTOMATICALLY:")
    print("    - Picks fastest model based on real-time latency")
    print("    - Rate limit (429)? → retries with backoff, then fails over")
    print("    - Credits exhausted? → auto-routes to next provider")
    print("    - Slow response? → latency routing avoids it next time")
    print("    - Model down? → 60s cooldown, then auto-recovers")
    print("=" * 60)

    # Also write a summary of models
    summary_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models.json")
    with open(summary_path, "w") as f:
        json.dump(final_models, f, indent=2)
    print(f"\n[+] Model summary written to {summary_path}")


if __name__ == "__main__":
    main()
