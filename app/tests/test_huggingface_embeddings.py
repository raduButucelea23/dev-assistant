import os
import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.embeddings.huggingface_embeddings import (
    HuggingFaceEmbeddings, 
    get_huggingface_embeddings
)

# Remove the skip as we'll use mocking instead
# pytestmark = pytest.mark.skipif(
#     os.environ.get("HUGGINGFACE_API_TOKEN") is None,
#     reason="HUGGINGFACE_API_TOKEN environment variable not set"
# )

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
        if isinstance(texts, list):
            return np.random.rand(len(texts), self.dimension).astype(np.float32)
        else:
            return np.random.rand(self.dimension).astype(np.float32)

class TestHuggingFaceEmbeddings:
    """Tests for the HuggingFaceEmbeddings class."""
    
    @patch("app.embeddings.huggingface_embeddings.SentenceTransformer", MockSentenceTransformer)
    @patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "mock-token"})
    def test_initialization(self):
        """Test that the embeddings object initializes correctly."""
        embeddings = get_huggingface_embeddings()
        assert embeddings.model_name == "BAAI/bge-large-en-v1.5"
        assert embeddings.device == "cpu"
        
    @patch("app.embeddings.huggingface_embeddings.SentenceTransformer", MockSentenceTransformer)
    @patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "mock-token"})
    def test_get_model(self):
        """Test that the model can be loaded."""
        embeddings = get_huggingface_embeddings()
        model = embeddings._get_model()
        assert model is not None
        # Check that the model has the expected embedding dimension
        assert model.get_sentence_embedding_dimension() == 1024  # BGE-large has 1024 dimensions
        
    @patch("app.embeddings.huggingface_embeddings.SentenceTransformer", MockSentenceTransformer)
    @patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "mock-token"})
    def test_embed_documents(self):
        """Test embedding multiple documents."""
        embeddings = get_huggingface_embeddings()
        texts = ["This is a test document", "Another test document"]
        result = embeddings.embed_documents(texts)
        
        # Check shape and type
        assert len(result) == 2
        assert all(len(emb) == embeddings.get_embedding_dimension() for emb in result)
        assert all(isinstance(emb, list) for emb in result)
        assert all(isinstance(val, float) for emb in result for val in emb)
        
    @patch("app.embeddings.huggingface_embeddings.SentenceTransformer", MockSentenceTransformer)
    @patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "mock-token"})
    def test_embed_query(self):
        """Test embedding a single query."""
        embeddings = get_huggingface_embeddings()
        query = "Test query"
        result = embeddings.embed_query(query)
        
        # Check shape and type
        assert len(result) == embeddings.get_embedding_dimension()
        assert isinstance(result, list)
        assert all(isinstance(val, float) for val in result)
        
    @patch("app.embeddings.huggingface_embeddings.SentenceTransformer", MockSentenceTransformer)
    @patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "mock-token"})
    def test_empty_input(self):
        """Test handling of empty inputs."""
        embeddings = get_huggingface_embeddings()
        
        # Empty list of documents
        result = embeddings.embed_documents([])
        assert result == []
        
        # Empty string
        query_result = embeddings.embed_query("")
        assert len(query_result) == embeddings.get_embedding_dimension()
        
    @patch("app.embeddings.huggingface_embeddings.SentenceTransformer", MockSentenceTransformer)
    @patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "mock-token"})
    def test_get_embedding_dimension(self):
        """Test getting the embedding dimension."""
        embeddings = get_huggingface_embeddings()
        dim = embeddings.get_embedding_dimension()
        assert dim == 1024  # BGE-large has 1024 dimensions
        
    @patch("app.embeddings.huggingface_embeddings.SentenceTransformer", MockSentenceTransformer)
    @patch.dict(os.environ, {"HUGGINGFACE_API_TOKEN": "mock-token"})
    def test_different_model(self):
        """Test using a different model."""
        embeddings = get_huggingface_embeddings(model_name="Alibaba-NLP/gte-large-en-v1.5")
        assert embeddings.model_name == "Alibaba-NLP/gte-large-en-v1.5"
        
        # Test embedding
        result = embeddings.embed_query("Test query")
        assert len(result) == 1024  # GTE-large also has 1024 dimensions 