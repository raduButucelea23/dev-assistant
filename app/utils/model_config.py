"""Model configuration utility for Auto-Dev Assistant.

This module provides functions to configure embedding and LLM models
for the Auto-Dev Assistant application.
"""

import os
import json
import logging
from typing import Dict, Optional, List, Any
from dotenv import load_dotenv

# Load environment variables (needed for API keys, not for model selection)
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the generation parameters configuration
from app.utils.generation_config import (
    get_config_manager, 
    get_model_config as get_model_config_v2,
    get_available_models as get_available_models_v2,
    get_available_providers as get_available_providers_v2,
    save_config_to_file as save_config_to_file_v2,
    EMBEDDING_PROVIDERS,
    LLM_PROVIDERS
)

# Path to configuration file
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "model_config.json")

# Default fallback configuration (only used if file can't be loaded)
DEFAULT_CONFIG = {
    "provider": "huggingface",
    "embedding_provider": "huggingface",
    "embedding_model": "BAAI/bge-large-en-v1.5",
    "llm_provider": "huggingface",
    "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
}


def get_config_from_file() -> Dict[str, str]:
    """Get model configuration from configuration file.
    
    Returns:
        Dictionary with model configuration. If file doesn't exist or can't be read,
        returns the default configuration.
    """
    if not os.path.exists(CONFIG_FILE_PATH):
        logger.warning(f"Configuration file not found at {CONFIG_FILE_PATH}. Using default configuration.")
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            config = json.load(f)
            
        # Log the loaded configuration
        logger.info(f"Loaded configuration from {CONFIG_FILE_PATH}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration file: {str(e)}. Using default configuration.")
        return DEFAULT_CONFIG.copy()


