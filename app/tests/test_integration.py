import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from langchain_core.documents.base import Document

from app.embeddings.db_manager import DBManager
from app.embeddings.huggingface_embeddings import get_huggingface_embeddings
from app.api.huggingface_client import get_huggingface_client
from app.utils.model_config import get_model_config

# Mock the SentenceTransformer class
class MockSentenceTransformer:
    def __init__(self, model_name_or_path, device="cpu", cache_folder=None, **kwargs):
        self.model_name = model_name_or_path
        self.device = device
        self.cache_folder = cache_folder
        self.kwargs = kwargs
        self.dimension = 1024  # Default for tests
        
    def get_sentence_embedding_dimension(self):
        return self.dimension
        
    def encode(self, texts, **kwargs):
        # Return fake embeddings of correct dimension
        import numpy as np
        if isinstance(texts, list):
            return np.random.rand(len(texts), self.dimension).astype(np.float32)
        else:
            return np.random.rand(self.dimension).astype(np.float32)

# Mock the ChromaDB collection
class MockChromaCollection:
    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.metadatas = []
        self.ids = []
        
    def count(self):
        return len(self.documents)
        
    def add(self, documents, embeddings, metadatas, ids):
        self.documents.extend(documents)
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)

# Mock the ChromaDB client
class MockChromaClient:
    def __init__(self, path=None):
        self.path = path
        self.collection = MockChromaCollection()
        
    def get_or_create_collection(self, name):
        return self.collection

# Mock Chroma vector store
class MockChroma:
    def __init__(self, persist_directory=None, embedding_function=None, client=None):
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self.client = client
        self._collection = client.collection if client else MockChromaCollection()
    
    @classmethod
    def from_documents(cls, documents, embedding, persist_directory=None, client=None):
        chroma = cls(persist_directory=persist_directory, embedding_function=embedding, client=client)
        # Create a mock collection with the documents
        if client and hasattr(client, 'collection'):
            for i, doc in enumerate(documents):
                client.collection.add(
                    documents=[doc.page_content],
                    embeddings=[[0.1] * 1024],  # Fake embeddings
                    metadatas=[doc.metadata],
                    ids=[f"doc{i}"]
                )
        return chroma
    
    def similarity_search(self, query, k=5, filter_dict=None):
        # Return original documents that match the query (for simplicity)
        # In a real implementation, this would perform vector similarity search
        result = []
        for _ in range(min(k, self._collection.count())):
            # Create a fake document that includes the query term
            result.append(Document(page_content=f"Document matching {query}", metadata={"source": "test.txt"}))
        return result
    
    def add_documents(self, documents):
        # Add documents to the collection
        for i, doc in enumerate(documents):
            self._collection.add(
                documents=[doc.page_content],
                embeddings=[[0.1] * 1024],  # Fake embeddings
                metadatas=[doc.metadata],
                ids=[f"add{i}"]
            )

# Mock for filter_complex_metadata
def mock_filter_complex_metadata(metadata):
    # Simply return the metadata unchanged
    return metadata

# Simplified test class to test our model configuration changes
class TestIntegration:
    """Integration tests for the file-based model configuration."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Create a temporary directory 
        self.temp_dir = tempfile.mkdtemp()
        
        # Save current environment for API keys
        self.old_env = os.environ.copy()
        
        # Set API tokens for testing
        os.environ["HUGGINGFACE_API_TOKEN"] = "mock-token"
        os.environ["OPENAI_API_KEY"] = "mock-openai-key"
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
        
        # Restore environment
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_model_config_integration(self):
        """Test that model_config correctly loads from file."""
        # Create huggingface config
        hf_config = {
            "embedding_provider": "huggingface",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "llm_provider": "huggingface",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
        }
        
        # Create openai config
        openai_config = {
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-large",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini"
        }
        
        # Test with HuggingFace config
        with patch("app.utils.model_config.get_config_from_file", return_value=hf_config):
            config = get_model_config()
            
            # Check config values
            assert config["embedding_provider"] == "huggingface"
            assert config["embedding_model"] == "BAAI/bge-large-en-v1.5"
            assert config["llm_provider"] == "huggingface"
            assert config["llm_model"] == "meta-llama/Llama-3.3-70B-Instruct"
            
            # Verify DBManager uses this config
            with patch("app.embeddings.db_manager.logger"):  # Mock logger to avoid output
                db_manager = DBManager(
                    persist_directory=self.temp_dir,
                    embedding_provider=config["embedding_provider"],
                    embedding_model=config["embedding_model"]
                )
                
                # Check DBManager config
                assert db_manager.embedding_provider == "huggingface"
                assert db_manager.embedding_model == "BAAI/bge-large-en-v1.5"
        
        # Test with OpenAI config
        with patch("app.utils.model_config.get_config_from_file", return_value=openai_config):
            config = get_model_config()
            
            # Check config values
            assert config["embedding_provider"] == "openai"
            assert config["embedding_model"] == "text-embedding-3-large"
            assert config["llm_provider"] == "openai" 
            assert config["llm_model"] == "gpt-4o-mini"
            
            # Verify DBManager uses this config
            with patch("app.embeddings.db_manager.logger"):  # Mock logger to avoid output
                db_manager = DBManager(
                    persist_directory=self.temp_dir,
                    embedding_provider=config["embedding_provider"],
                    embedding_model=config["embedding_model"]
                )
                
                # Check DBManager config
                assert db_manager.embedding_provider == "openai"
                assert db_manager.embedding_model == "text-embedding-3-large" 