import os
import sys
import unittest
import json
import shutil
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import the app modules
script_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(app_dir)
sys.path.append(root_dir)

from app.utils.model_config import (
    get_model_config,
    save_config_to_file,
    get_available_models,
    get_available_providers,
    CONFIG_FILE_PATH
)


class TestModelSettingsUI(unittest.TestCase):
    """Test the model settings UI functionality"""
    
    def setUp(self):
        """Set up a temporary config file for testing"""
        # Create backup of existing config
        self.config_backup = None
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r') as f:
                self.config_backup = f.read()
        
        # Test config with different providers
        self.test_config = {
            "_comment_1": "MODEL CONFIGURATION",
            "_comment_2": "This file defines the default models for Auto-Dev Assistant",
            "_comment_3": "Changes here will apply to all users without requiring environment variables",
            
            "provider": "huggingface",
            "_provider_options": ["huggingface", "openai"],
            
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
        
        # Write test config
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(self.test_config, f, indent=2)
    
    def tearDown(self):
        """Restore the original config file"""
        if self.config_backup:
            with open(CONFIG_FILE_PATH, 'w') as f:
                f.write(self.config_backup)
    
    def test_change_models(self):
        """Test changing models and verifying config changes"""
        # Get initial config
        initial_config = get_model_config()
        
        # Create new config with different models
        new_config = {
            "provider": "openai",
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-large",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini"
        }
        
        # Save new config
        result = save_config_to_file(new_config)
        self.assertTrue(result, "Config file save failed")
        
        # Load updated config
        updated_config = get_model_config()
        
        # Verify changes
        self.assertEqual(updated_config["provider"], "openai")
        self.assertEqual(updated_config["embedding_provider"], "openai")
        self.assertEqual(updated_config["embedding_model"], "text-embedding-3-large")
        self.assertEqual(updated_config["llm_provider"], "openai")
        self.assertEqual(updated_config["llm_model"], "gpt-4o-mini")
        
        # Check that comments and other fields were preserved
        with open(CONFIG_FILE_PATH, 'r') as f:
            saved_config = json.load(f)
        
        self.assertIn("_comment_1", saved_config)
        self.assertIn("default_configs", saved_config)
    
    def test_mixed_providers(self):
        """Test using different providers for embedding and LLM"""
        # Create mixed provider config
        mixed_config = {
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-large",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        # Save config
        result = save_config_to_file(mixed_config)
        self.assertTrue(result, "Config file save failed")
        
        # Load updated config
        updated_config = get_model_config()
        
        # Verify changes
        self.assertEqual(updated_config["embedding_provider"], "openai")
        self.assertEqual(updated_config["embedding_model"], "text-embedding-3-large")
        self.assertEqual(updated_config["llm_provider"], "huggingface")
        self.assertEqual(updated_config["llm_model"], "meta-llama/Llama-3.3-70B-Instruct")


if __name__ == "__main__":
    unittest.main() 