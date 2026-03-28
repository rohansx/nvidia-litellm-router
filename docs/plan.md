# Implementation Plan

## Project Scope

A Python config generator that produces a LiteLLM proxy config for routing across all free NVIDIA NIM models with latency-based routing, automatic failover, and tier-based model selection.

## File Structure

```
nvidia-litellm-router/
├── setup.py              # Config generator (main entry point)
├── config.yaml           # Generated LiteLLM config (output)
├── models.json           # Generated model registry (output)
├── test_proxy.py         # Smoke tests for running proxy
├── requirements.txt      # Python dependencies
├── Dockerfile            # Optional containerized deployment
├── .env.example          # Template for environment variables
├── README.md             # Usage guide (from original spec)
├── examples/
│   ├── rust_usage.rs     # Rust async-openai example
│   └── python_usage.py   # Python openai example
└── docs/
    ├── architecture.md   # System design and data flow
    ├── tech-specs.md     # Technical specifications
    ├── plan.md           # This file
    └── phases.md         # Phased rollout plan
```

## Implementation Tasks

### Phase 1: Core (MVP)

| # | Task | File | Description |
|---|------|------|-------------|
| 1 | Hardcoded model registry | `setup.py` | Define `KNOWN_FREE_CHAT_MODELS` with 21 models, tiers, and context windows |
| 2 | API model discovery | `setup.py` | `discover_nvidia_models()` — GET /v1/models, handle errors gracefully |
| 3 | Chat model filter | `setup.py` | `filter_chat_models()` — exclude non-chat models by keyword |
| 4 | Model merge logic | `setup.py` | Merge discovered models with hardcoded list, deduplicate by ID |
| 5 | Config generator | `setup.py` | `build_litellm_config()` — produce model_list with 3 group layers + router/litellm settings |
| 6 | Config writer | `setup.py` | Write config.yaml and models.json |
| 7 | CLI output | `setup.py` | Print usage instructions after generation |

### Phase 2: Multi-Provider

| # | Task | File | Description |
|---|------|------|-------------|
| 8 | Bonus providers | `setup.py` | `build_bonus_providers_config()` — add Groq, Cerebras, OpenCode Zen if keys present |
| 9 | Fallback chains | `setup.py` | Define cross-tier fallback routing |

### Phase 3: Testing & Examples

| # | Task | File | Description |
|---|------|------|-------------|
| 10 | Smoke test suite | `test_proxy.py` | Test nvidia-auto, nvidia-coding, nvidia-reasoning, nvidia-fast |
| 11 | Rust example | `examples/rust_usage.rs` | async-openai client pointing at proxy |
| 12 | Python example | `examples/python_usage.py` | openai client pointing at proxy |

### Phase 4: Packaging

| # | Task | File | Description |
|---|------|------|-------------|
| 13 | Requirements file | `requirements.txt` | Pin dependencies |
| 14 | Env template | `.env.example` | Document all env vars |
| 15 | Docker support | `Dockerfile` or docs | Document docker run command |
| 16 | README | `README.md` | Full usage guide |

## Dependencies

```
litellm
openai
requests
pyyaml
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| NVIDIA removes free tier | Low | High | Bonus providers (Groq, Cerebras) as backup |
| Model IDs change | Medium | Medium | Hardcoded list + API discovery merge handles this |
| LiteLLM config format changes | Low | Medium | Pin litellm version in requirements |
| Rate limits hit with multiple users | High | Low | Latency routing naturally spreads load; cooldown handles 429s |
| Discovery returns non-chat models | Medium | Low | Keyword filter + hardcoded list as ground truth |

## Non-Goals

- No web UI / dashboard (use LiteLLM's built-in UI if needed)
- No persistent logging or analytics
- No model fine-tuning or custom prompts
- No authentication beyond master key
- No paid model support (free tier only)
