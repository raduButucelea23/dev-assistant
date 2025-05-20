# Model Configuration Guide

## Summary

Auto-Dev Assistant uses AI models for various tasks and can be configured to work with either HuggingFace or OpenAI models. This guide explains how to configure and use these models with your application.

## Setup & Running Instructions

1. **Locate the configuration file**: The models are configured in the `model_config.json` file located in the `app/config` directory.

2. **Set up your provider**: Choose either HuggingFace or OpenAI as your provider by editing the configuration file:
   ```json
   {
     "provider": "huggingface"  // or "openai"
   }
   ```

3. **Set environment variables**: Add the appropriate API keys to your environment:
   - For OpenAI: `OPENAI_API_KEY`
   - For HuggingFace: `HUGGINGFACE_API_TOKEN`

4. That's it! The system will automatically use the default models for your chosen provider.

## Configuration Options

### Basic Configuration

The simplest way to configure the system is to only specify the provider:

```json
{
  "provider": "huggingface"  // or "openai"
}
```

This will automatically set both the embedding model and LLM model to use the default models for that provider.

### Default Models

The default models for each provider are defined in the system's `default_configs` section:

```json
"default_configs": {
  "huggingface": {
    "embedding_model": "BAAI/bge-large-en-v1.5",
    "llm_model": "mistralai/Mistral-7B-Instruct-v0.3",
    "generation_params": {
      "temperature": 0.3,
      "max_tokens": 4000,
      "top_p": 0.85
    }
  },
  "openai": {
    "embedding_model": "text-embedding-3-large",
    "llm_model": "gpt-4o-mini",
    "generation_params": {
      "temperature": 0.3,
      "max_tokens": 4000,
      "top_p": 0.85,
      "frequency_penalty": 0.5,
      "presence_penalty": 0.1
    }
  }
}
```

### Model Generation Parameters

The configuration now includes generation parameters for each provider. These parameters control how the model generates responses:

- **temperature**: Controls randomness (0-1). Lower values make responses more deterministic and focused.
- **max_tokens**: Maximum length of the generated response.
- **top_p**: Nucleus sampling parameter that controls diversity.
- **frequency_penalty**: (OpenAI only) Reduces repetition of token sequences.
- **presence_penalty**: (OpenAI only) Reduces repetition of topics.

You can adjust these parameters in the `generation_params` section for each provider to fine-tune the model's responses.

### Advanced Configuration

If you want to override the default models, you can explicitly specify the model you want to use:

```json
{
  "provider": "huggingface",
  "llm_model": "meta-llama/Llama-3.3-70B-Instruct"  // Override default LLM model
}
```

You can also create a mixed configuration by specifying both the provider and individual models:

```json
{
  "provider": "huggingface",
  "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
  "embedding_model": "Alibaba-NLP/gte-large-en-v1.5"
}
```

## Available Models

### HuggingFace

- **Embedding models**:
  - `BAAI/bge-large-en-v1.5` (default)
  - `Alibaba-NLP/gte-large-en-v1.5`
  
- **LLM models**:
  - `mistralai/Mistral-7B-Instruct-v0.3` (default)
  - `meta-llama/Llama-3.3-70B-Instruct`
  - `tiiuae/falcon-40b-instruct`

### OpenAI

- **Embedding models**:
  - `text-embedding-3-large` (default)
  
- **LLM models**:
  - `gpt-4o-mini` (default)

## Configuration Examples

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

To use HuggingFace with a specific LLM model:

```json
{
  "provider": "huggingface",
  "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
}
```

### Example 3: Mixed Configuration (Advanced)

If needed, you can set up a mixed configuration:

```json
{
  "provider": "huggingface",
  "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
  "embedding_model": "Alibaba-NLP/gte-large-en-v1.5"
}
```

### Example 4: Adjusting Generation Parameters

To customize how the model generates responses:

```json
{
  "provider": "openai",
  "default_configs": {
    "openai": {
      "generation_params": {
        "temperature": 0.7,  // Increased creativity
        "max_tokens": 2000,  // Shorter responses
        "top_p": 0.9         // More diverse output
      }
    }
  }
}
``` 