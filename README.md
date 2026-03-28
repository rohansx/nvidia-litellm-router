# nvidia-litellm-router

Auto-route across **all NVIDIA NIM free models** with latency-based routing, automatic failover, and smart tier-based model selection. Zero cost.

## What it does

- Discovers all free models on NVIDIA NIM (Kimi K2.5, DeepSeek R1/V3, Llama 3.3, Qwen3, Nemotron, Mistral, etc.)
- Generates a [LiteLLM](https://github.com/BerriAI/litellm) proxy config with **latency-based routing**
- Automatically picks the **fastest** model for each request
- **Failover**: rate limit hit → retries → routes to next model
- **Cooldown**: bad model gets benched for 60s, auto-recovers
- **Tier routing**: ask for `nvidia-coding` and only coding models compete
- Optionally adds OpenCode Zen, Groq, Cerebras free models to the pool

## Quick start

```bash
# 1. Get your free NVIDIA API key
#    → https://build.nvidia.com/settings/api-keys

# 2. Setup
pip install -r requirements.txt
export NVIDIA_API_KEY=nvapi-xxxx

# 3. Generate config
python setup.py

# 4. Start proxy
litellm --config config.yaml --port 4000

# 5. Use it
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master" \
  -H "Content-Type: application/json" \
  -d '{"model": "nvidia-auto", "messages": [{"role": "user", "content": "hello"}]}'
```

## Available model groups

| Model name | Routes to | Use case |
|---|---|---|
| `nvidia-auto` | Fastest across ALL 20+ models | Default, use this |
| `nvidia-coding` | Kimi K2.5, Qwen Coder, etc. | Code generation, debugging |
| `nvidia-reasoning` | DeepSeek R1, Nemotron Ultra, Llama 405B | Hard problems, math, planning |
| `nvidia-general` | Llama 70B, Qwen 72B, Mistral Large | Balanced tasks |
| `nvidia-fast` | Phi-4, Nemotron Nano, Llama 8B, Gemma | Quick responses, high throughput |
| `<model-name>` | Specific model directly | e.g. `kimi-k2-instruct` |

## Add more free providers (optional)

```bash
export OPENCODE_API_KEY=xxx    # OpenCode Zen: Big Pickle, MiMo, MiniMax free
export GROQ_API_KEY=xxx        # Groq: Llama 70B, Mixtral (30 RPM)
export CEREBRAS_API_KEY=xxx    # Cerebras: Llama 70B (ultra-fast inference)

python setup.py  # re-run to add them to config
```

## Use from Rust (ctxgraph / CloakPipe)

```rust
let config = OpenAIConfig::new()
    .with_api_key("sk-litellm-master")
    .with_api_base("http://localhost:4000/v1");
let client = Client::with_config(config);

// LiteLLM auto-picks the fastest free model
let request = CreateChatCompletionRequestArgs::default()
    .model("nvidia-auto")
    .messages(vec![...])
    .build()?;
```

See `examples/rust_usage.rs` for full example.

## Use from Python

```python
import openai
client = openai.OpenAI(base_url="http://localhost:4000", api_key="sk-litellm-master")
resp = client.chat.completions.create(
    model="nvidia-auto",
    messages=[{"role": "user", "content": "hello"}]
)
print(resp.choices[0].message.content)
print(f"Routed to: {resp.model}")
```

## How routing works

```
Your request → LiteLLM proxy (localhost:4000)
                    │
                    ├─ Measures latency of all deployments
                    ├─ Picks fastest healthy model
                    ├─ If 429/error → retry with backoff
                    ├─ If still failing → failover to next model
                    ├─ If model slow → deprioritized automatically
                    └─ Response back to you
```

## Docker

```bash
docker run -d \
  -p 4000:4000 \
  -e NVIDIA_API_KEY=nvapi-xxxx \
  -v $(pwd)/config.yaml:/app/config.yaml \
  ghcr.io/berriai/litellm:main-stable \
  --config /app/config.yaml
```

## Testing

```bash
# Start proxy first
litellm --config config.yaml --port 4000

# Run smoke tests
python test_proxy.py
```

## Limits

- NVIDIA NIM free tier: ~40 RPM, 1000 credits (then request more)
- OpenCode Zen free: ~200 req/5hr for free models
- Groq free: 30 RPM, 14.4k tokens/min
- Cerebras free: 30 RPM, 1M tokens/day

With all providers combined, you get **~140 RPM** of free inference across 25+ models.

## Docs

- [Architecture](docs/architecture.md) — system design, data flow, tier classification
- [Tech Specs](docs/tech-specs.md) — config schema, env vars, routing details
- [Plan](docs/plan.md) — implementation tasks, risks, file structure
- [Phases](docs/phases.md) — phased rollout with acceptance criteria
