"""
Model generation parameters configuration manager for Auto-Dev Assistant.

This module provides a centralized configuration system with type-safe accessors
for model generation parameters such as temperature, max_tokens, etc.

It complements the basic model_config.py module which handles model selection,
by focusing specifically on generation parameters configuration.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, TypedDict, Union, cast
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type definitions for better type safety
class GenerationParams(TypedDict, total=False):
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    

class ModelConfig(TypedDict, total=False):
    embedding_model: str
    llm_model: str
    generation_params: GenerationParams


class ProviderConfigs(TypedDict):
    huggingface: ModelConfig
    openai: ModelConfig


class ConfigDict(TypedDict, total=False):
    provider: str
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    llm_model: str
    default_configs: ProviderConfigs


# Constants for model selection
EMBEDDING_PROVIDERS = {
    "openai": {
        "display_name": "OpenAI",
        "models": ["text-embedding-3-large"]
    },
    "huggingface": {
        "display_name": "HuggingFace (Local)",
        "models": ["BAAI/bge-large-en-v1.5", "Alibaba-NLP/gte-large-en-v1.5"]
    }
}

LLM_PROVIDERS = {
    "openai": {
        "display_name": "OpenAI",
        "models": ["gpt-4o-mini"]
    },
    "huggingface": {
        "display_name": "HuggingFace (API)",
        "models": ["meta-llama/Llama-3.3-70B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3", "tiiuae/falcon-40b-instruct"]
    }
}

# Default generation parameters for each provider
DEFAULT_GENERATION_PARAMS = {
    "huggingface": {
        "temperature": 0.3,
        "max_tokens": 4000,
        "top_p": 0.85
    },
    "openai": {
        "temperature": 0.3,
        "max_tokens": 4000,
        "top_p": 0.85,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.1
    }
}

# Path to configuration file
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                              "app", "config", "model_config.json")

# Default fallback configuration
DEFAULT_CONFIG: ConfigDict = {
    "provider": "huggingface",
    "embedding_provider": "huggingface",
    "embedding_model": "BAAI/bge-large-en-v1.5",
    "llm_provider": "huggingface",
    "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
    "default_configs": {
        "huggingface": {
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
            "generation_params": DEFAULT_GENERATION_PARAMS["huggingface"]
        },
        "openai": {
            "embedding_model": "text-embedding-3-large",
            "llm_model": "gpt-4o-mini",
            "generation_params": DEFAULT_GENERATION_PARAMS["openai"]
        }
    }
}


@dataclass
class ModelGenerationParams:
    """Class to represent model generation parameters with type safety."""
    temperature: float = 0.3
    max_tokens: int = 4000
    top_p: float = 0.85
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelGenerationParams':
        """Create ModelGenerationParams from a dictionary."""
        params = cls()
        
        if data is None:
            return params
            
        # Set attributes from dictionary, ignoring unknown keys
        for key, value in data.items():
            if hasattr(params, key) and value is not None:
                setattr(params, key, value)
        
        return params
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


class ModelConfigManager:
    """Singleton class to manage model configuration."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ModelConfigManager, cls).__new__(cls)
            cls._instance._config = None
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if not os.path.exists(CONFIG_FILE_PATH):
            logger.warning(f"Configuration file not found at {CONFIG_FILE_PATH}. Using default configuration.")
            self._config = DEFAULT_CONFIG.copy()
            return
        
        try:
            with open(CONFIG_FILE_PATH, "r") as f:
                config = json.load(f)
            
            # Add default configurations if not present
            if "default_configs" not in config:
                config["default_configs"] = DEFAULT_CONFIG["default_configs"]
            
            # Complete default_configs if partial
            if "huggingface" not in config["default_configs"]:
                config["default_configs"]["huggingface"] = DEFAULT_CONFIG["default_configs"]["huggingface"]
            if "openai" not in config["default_configs"]:
                config["default_configs"]["openai"] = DEFAULT_CONFIG["default_configs"]["openai"]
                
            # Ensure generation_params exist for both providers
            for provider in ["huggingface", "openai"]:
                if provider in config["default_configs"]:
                    provider_config = config["default_configs"][provider]
                    if "generation_params" not in provider_config:
                        provider_config["generation_params"] = DEFAULT_GENERATION_PARAMS[provider]
            
            # Validate configuration
            self._config = self._validate_config(config)
            logger.info(f"Loaded configuration from {CONFIG_FILE_PATH}")
        except Exception as e:
            logger.error(f"Error loading configuration file: {str(e)}. Using default configuration.")
            self._config = DEFAULT_CONFIG.copy()
    
    def _validate_config(self, config: Dict[str, Any]) -> ConfigDict:
        """Validate and normalize configuration.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Validated configuration dictionary
        """
        result = cast(ConfigDict, {})
        
        # Handle provider
        if "provider" not in config:
            result["provider"] = DEFAULT_CONFIG["provider"]
        else:
            provider = config["provider"]
            if provider not in EMBEDDING_PROVIDERS:
                logger.warning(f"Invalid provider '{provider}'. Using default: {DEFAULT_CONFIG['provider']}")
                result["provider"] = DEFAULT_CONFIG["provider"]
            else:
                result["provider"] = provider
        
        # Handle embedding provider
        if "embedding_provider" not in config:
            result["embedding_provider"] = result["provider"]
        else:
            embedding_provider = config["embedding_provider"]
            if embedding_provider not in EMBEDDING_PROVIDERS:
                logger.warning(f"Invalid embedding provider '{embedding_provider}'. Using provider: {result['provider']}")
                result["embedding_provider"] = result["provider"]
            else:
                result["embedding_provider"] = embedding_provider
        
        # Handle embedding model
        if "embedding_model" not in config:
            # Get from default_configs if available
            if ("default_configs" in config and 
                result["embedding_provider"] in config["default_configs"] and
                "embedding_model" in config["default_configs"][result["embedding_provider"]]):
                result["embedding_model"] = config["default_configs"][result["embedding_provider"]]["embedding_model"]
            else:
                # Fallback to first available model
                result["embedding_model"] = EMBEDDING_PROVIDERS[result["embedding_provider"]]["models"][0]
        else:
            embedding_model = config["embedding_model"]
            valid_models = EMBEDDING_PROVIDERS[result["embedding_provider"]]["models"]
            if embedding_model not in valid_models:
                logger.warning(f"Invalid embedding model '{embedding_model}' for provider '{result['embedding_provider']}'. Using default.")
                result["embedding_model"] = valid_models[0]
            else:
                result["embedding_model"] = embedding_model
        
        # Handle LLM provider
        if "llm_provider" not in config:
            result["llm_provider"] = result["provider"]
        else:
            llm_provider = config["llm_provider"]
            if llm_provider not in LLM_PROVIDERS:
                logger.warning(f"Invalid LLM provider '{llm_provider}'. Using provider: {result['provider']}")
                result["llm_provider"] = result["provider"]
            else:
                result["llm_provider"] = llm_provider
        
        # Handle LLM model
        if "llm_model" not in config:
            # Get from default_configs if available
            if ("default_configs" in config and 
                result["llm_provider"] in config["default_configs"] and
                "llm_model" in config["default_configs"][result["llm_provider"]]):
                result["llm_model"] = config["default_configs"][result["llm_provider"]]["llm_model"]
            else:
                # Fallback to first available model
                result["llm_model"] = LLM_PROVIDERS[result["llm_provider"]]["models"][0]
        else:
            llm_model = config["llm_model"]
            valid_models = LLM_PROVIDERS[result["llm_provider"]]["models"]
            if llm_model not in valid_models:
                logger.warning(f"Invalid LLM model '{llm_model}' for provider '{result['llm_provider']}'. Using default.")
                result["llm_model"] = valid_models[0]
            else:
                result["llm_model"] = llm_model
        
        # Copy default_configs
        result["default_configs"] = config.get("default_configs", DEFAULT_CONFIG["default_configs"])
        
        return result
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if saved successfully, False otherwise
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
            for field in ["provider", "embedding_provider", "embedding_model", "llm_provider", "llm_model", "default_configs"]:
                if field in config:
                    existing_config[field] = config[field]
            
            # Write updated config
            with open(CONFIG_FILE_PATH, "w") as f:
                json.dump(existing_config, f, indent=2)
            
            # Reload configuration
            self._load_config()
            
            logger.info(f"Successfully saved configuration to {CONFIG_FILE_PATH}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration file: {str(e)}")
            return False
    
    def get_raw_config(self) -> ConfigDict:
        """Get the raw configuration dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self._config.copy()
    
    def get_provider(self) -> str:
        """Get the main provider.
        
        Returns:
            Provider name
        """
        return self._config["provider"]
    
    def get_embedding_provider(self) -> str:
        """Get the embedding provider.
        
        Returns:
            Embedding provider name
        """
        return self._config["embedding_provider"]
    
    def get_embedding_model(self) -> str:
        """Get the embedding model.
        
        Returns:
            Embedding model name
        """
        return self._config["embedding_model"]
    
    def get_llm_provider(self) -> str:
        """Get the LLM provider.
        
        Returns:
            LLM provider name
        """
        return self._config["llm_provider"]
    
    def get_llm_model(self) -> str:
        """Get the LLM model.
        
        Returns:
            LLM model name
        """
        return self._config["llm_model"]
    
    def get_generation_params(self, provider: Optional[str] = None) -> ModelGenerationParams:
        """Get generation parameters for a provider.
        
        Args:
            provider: Provider name. If None, uses the current LLM provider.
            
        Returns:
            ModelGenerationParams object with generation parameters
        """
        if provider is None:
            provider = self.get_llm_provider()
        
        # Get default_configs
        default_configs = self._config.get("default_configs", {})
        
        # If provider not in default_configs, use fallback
        if provider not in default_configs:
            logger.warning(f"Provider '{provider}' not found in default_configs. Using defaults.")
            params_dict = DEFAULT_GENERATION_PARAMS.get(provider, DEFAULT_GENERATION_PARAMS["huggingface"])
            return ModelGenerationParams.from_dict(params_dict)
        
        # Get provider config
        provider_config = default_configs[provider]
        
        # Get generation_params
        generation_params = provider_config.get("generation_params")
        if not generation_params:
            logger.warning(f"No generation_params found for provider '{provider}'. Using defaults.")
            generation_params = DEFAULT_GENERATION_PARAMS.get(provider, DEFAULT_GENERATION_PARAMS["huggingface"])
        
        return ModelGenerationParams.from_dict(generation_params)
    
    def set_generation_params(self, params: ModelGenerationParams, provider: Optional[str] = None) -> bool:
        """Set generation parameters for a provider.
        
        Args:
            params: ModelGenerationParams object with new parameters
            provider: Provider name. If None, uses the current LLM provider.
            
        Returns:
            True if saved successfully, False otherwise
        """
        if provider is None:
            provider = self.get_llm_provider()
        
        try:
            # Copy current config
            config = self.get_raw_config()
            
            # Ensure default_configs exists
            if "default_configs" not in config:
                config["default_configs"] = DEFAULT_CONFIG["default_configs"]
            
            # Ensure provider exists in default_configs
            if provider not in config["default_configs"]:
                config["default_configs"][provider] = {}
            
            # Update generation_params
            config["default_configs"][provider]["generation_params"] = params.to_dict()
            
            # Save config
            return self.save_config(config)
        except Exception as e:
            logger.error(f"Error setting generation parameters: {str(e)}")
            return False


# Singleton instance
_config_manager = None

def get_config_manager() -> ModelConfigManager:
    """Get the singleton instance of ModelConfigManager.
    
    Returns:
        ModelConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ModelConfigManager()
    return _config_manager


