# Architecture

## System Overview

nvidia-litellm-router is a config generator + proxy layer that sits between your application and 20+ free LLM endpoints on NVIDIA NIM (plus optional Groq, Cerebras, OpenCode Zen). It uses LiteLLM as the proxy runtime.

```
┌──────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
│ Your App     │      │ LiteLLM Proxy        │      │ NVIDIA NIM           │
│ (any lang)   │─────▶│ localhost:4000        │─────▶│ integrate.api.nvidia │
│              │ HTTP  │                      │      │                      │
│ model:       │      │ ┌──────────────────┐ │      │ DeepSeek R1          │
│ "nvidia-auto"│      │ │ Latency Router   │ │      │ DeepSeek V3          │
│              │      │ │                  │ │      │ Nemotron Ultra 253B  │
│              │      │ │ Measures TTFB    │ │      │ Nemotron Super 49B   │
│              │      │ │ per deployment,  │ │      │ Llama 3.3 70B        │
│              │      │ │ picks fastest    │ │      │ Kimi K2.5            │
│              │      │ └──────────────────┘ │      │ Qwen3 235B           │
│              │      │                      │      │ Qwen 2.5 Coder 32B  │
│              │      │ ┌──────────────────┐ │      │ Mistral Large 2      │
│              │      │ │ Failover Engine  │ │      │ Phi-4                │
│              │      │ │                  │ │      │ ... 20+ models       │
│              │      │ │ 429 → retry      │ │      └──────────────────────┘
│              │      │ │ 500 → next model │ │
│              │      │ │ slow → depriori- │ │      ┌──────────────────────┐
│              │      │ │        tize      │ │      │ Bonus Providers      │
│              │      │ └──────────────────┘ │─────▶│ (optional)           │
│              │      │                      │      │ Groq, Cerebras,      │
│              │      │ ┌──────────────────┐ │      │ OpenCode Zen         │
│              │      │ │ Cooldown Manager │ │      └──────────────────────┘
│              │      │ │ 60s bench for    │ │
│              │      │ │ failing models   │ │
│              │      │ └──────────────────┘ │
└──────────────┘      └──────────────────────┘
```

## Components

### 1. Config Generator (`setup.py`)

Single-file Python script. Does three things:

1. **Model Discovery** — Calls `GET /v1/models` on NVIDIA NIM API, filters to chat-capable models using keyword exclusion (skips embedding, vision, audio, etc.)
2. **Model Merging** — Merges discovered models with a hardcoded curated list (`KNOWN_FREE_CHAT_MODELS`). Hardcoded list is authoritative for tier assignments and context window sizes. Discovered-only models get default `general` tier.
3. **Config Generation** — Builds a LiteLLM-compatible YAML config with three model group layers:
   - `nvidia-auto` — all models in one pool
   - `nvidia-{tier}` — tier-based pools (coding, reasoning, general, fast)
   - `{model-short-name}` — direct access to individual models

Outputs: `config.yaml` + `models.json`

### 2. LiteLLM Proxy (runtime, not our code)

LiteLLM is the proxy runtime. We generate its config; it handles:
- OpenAI-compatible HTTP server on port 4000
- Latency-based routing (measures TTFB, picks fastest)
- Retry with exponential backoff on 429/5xx
- Failover to next model in group on persistent failure
- Cooldown: model benched for 60s after `allowed_fails` consecutive failures
- Cross-tier fallback chains (e.g., coding → reasoning → general)

### 3. Test Suite (`test_proxy.py`)

Smoke tests that hit the running proxy and verify each tier routes successfully. Reports latency and which model was selected.

## Data Flow

```
Request: model="nvidia-coding", messages=[...]
    │
    ▼
LiteLLM receives request
    │
    ▼
Router checks "nvidia-coding" group (2 deployments: Kimi K2.5, Qwen Coder 32B)
    │
    ▼
Latency router picks deployment with lowest recent TTFB
    │
    ├─ Success → return response (model field shows which was used)
    │
    ├─ 429 Rate Limited → retry up to 3x with backoff
    │   ├─ Retry succeeds → return response
    │   └─ All retries fail → failover
    │
    └─ Failover chain: nvidia-coding → nvidia-reasoning → nvidia-general
        └─ Try next group's fastest model
```

## Model Tier Classification

| Tier | Criteria | Models |
|------|----------|--------|
| `reasoning` | Chain-of-thought, hard problems, 100B+ params | DeepSeek R1, Nemotron Ultra 253B, Llama 405B, Qwen3 235B |
| `coding` | Code-specialized training or benchmarks | Kimi K2.5, Qwen 2.5 Coder 32B |
| `general` | Strong all-rounders, 49B-72B range | DeepSeek V3, Llama 70B variants, Qwen 72B, Mistral Large, Mixtral |
| `fast` | Small/efficient, <30B, low latency | Nemotron Nano 8B, Llama 8B, Phi-4, Gemma 27B, Mistral Small, GLM-4 9B |

## Fallback Chains

```
nvidia-coding    → nvidia-reasoning → nvidia-general
nvidia-reasoning → nvidia-general   → nvidia-coding
nvidia-general   → nvidia-fast      → nvidia-reasoning
nvidia-fast      → nvidia-general
```

## Security Model

- API keys are never written to config.yaml — referenced via `os.environ/KEY_NAME`
- Master key (`sk-litellm-master`) authenticates proxy clients — should be changed in production
- All communication to NVIDIA NIM is over HTTPS
- No persistent storage of requests/responses
