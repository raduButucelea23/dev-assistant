import os
import sys
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.utils.model_config import (
    get_config_from_file,
    save_config_to_file,
    get_model_config,
    validate_config,
    get_available_models,
    get_available_providers,
    EMBEDDING_PROVIDERS,
    LLM_PROVIDERS,
    DEFAULT_CONFIG
)

class TestModelConfig:
    """Tests for the model_config.py utility."""
    
    def test_constants(self):
        """Test that constants are properly defined."""
        # Check embedding providers
        assert "openai" in EMBEDDING_PROVIDERS
        assert "huggingface" in EMBEDDING_PROVIDERS
        assert isinstance(EMBEDDING_PROVIDERS["openai"]["models"], list)
        assert isinstance(EMBEDDING_PROVIDERS["huggingface"]["models"], list)
        
        # Check LLM providers
        assert "openai" in LLM_PROVIDERS
        assert "huggingface" in LLM_PROVIDERS
        assert isinstance(LLM_PROVIDERS["openai"]["models"], list)
        assert isinstance(LLM_PROVIDERS["huggingface"]["models"], list)
        
        # Check defaults
        assert "provider" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["provider"] in EMBEDDING_PROVIDERS
        assert DEFAULT_CONFIG["embedding_provider"] in EMBEDDING_PROVIDERS
        assert DEFAULT_CONFIG["embedding_model"] in EMBEDDING_PROVIDERS[DEFAULT_CONFIG["embedding_provider"]]["models"]
        assert DEFAULT_CONFIG["llm_provider"] in LLM_PROVIDERS
        assert DEFAULT_CONFIG["llm_model"] in LLM_PROVIDERS[DEFAULT_CONFIG["llm_provider"]]["models"]
    
    def test_get_config_from_file(self):
        """Test getting configuration from file."""
        # Create test config
        test_config = {
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        # Mock open to return our test config
        with patch("builtins.open", mock_open(read_data=json.dumps(test_config))):
            # Mock os.path.exists to return True
            with patch("os.path.exists", return_value=True):
                config = get_config_from_file()
                
                # Verify values
                assert config["embedding_provider"] == "huggingface"
                assert config["embedding_model"] == "BAAI/bge-large-en-v1.5"
                assert config["llm_provider"] == "huggingface"
                assert config["llm_model"] == "meta-llama/Llama-3.3-70B-Instruct"
    
    def test_get_config_from_file_not_exists(self):
        """Test getting configuration from a non-existent file."""
        # Mock os.path.exists to return False
        with patch("os.path.exists", return_value=False):
            config = get_config_from_file()
            # Should return the default config now
            assert config["provider"] == DEFAULT_CONFIG["provider"]
            assert config["embedding_provider"] == DEFAULT_CONFIG["embedding_provider"]
            assert config["embedding_model"] == DEFAULT_CONFIG["embedding_model"]
            assert config["llm_provider"] == DEFAULT_CONFIG["llm_provider"]
            assert config["llm_model"] == DEFAULT_CONFIG["llm_model"]
    
    def test_save_config_to_file(self):
        """Test saving configuration to file."""
        # Create test config
        test_config = {
            "provider": "huggingface",
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        # Mock open for write
        with patch("builtins.open", mock_open()) as mock_file:
            # Mock os.path.exists to return True
            with patch("os.path.exists", return_value=True):
                # Mock os.makedirs to do nothing
                with patch("os.makedirs"):
                    success = save_config_to_file(test_config)
                    
                    # Verify function returned success
                    assert success
                    
                    # Verify file was opened for writing
                    mock_file.assert_called_once()
                    
                    # Verify json.dump was called with our config
                    file_handle = mock_file()
                    file_handle.write.assert_called()
    
    def test_validate_config_valid(self):
        """Test validating a valid configuration."""
        # Create valid test config
        test_config = {
            "provider": "huggingface",
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        validated = validate_config(test_config)
        
        # Should keep the valid values
        assert validated["provider"] == "huggingface"
        assert validated["embedding_provider"] == "huggingface"
        assert validated["embedding_model"] == "BAAI/bge-large-en-v1.5"
        assert validated["llm_provider"] == "huggingface"
        assert validated["llm_model"] == "meta-llama/Llama-3.3-70B-Instruct"
    
    def test_validate_config_invalid(self):
        """Test validating an invalid configuration."""
        # Create invalid test config
        test_config = {
            "provider": "invalid",
            "embedding_provider": "invalid",
            "embedding_model": "invalid",
            "llm_provider": "invalid",
            "llm_model": "invalid"
        }
        
        validated = validate_config(test_config)
        
        # Should default to default values
        assert validated["provider"] == DEFAULT_CONFIG["provider"]
        assert validated["embedding_provider"] == DEFAULT_CONFIG["embedding_provider"]
        assert validated["embedding_model"] in EMBEDDING_PROVIDERS[DEFAULT_CONFIG["embedding_provider"]]["models"]
        assert validated["llm_provider"] == DEFAULT_CONFIG["llm_provider"]
        assert validated["llm_model"] in LLM_PROVIDERS[DEFAULT_CONFIG["llm_provider"]]["models"]
    
    def test_get_model_config(self):
        """Test getting model configuration."""
        # Create test config
        test_config = {
            "provider": "huggingface",
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        # Mock get_config_from_file to return our test config
        with patch("app.utils.model_config.get_config_from_file", return_value=test_config):
            config = get_model_config()
            
            # Verify values from file config
            assert config["provider"] == "huggingface"
            assert config["embedding_provider"] == "huggingface"
            assert config["embedding_model"] == "BAAI/bge-large-en-v1.5"
            assert config["llm_provider"] == "huggingface"
            assert config["llm_model"] == "meta-llama/Llama-3.3-70B-Instruct"
    
    def test_get_available_models(self):
        """Test getting available models."""
        models = get_available_models()
        
        # Check structure
        assert "embedding" in models
        assert "llm" in models
        assert models["embedding"] == EMBEDDING_PROVIDERS
        assert models["llm"] == LLM_PROVIDERS
    
    def test_get_available_providers(self):
        """Test getting available providers."""
        providers = get_available_providers()
        
        # Check that available providers include expected values
        assert "huggingface" in providers
        assert "openai" in providers
        
    def test_provider_based_config(self):
        """Test using the provider-based configuration."""
        # Create provider-based config with defaults
        test_config = {
            "provider": "openai",
            "default_configs": {
                "openai": {
                    "embedding_model": "text-embedding-3-large",
                    "llm_model": "gpt-4o-mini"
                },
                "huggingface": {
                    "embedding_model": "BAAI/bge-large-en-v1.5",
                    "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
                }
            }
        }
        
        # Mock get_config_from_file to return our test config
        with patch("app.utils.model_config.get_config_from_file", return_value=test_config):
            config = get_model_config()
            
            # Verify values derived from provider
            assert config["provider"] == "openai"
            assert config["embedding_provider"] == "openai"
            assert config["embedding_model"] == "text-embedding-3-large"
            assert config["llm_provider"] == "openai"
            assert config["llm_model"] == "gpt-4o-mini"
    
    def test_provider_based_config_with_override(self):
        """Test using provider-based configuration with model override."""
        # Create provider-based config with model override
        test_config = {
            "provider": "huggingface",
            "embedding_model": "Alibaba-NLP/gte-large-en-v1.5",  # Override default
            "default_configs": {
                "huggingface": {
                    "embedding_model": "BAAI/bge-large-en-v1.5",
                    "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
                },
                "openai": {
                    "embedding_model": "text-embedding-3-large",
                    "llm_model": "gpt-4o-mini"
                }
            }
        }
        
        # Mock get_config_from_file to return our test config
        with patch("app.utils.model_config.get_config_from_file", return_value=test_config):
            config = get_model_config()
            
            # Verify provider values and overridden model
            assert config["provider"] == "huggingface"
            assert config["embedding_provider"] == "huggingface"
            assert config["embedding_model"] == "Alibaba-NLP/gte-large-en-v1.5"  # Overridden
            assert config["llm_provider"] == "huggingface"
            assert config["llm_model"] == "meta-llama/Llama-3.3-70B-Instruct"  # Default from provider 