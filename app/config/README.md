# Model Configuration Guide

This guide explains how to configure the models used by Auto-Dev Assistant.

## Configuration File

The models are configured in the `model_config.json` file located in the `app/config` directory.

## Simplified Provider-Based Configuration

The configuration system is now simplified to make it easier to switch between providers. The recommended way to configure the models is to only set the `provider` field:

```json
{
  "provider": "huggingface"  // or "openai"
}
```

This will automatically set both the embedding model and LLM model to use the specified provider, and will select the default models for that provider from the `default_configs` section.

## Default Models

The default models for each provider are defined in the `default_configs` section:

```json
"default_configs": {
  "huggingface": {
    "embedding_model": "BAAI/bge-large-en-v1.5",
    "llm_model": "mistralai/Mistral-7B-Instruct-v0.3"
  },
  "openai": {
    "embedding_model": "text-embedding-3-large",
    "llm_model": "gpt-4o-mini"
  }
}
```

## Overriding Default Models

If you want to use a different model than the default, you can add an explicit `embedding_model` or `llm_model` field:

```json
{
  "provider": "huggingface",
  "llm_model": "meta-llama/Llama-3.3-70B-Instruct"  // Override default LLM model
}
```

## Available Models

Here are the available models for each provider:

### HuggingFace

- Embedding models:
  - `BAAI/bge-large-en-v1.5` (default)
  - `Alibaba-NLP/gte-large-en-v1.5`
  
- LLM models:
  - `mistralai/Mistral-7B-Instruct-v0.3` (default)
  - `meta-llama/Llama-3.3-70B-Instruct`
  - `tiiuae/falcon-40b-instruct`

### OpenAI

- Embedding models:
  - `text-embedding-3-large` (default)
  
- LLM models:
  - `gpt-4o-mini` (default)

## Examples

### Example 1: Using OpenAI

To use OpenAI models:

```json
{
  "provider": "openai"
}
```

This will automatically use:
- `text-embedding-3-large` for embeddings
- `gpt-4o-mini` for LLM

### Example 2: Using HuggingFace with a Different LLM

To use HuggingFace with a different LLM model:

```json
{
  "provider": "huggingface",
  "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
}
```

### Example 3: Mixed Configuration (Advanced)

If needed, you can also set up a mixed configuration by specifying both provider and individual models:

```json
{
  "provider": "huggingface",
  "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
  "embedding_model": "Alibaba-NLP/gte-large-en-v1.5"
}
```

## API Keys

Remember that you still need to set the appropriate API keys in your environment variables:

- For OpenAI: `OPENAI_API_KEY`
- For HuggingFace: `HUGGINGFACE_API_TOKEN` 