# Compatibility functions for legacy code
def get_model_config() -> Dict[str, str]:
    """Get model configuration (compatibility function).
    
    Returns:
        Dictionary with model configuration
    """
    config = get_config_manager().get_raw_config()
    return {
        "provider": config["provider"],
        "embedding_provider": config["embedding_provider"],
        "embedding_model": config["embedding_model"],
        "llm_provider": config["llm_provider"],
        "llm_model": config["llm_model"]
    }


def get_generation_params(provider: Optional[str] = None) -> Dict[str, Any]:
    """Get generation parameters (compatibility function).
    
    Args:
        provider: Provider name. If None, uses the current LLM provider.
        
    Returns:
        Dictionary with generation parameters
    """
    params = get_config_manager().get_generation_params(provider)
    return params.to_dict()


def get_available_models() -> Dict[str, Dict[str, List[str]]]:
    """Get available models (compatibility function).
    
    Returns:
        Dictionary with available models
    """
    return {
        "embedding": EMBEDDING_PROVIDERS,
        "llm": LLM_PROVIDERS
    }


def get_available_providers() -> List[str]:
    """Get available providers (compatibility function).
    
    Returns:
        List of provider names
    """
    return list(EMBEDDING_PROVIDERS.keys())


def save_config_to_file(config: Dict[str, Any]) -> bool:
    """Save configuration to file (compatibility function).
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if saved successfully, False otherwise
    """
    return get_config_manager().save_config(config)


if __name__ == "__main__":
    """If run as a script, print current configuration"""
    config_manager = get_config_manager()
    config = config_manager.get_raw_config()
    
    print("Current model configuration:")
    print(f"Provider: {config_manager.get_provider()}")
    print(f"Embedding: {config_manager.get_embedding_provider()} / {config_manager.get_embedding_model()}")
    print(f"LLM: {config_manager.get_llm_provider()} / {config_manager.get_llm_model()}")
    
    print("\nGeneration parameters:")
    params = config_manager.get_generation_params()
    for key, value in params.to_dict().items():
        print(f"  {key}: {value}") 