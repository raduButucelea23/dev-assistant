import os
import sys
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.utils.model_config import get_model_config

class TestDBBasics:
    """Simple tests for database configuration functionality."""
    
    def test_model_config(self):
        """Test that model_config correctly reads from config file."""
        # Create test config
        test_config = {
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        # Mock file config loading
        with patch("app.utils.model_config.get_config_from_file", return_value=test_config):
            # Get config
            config = get_model_config()
            
            # Verify values
            assert config["embedding_provider"] == "huggingface"
            assert config["embedding_model"] == "BAAI/bge-large-en-v1.5"
            assert config["llm_provider"] == "huggingface"
            assert config["llm_model"] == "meta-llama/Llama-3.3-70B-Instruct"
    
    def test_different_model_configs(self):
        """Test different model configurations."""
        # Create HuggingFace config
        hf_config = {
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        # Create OpenAI config
        openai_config = {
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-large",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini"
        }
        
        # Test with HuggingFace config
        with patch("app.utils.model_config.get_config_from_file", return_value=hf_config):
            hf_result = get_model_config()
            assert hf_result["embedding_provider"] == "huggingface"
            assert hf_result["embedding_model"] == "BAAI/bge-large-en-v1.5"
        
        # Test with OpenAI config
        with patch("app.utils.model_config.get_config_from_file", return_value=openai_config):
            openai_result = get_model_config()
            assert openai_result["embedding_provider"] == "openai"
            assert openai_result["embedding_model"] == "text-embedding-3-large" 