def save_config_to_file(config: Dict[str, str]) -> bool:
    """Save model configuration to configuration file.
    
    Args:
        config: Dictionary with model configuration
        
    Returns:
        True if configuration was saved successfully, False otherwise
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    
    try:
        # Read existing config to preserve structure
        existing_config = {}
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r") as f:
                    existing_config = json.load(f)
            except Exception as e:
                logger.warning(f"Could not read existing config file: {str(e)}. Creating new file.")
        
        # Update only the necessary fields while preserving the rest
        # Core configuration values
        for field in ["provider", "embedding_provider", "embedding_model", "llm_provider", "llm_model"]:
            if field in config:
                existing_config[field] = config[field]
        
        # Write updated config
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(existing_config, f, indent=2)
        
        logger.info(f"Successfully saved configuration to {CONFIG_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration file: {str(e)}")
        return False


def get_model_config() -> Dict[str, str]:
    """Get model configuration from configuration file.
    
    Returns:
        Dictionary with model configuration
    """
    # Get configuration from file
    config = get_config_from_file()
    
    # Handle provider-based configuration
    if "provider" in config:
        provider = config["provider"]
        
        # Only set embedding_provider and llm_provider if they are not explicitly defined
        if "embedding_provider" not in config:
            config["embedding_provider"] = provider
            
        if "llm_provider" not in config:
            config["llm_provider"] = provider
        
        # If default_configs exists, use it to set default models based on provider
        if "default_configs" in config:
            # For embedding model
            embedding_provider = config["embedding_provider"]
            if embedding_provider in config["default_configs"]:
                defaults = config["default_configs"][embedding_provider]
                if "embedding_model" not in config or not config["embedding_model"]:
                    config["embedding_model"] = defaults.get("embedding_model")
            
            # For LLM model
            llm_provider = config["llm_provider"]
            if llm_provider in config["default_configs"]:
                defaults = config["default_configs"][llm_provider]
                if "llm_model" not in config or not config["llm_model"]:
                    config["llm_model"] = defaults.get("llm_model")
    
    # Validate configuration
    config = validate_config(config)
    
    # Log the active configuration
    logger.info(f"Active model configuration: embedding={config['embedding_provider']}:{config['embedding_model']}, llm={config['llm_provider']}:{config['llm_model']}")
    
    return config


def validate_config(config: Dict[str, str]) -> Dict[str, str]:
    """Validate model configuration and set default values if needed.
    
    Args:
        config: Dictionary with model configuration
        
    Returns:
        Validated configuration dictionary
    """
    # Add provider field if missing (for backward compatibility)
    if "provider" not in config:
        # If embedding_provider and llm_provider are the same, use that as provider
        if "embedding_provider" in config and "llm_provider" in config:
            if config["embedding_provider"] == config["llm_provider"]:
                config["provider"] = config["embedding_provider"]
            else:
                # When different, prefer embedding_provider for backwards compatibility
                config["provider"] = config["embedding_provider"]
                logger.warning(f"embedding_provider '{config['embedding_provider']}' and llm_provider '{config['llm_provider']}' differ. Using '{config['provider']}' as default provider.")
        else:
            # Default to DEFAULT_CONFIG
            config["provider"] = DEFAULT_CONFIG["provider"]
    
    # Check provider
    valid_providers = list(EMBEDDING_PROVIDERS.keys())
    if config["provider"] not in valid_providers:
        logger.warning(f"Invalid provider '{config['provider']}'. Using default: {DEFAULT_CONFIG['provider']}")
        config["provider"] = DEFAULT_CONFIG["provider"]
    
    # Check embedding provider
    if "embedding_provider" not in config:
        config["embedding_provider"] = config["provider"]
    elif config["embedding_provider"] not in EMBEDDING_PROVIDERS:
        logger.warning(f"Invalid embedding provider '{config['embedding_provider']}'. Using provider: {config['provider']}")
        config["embedding_provider"] = config["provider"]
    
    # Check embedding model
    valid_embedding_models = EMBEDDING_PROVIDERS[config["embedding_provider"]]["models"]
    if "embedding_model" not in config or config["embedding_model"] not in valid_embedding_models:
        default_model = valid_embedding_models[0]
        logger.warning(f"Invalid embedding model for provider '{config['embedding_provider']}'. Using default: {default_model}")
        config["embedding_model"] = default_model
    
    # Check LLM provider
    if "llm_provider" not in config:
        config["llm_provider"] = config["provider"]
    elif config["llm_provider"] not in LLM_PROVIDERS:
        logger.warning(f"Invalid LLM provider '{config['llm_provider']}'. Using provider: {config['provider']}")
        config["llm_provider"] = config["provider"]
    
    # Check LLM model
    valid_llm_models = LLM_PROVIDERS[config["llm_provider"]]["models"]
    if "llm_model" not in config or config["llm_model"] not in valid_llm_models:
        default_model = valid_llm_models[0]
        logger.warning(f"Invalid LLM model for provider '{config['llm_provider']}'. Using default: {default_model}")
        config["llm_model"] = default_model
    
    return config


def get_available_models() -> Dict[str, Dict[str, List[str]]]:
    """Get a dictionary of available models.
    
    Returns:
        Dictionary with available models
    """
    return {
        "embedding": EMBEDDING_PROVIDERS,
        "llm": LLM_PROVIDERS
    }


def get_available_providers() -> List[str]:
    """Get a list of available providers.
    
    Returns:
        List of provider names
    """
    # Providers are the same for both embedding and LLM
    return list(EMBEDDING_PROVIDERS.keys())


if __name__ == "__main__":
    """If run as a script, print current configuration"""
    config = get_model_config()
    print("Current model configuration:")
    print(f"Provider: {config['provider']}")
    print(f"Embedding Provider: {config['embedding_provider']}")
    print(f"Embedding Model: {config['embedding_model']}")
    print(f"LLM Provider: {config['llm_provider']}")
    print(f"LLM Model: {config['llm_model']}")
    
    print("\nAvailable models:")
    available_models = get_available_models()
    
    print("\nEmbedding Providers:")
    for provider, info in available_models["embedding"].items():
        print(f"  {provider} ({info['display_name']}):")
        for model in info["models"]:
            print(f"    - {model}")
    
    print("\nLLM Providers:")
    for provider, info in available_models["llm"].items():
        print(f"  {provider} ({info['display_name']}):")
        for model in info["models"]:
            print(f"    - {model}") 