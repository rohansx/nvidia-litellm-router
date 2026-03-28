# nvidia-litellm-router

Auto-route across **31 free NVIDIA NIM models** with latency-based routing, automatic failover, and smart tier-based model selection. Zero cost.

## Features

- Latency-based routing — automatically picks the **fastest** healthy model
- **5 model tiers** — auto, coding, reasoning, general, fast
- Automatic **failover** — rate limit hit → retries with backoff → routes to next model
- **Cooldown** — bad model gets benched for 60s, auto-recovers
- **API validation** — hardcoded models verified against live NVIDIA NIM API on each run
- **Multi-provider** — optionally add Groq, Cerebras, OpenCode Zen for ~140 RPM combined
- **OpenAI-compatible** — works with any OpenAI SDK (Python, Rust, TypeScript, Go, etc.)

## Requirements

- Python 3.10+
- A free [NVIDIA NIM API key](https://build.nvidia.com/settings/api-keys)

## Installation

### From source

```bash
git clone https://github.com/rohansx/nvidia-litellm-router.git
cd nvidia-litellm-router
pip install -r requirements.txt
```

### Dependencies

```
litellm        # Proxy runtime
openai         # Test client + Python usage
requests       # NVIDIA API model discovery
pyyaml         # Config generation
```

## Setup

### 1. Get your free NVIDIA API key

Go to [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys) and create a free key.

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```env
NVIDIA_API_KEY=nvapi-xxxx
```

### 3. Generate config

```bash
python setup.py
```

This will:
- Fetch the model list from NVIDIA's API
- Validate your curated models against the live API
- Generate `config.yaml` with latency-based routing across all tiers
- Write `models.json` with the final model registry

### 4. Start the proxy

```bash
litellm --config config.yaml --port 4000
```

### 5. Send a request

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia-auto",
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

The response includes which model was selected in the `model` field.

## Available Model Groups

| Model name | Routes to | Use case |
|---|---|---|
| `nvidia-auto` | Fastest across ALL 31 models | Default, use this |
| `nvidia-coding` | Kimi K2, Qwen3 Coder 480B, Devstral 2, Codestral, Qwen 2.5 Coder | Code generation, debugging |
| `nvidia-reasoning` | DeepSeek V3.2, Qwen 3.5 397B, Nemotron Ultra 253B, Llama 405B | Hard problems, math, planning |
| `nvidia-general` | Llama 4 Maverick/Scout, Mistral Large 2, DeepSeek V3.1, Mixtral | Balanced tasks |
| `nvidia-fast` | Phi 4 Mini, DeepSeek R1 distills, Mistral Small, Gemma 2 | Quick responses, high throughput |
| `<model-name>` | Specific model directly | e.g. `kimi-k2-instruct`, `deepseek-v3.2` |

### Full Model List (31 models)

<details>
<summary>Click to expand</summary>

**Reasoning (6)**
| Model | ID |
|---|---|
| DeepSeek V3.2 | `deepseek-ai/deepseek-v3.2` |
| DeepSeek R1 Distill 32B | `deepseek-ai/deepseek-r1-distill-qwen-32b` |
| Nemotron Ultra 253B | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Llama 3.1 405B | `meta/llama-3.1-405b-instruct` |
| Qwen 3.5 397B | `qwen/qwen3.5-397b-a17b` |
| Qwen 3.5 122B | `qwen/qwen3.5-122b-a10b` |

**Coding (5)**
| Model | ID |
|---|---|
| Kimi K2 | `moonshotai/kimi-k2-instruct` |
| Qwen3 Coder 480B | `qwen/qwen3-coder-480b-a35b-instruct` |
| Qwen 2.5 Coder 32B | `qwen/qwen2.5-coder-32b-instruct` |
| Devstral 2 123B | `mistralai/devstral-2-123b-instruct-2512` |
| Codestral 22B | `mistralai/codestral-22b-instruct-v0.1` |

**General (11)**
| Model | ID |
|---|---|
| DeepSeek V3.1 | `deepseek-ai/deepseek-v3.1` |
| DeepSeek V3.1 Terminus | `deepseek-ai/deepseek-v3.1-terminus` |
| Nemotron Super 49B | `nvidia/llama-3.3-nemotron-super-49b-v1` |
| Llama 3.3 70B | `meta/llama-3.3-70b-instruct` |
| Llama 3.1 70B | `meta/llama-3.1-70b-instruct` |
| Llama 4 Maverick | `meta/llama-4-maverick-17b-128e-instruct` |
| Llama 4 Scout | `meta/llama-4-scout-17b-16e-instruct` |
| Qwen3 Next 80B | `qwen/qwen3-next-80b-a3b-instruct` |
| Mistral Large 2 | `mistralai/mistral-large-2-instruct` |
| Mixtral 8x22B | `mistralai/mixtral-8x22b-instruct-v0.1` |
| Mistral Medium 3 | `mistralai/mistral-medium-3-instruct` |

**Fast (9)**
| Model | ID |
|---|---|
| Nemotron Nano 8B | `nvidia/llama-3.1-nemotron-nano-8b-v1` |
| Llama 3.1 8B | `meta/llama-3.1-8b-instruct` |
| Mistral Small 24B | `mistralai/mistral-small-24b-instruct` |
| Gemma 2 27B | `google/gemma-2-27b-it` |
| Phi 4 Mini | `microsoft/phi-4-mini-instruct` |
| Phi 4 Mini Flash | `microsoft/phi-4-mini-flash-reasoning` |
| DeepSeek R1 Distill 14B | `deepseek-ai/deepseek-r1-distill-qwen-14b` |
| DeepSeek R1 Distill 7B | `deepseek-ai/deepseek-r1-distill-qwen-7b` |
| DeepSeek R1 Distill Llama 8B | `deepseek-ai/deepseek-r1-distill-llama-8b` |

</details>

## Usage Examples

### Python

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-litellm-master",
)

