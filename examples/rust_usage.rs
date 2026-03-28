// Example: Using the LiteLLM proxy from Rust with async-openai
//
// Add to Cargo.toml:
//   async-openai = "0.25"
//   tokio = { version = "1", features = ["full"] }
//
// This connects to the LiteLLM proxy at localhost:4000 which
// auto-routes across all NVIDIA NIM free models.

use async_openai::{
    config::OpenAIConfig,
    types::{
        ChatCompletionRequestUserMessageArgs, CreateChatCompletionRequestArgs,
    },
    Client,
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Point to LiteLLM proxy
    let config = OpenAIConfig::new()
        .with_api_key("sk-litellm-master")
        .with_api_base("http://localhost:4000/v1");

    let client = Client::with_config(config);

    // "nvidia-auto" → LiteLLM picks the fastest available model
    let request = CreateChatCompletionRequestArgs::default()
        .model("nvidia-auto")
        .messages(vec![
            ChatCompletionRequestUserMessageArgs::default()
                .content("Extract all named entities from: 'Rohan built ctxgraph in Rust at his apartment in Pune, India'")
                .build()?
                .into(),
        ])
        .max_tokens(500_u32)
        .build()?;

    let response = client.chat().create(request).await?;

    for choice in &response.choices {
        println!("Model used: {}", response.model);
        println!("Response: {}", choice.message.content.as_ref().unwrap());
    }

    // You can also target specific tiers:
    // "nvidia-coding"    → fastest coding model
    // "nvidia-reasoning" → fastest reasoning model (DeepSeek R1, Nemotron Ultra)
    // "nvidia-fast"      → fastest small model (Phi-4, Nemotron Nano, Llama 8B)
    // "kimi-k2-instruct" → specific model directly

    Ok(())
}
