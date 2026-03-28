# Technical Specifications

## Runtime Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.10+ | f-string type hints, `list[dict]` syntax |
| litellm | latest | Proxy runtime |
| openai | 1.x+ | Test client, example usage |
| requests | any | NVIDIA API model discovery |
| pyyaml | any | Config file generation |

## API Endpoints

### NVIDIA NIM
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Auth**: Bearer token via `NVIDIA_API_KEY`
- **Endpoints used**:
  - `GET /v1/models` — model discovery
  - `POST /v1/chat/completions` — inference (via LiteLLM)
- **Rate limits**: ~40 RPM, 1000 free credits (can request more)
- **Protocol**: OpenAI-compatible

### LiteLLM Proxy (generated)
- **Listen**: `http://localhost:4000`
- **Auth**: Bearer token `sk-litellm-master` (configurable)
- **Endpoints exposed**:
  - `POST /v1/chat/completions` — main inference endpoint
  - `GET /v1/models` — list available model groups
  - `GET /health` — proxy health check

## Config Schema (`config.yaml`)

```yaml
model_list:           # Array of deployment objects
  - model_name: str   # Virtual model name (nvidia-auto, nvidia-coding, etc.)
    litellm_params:
      model: str      # "nvidia_nim/{org}/{model-id}"
      api_key: str    # "os.environ/NVIDIA_API_KEY" (env reference)
      api_base: str   # "https://integrate.api.nvidia.com/v1"
      timeout: int    # 30s request timeout
      stream_timeout: int  # 60s streaming timeout

litellm_settings:
  num_retries: 3          # Retries per deployment before failover
  request_timeout: 30     # Global request timeout
  fallbacks: [...]        # Cross-tier fallback chains
  drop_params: true       # Drop unsupported params silently

router_settings:
  routing_strategy: "latency-based-routing"
  cooldown_time: 60       # Seconds to bench a failing model
  retry_after: 5          # Seconds between retries
  allowed_fails: 2        # Consecutive failures before cooldown
  enable_pre_call_checks: true

general_settings:
  master_key: str         # Proxy auth key
  alerting: [str]         # Optional Slack alerting
```

## Model Registry Schema (`models.json`)

```json
[
  {
    "id": "deepseek-ai/deepseek-r1",   // NVIDIA NIM model identifier
    "name": "DeepSeek R1",              // Human-readable name
    "tier": "reasoning",                // One of: reasoning, coding, general, fast
    "ctx": 128000                       // Context window in tokens
  }
]
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NVIDIA_API_KEY` | Yes (at runtime) | NVIDIA NIM API key. Free at build.nvidia.com |
| `OPENCODE_API_KEY` | No | OpenCode Zen free models (Big Pickle, MiniMax, etc.) |
| `GROQ_API_KEY` | No | Groq free tier (Llama 70B, Mixtral) |
| `CEREBRAS_API_KEY` | No | Cerebras free tier (Llama 70B ultra-fast) |
| `SLACK_WEBHOOK_URL` | No | Enable Slack alerting for proxy errors |

## Model Discovery Heuristics

The `filter_chat_models()` function excludes non-chat models by keyword matching on model IDs:

**Excluded keywords**: embed, rerank, vlm, audio, image, video, neva, fuyu, kosmos, sdxl, stable-diffusion, grounding, nv-rerankqa, parakeet, canary

This is a best-effort filter. The hardcoded `KNOWN_FREE_CHAT_MODELS` list is the authoritative source for known-working models.

## Routing Strategy Details

### Latency-Based Routing
LiteLLM tracks the Time-To-First-Byte (TTFB) for each deployment. When a request arrives for a model group (e.g., `nvidia-auto`), it selects the deployment with the lowest weighted average TTFB.

### Cooldown Mechanics
- After `allowed_fails` (2) consecutive failures, the deployment enters cooldown
- Cooldown lasts `cooldown_time` (60) seconds
- After cooldown, the deployment is automatically re-added to the pool
- If ALL deployments in a group are in cooldown, fallback chains activate

### Retry Behavior
- On 429 or 5xx: retry up to `num_retries` (3) times
- Wait `retry_after` (5) seconds between retries
- If all retries exhausted: increment failure counter, try next deployment
- `drop_params: true` silently drops params not supported by a model (prevents errors from model-specific param differences)

## Deployment Count Calculation

For N models with T unique tiers:
- `nvidia-auto` group: N deployments
- Tier groups: N deployments total (each model in its tier)
- Individual access: N deployments (one per model)
- **Total deployments**: 3N

With 21 hardcoded models: **63 deployments** in the base config.

## Docker Deployment

```bash
docker run -d \
  -p 4000:4000 \
  -e NVIDIA_API_KEY=nvapi-xxxx \
  -v $(pwd)/config.yaml:/app/config.yaml \
  ghcr.io/berriai/litellm:main-stable \
  --config /app/config.yaml
```

No custom Docker image needed — mount the generated config into the official LiteLLM image.
