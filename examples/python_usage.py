#!/usr/bin/env python3
"""Example: Using the LiteLLM proxy from Python with openai SDK."""

import openai

client = openai.OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-litellm-master",
)

# "nvidia-auto" → LiteLLM picks the fastest available model
resp = client.chat.completions.create(
    model="nvidia-auto",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.choices[0].message.content)
print(f"Routed to: {resp.model}")
