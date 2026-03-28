# Phased Rollout

## Phase 1: Core Config Generator (MVP)

**Goal**: Generate a working LiteLLM config that routes across all NVIDIA NIM free models.

**Deliverables**:
- `setup.py` with hardcoded model list + API discovery
- Generates `config.yaml` with latency-based routing
- Generates `models.json` model registry
- Works without NVIDIA_API_KEY (uses hardcoded list only)
- Works with NVIDIA_API_KEY (discovers + merges)

**Acceptance Criteria**:
- `python setup.py` produces valid config.yaml
- `litellm --config config.yaml` starts without errors
- `curl localhost:4000/v1/chat/completions -d '{"model":"nvidia-auto",...}'` returns a response
- Response headers/body show which model was selected

**Model Groups Created**:
- `nvidia-auto` — 21 deployments (all models)
- `nvidia-reasoning` — 5 deployments
- `nvidia-coding` — 2 deployments
- `nvidia-general` — 7 deployments
- `nvidia-fast` — 6 deployments
- 21 individual model names

---

## Phase 2: Multi-Provider Expansion

**Goal**: Add Groq, Cerebras, and OpenCode Zen free models to the routing pool.

**Deliverables**:
- `build_bonus_providers_config()` in setup.py
- Bonus models join `nvidia-auto` pool (same latency routing)
- Cross-tier fallback chains defined

**Acceptance Criteria**:
- With `GROQ_API_KEY` set: Groq models appear in config
- With `CEREBRAS_API_KEY` set: Cerebras models appear in config
- With `OPENCODE_API_KEY` set: OpenCode Zen models appear in config
- Fallover works: block NVIDIA → request routes to Groq/Cerebras

**Combined Capacity**:
| Provider | RPM | Models Added |
|----------|-----|-------------|
| NVIDIA NIM | ~40 | 21 |
| OpenCode Zen | ~40/hr | 4 |
| Groq | 30 | 2 |
| Cerebras | 30 | 1 |
| **Total** | **~140** | **28** |

---

## Phase 3: Testing & Examples

**Goal**: Verify routing works end-to-end, provide usage examples.

**Deliverables**:
- `test_proxy.py` — smoke tests hitting each tier
- `examples/rust_usage.rs` — Rust async-openai example
- `examples/python_usage.py` — Python openai example

**Acceptance Criteria**:
- `python test_proxy.py` passes with proxy running
- All 4 tiers (auto, coding, reasoning, fast) return valid responses
- Latency reported for each tier
- Routed model name shown in output

---

## Phase 4: Packaging & Documentation

**Goal**: Make the project easy to set up and deploy.

**Deliverables**:
- `requirements.txt` with pinned dependencies
- `.env.example` with all env vars documented
- Docker deployment instructions
- Complete README with quickstart, model table, routing explanation

**Acceptance Criteria**:
- `pip install -r requirements.txt && python setup.py` works from clean env
- Docker command from README starts working proxy
- All env vars documented with descriptions

---

## Implementation Order

```
Phase 1 (Core)
    │
    ▼
Phase 2 (Multi-Provider)    ← can run setup.py after this
    │
    ▼
Phase 3 (Testing)           ← requires running proxy
    │
    ▼
Phase 4 (Packaging)         ← final polish
```

All phases are in the same `setup.py` file (phases 1-2) plus supporting files (phases 3-4). Total implementation is ~350 lines of Python + config.