# Auto-route to fastest model
resp = client.chat.completions.create(
    model="nvidia-auto",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.choices[0].message.content)
print(f"Routed to: {resp.model}")

# Target a specific tier
resp = client.chat.completions.create(
    model="nvidia-coding",
    messages=[{"role": "user", "content": "Write a Python quicksort"}],
)
```

### Rust (async-openai)

```rust
// Cargo.toml: async-openai = "0.25", tokio = { version = "1", features = ["full"] }

let config = OpenAIConfig::new()
    .with_api_key("sk-litellm-master")
    .with_api_base("http://localhost:4000/v1");
let client = Client::with_config(config);

let request = CreateChatCompletionRequestArgs::default()
    .model("nvidia-auto")
    .messages(vec![
        ChatCompletionRequestUserMessageArgs::default()
            .content("hello")
            .build()?
            .into(),
    ])
    .build()?;

let response = client.chat().create(request).await?;
```

See [`examples/`](examples/) for full working examples.

### TypeScript / Node.js

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost:4000",
  apiKey: "sk-litellm-master",
});

const resp = await client.chat.completions.create({
  model: "nvidia-auto",
  messages: [{ role: "user", content: "hello" }],
});
```

### curl

```bash
# Auto-route
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master" \
  -H "Content-Type: application/json" \
  -d '{"model": "nvidia-auto", "messages": [{"role": "user", "content": "hello"}]}'

# Target coding models
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master" \
  -H "Content-Type: application/json" \
  -d '{"model": "nvidia-coding", "messages": [{"role": "user", "content": "Write a binary search in Go"}]}'

# Use a specific model
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master" \
  -H "Content-Type: application/json" \
  -d '{"model": "kimi-k2-instruct", "messages": [{"role": "user", "content": "hello"}]}'
```

## How Routing Works

```
Your request → LiteLLM proxy (localhost:4000)
                    │
                    ├─ Measures latency of all deployments
                    ├─ Picks fastest healthy model
                    ├─ If 429/error → retry with backoff (3 retries)
                    ├─ If still failing → failover to next model
                    ├─ If model slow → deprioritized automatically
                    ├─ If model down → 60s cooldown, then auto-recovers
                    └─ Response back to you
```

### Fallback Chains

When all models in a tier fail, requests fall through to the next tier:

```
nvidia-coding    → nvidia-reasoning → nvidia-general
nvidia-reasoning → nvidia-general   → nvidia-coding
nvidia-general   → nvidia-fast      → nvidia-reasoning
nvidia-fast      → nvidia-general
```

## Add More Free Providers (optional)

Add extra API keys to `.env` for more failover coverage:

```env
OPENCODE_API_KEY=xxx    # OpenCode Zen: Big Pickle, MiMo, MiniMax free
GROQ_API_KEY=xxx        # Groq: Llama 70B, Mixtral (30 RPM)
CEREBRAS_API_KEY=xxx    # Cerebras: Llama 70B (ultra-fast inference)
```

Then re-run `python setup.py` to regenerate the config. Bonus models join the `nvidia-auto` pool.

## Docker

```bash
# Generate config first
python setup.py

# Run with official LiteLLM image
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

# Run smoke tests (tests all 5 tiers)
python test_proxy.py
```

## Rate Limits

| Provider | RPM | Notes |
|----------|-----|-------|
| NVIDIA NIM | ~40 | 1000 free credits, request more at build.nvidia.com |
| OpenCode Zen | ~40/hr | Free tier models |
| Groq | 30 | 14.4k tokens/min |
| Cerebras | 30 | 1M tokens/day |
| **Combined** | **~140** | **31+ models** |

## Configuration Reference

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `NVIDIA_API_KEY` | Yes | Free at [build.nvidia.com](https://build.nvidia.com/settings/api-keys) |
| `OPENCODE_API_KEY` | No | OpenCode Zen free models |
| `GROQ_API_KEY` | No | Groq free tier |
| `CEREBRAS_API_KEY` | No | Cerebras free tier |
| `SLACK_WEBHOOK_URL` | No | Slack alerting for proxy errors |

## Project Structure

```
nvidia-litellm-router/
├── setup.py              # Config generator (run this first)
├── config.yaml           # Generated LiteLLM config (gitignored)
├── models.json           # Generated model registry (gitignored)
├── test_proxy.py         # Smoke tests for running proxy
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── examples/
│   ├── python_usage.py   # Python openai SDK example
│   └── rust_usage.rs     # Rust async-openai example
└── docs/
    ├── architecture.md   # System design and data flow
    ├── tech-specs.md     # Config schema, routing details
    ├── plan.md           # Implementation plan
    └── phases.md         # Phased rollout
```

## License

MIT
