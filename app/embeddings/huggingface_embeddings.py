import os
import numpy as np
from typing import List, Dict, Any, Optional
from langchain_core.embeddings import Embeddings
from langchain_core.pydantic_v1 import BaseModel, Field, PrivateAttr
import torch
from sentence_transformers import SentenceTransformer
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HuggingFaceEmbeddings(BaseModel, Embeddings):
    """HuggingFace embeddings wrapper for sentence_transformers models.
    
    This class provides a wrapper around HuggingFace's sentence_transformers models
    to generate embeddings that are compatible with LangChain's vector stores.
    """
    
    model_name: str = Field("BAAI/bge-large-en-v1.5")
    device: str = Field("cpu")
    model_kwargs: Dict[str, Any] = Field(default_factory=dict)
    encode_kwargs: Dict[str, Any] = Field(default_factory=dict)
    cache_folder: Optional[str] = Field(default=None)
    
    # Use PrivateAttr instead of Field for internal attributes
    _model: Optional[SentenceTransformer] = PrivateAttr(default=None)
    
    def __init__(self, **kwargs):
        """Initialize the HuggingFace embeddings wrapper."""
        # Get cache folder from environment if not provided
        if "cache_folder" not in kwargs or kwargs["cache_folder"] is None:
            env_cache = os.getenv("HUGGINGFACE_HUB_CACHE")
            if env_cache:
                kwargs["cache_folder"] = env_cache
                logger.info(f"Using HuggingFace cache from environment: {env_cache}")
        
        super().__init__(**kwargs)
        
        # Double-check and log cache location
        if self.cache_folder:
            logger.info(f"HuggingFace embeddings will use cache folder: {self.cache_folder}")
            # Ensure directory exists
            os.makedirs(self.cache_folder, exist_ok=True)
        
        # Set default encode_kwargs if not provided
        if "normalize_embeddings" not in self.encode_kwargs:
            self.encode_kwargs["normalize_embeddings"] = True
            
        # Set default model_kwargs if not provided
        if not self.model_kwargs:
            self.model_kwargs = {}
            
    def _get_model(self) -> SentenceTransformer:
        """Get or initialize the sentence transformer model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            logger.info(f"Using cache folder: {self.cache_folder or 'default'}")
            
            # Check if CUDA is available and requested
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available. Using CPU instead.")
                self.device = "cpu"
                
            # Load the model with specified parameters
            try:
                self._model = SentenceTransformer(
                    model_name_or_path=self.model_name,
                    device=self.device,
                    cache_folder=self.cache_folder,
                    **self.model_kwargs
                )
                logger.info(f"Successfully loaded model {self.model_name}, embedding dimension: {self._model.get_sentence_embedding_dimension()}")
            except Exception as e:
                logger.error(f"Error loading embedding model {self.model_name}: {str(e)}")
                raise
                
        return self._model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents.
        
        Args:
            texts: List of document texts to embed
            
        Returns:
            List of embeddings, one for each document
        """
        model = self._get_model()
        
        try:
            # Handle empty inputs
            if not texts:
                return []
                
            # Convert inputs to strings (model requires string input)
            texts = [str(text) for text in texts]
            
            # Generate embeddings using the model
            embeddings = model.encode(texts, **self.encode_kwargs)
            
            # Convert to list of lists (LangChain compatibility)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating document embeddings: {str(e)}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embeddings for a single query text.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding for the query
        """
        model = self._get_model()
        
        try:
            # Convert input to string
            text = str(text)
            
            # Generate embedding
            embedding = model.encode(text, **self.encode_kwargs)
            
            # Convert to list (LangChain compatibility)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise
            
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings produced by this model.
        
        Returns:
            Dimension of the embeddings
        """
        model = self._get_model()
        return model.get_sentence_embedding_dimension()


def get_huggingface_embeddings(model_name="BAAI/bge-large-en-v1.5", device="cpu", cache_folder=None):
    """Convenience function to get HuggingFace embeddings instance.
    
    Args:
        model_name: Name of the HuggingFace model to use
        device: Device to run the model on ("cpu" or "cuda")
        cache_folder: Optional folder to cache models
        
    Returns:
        HuggingFaceEmbeddings instance
    """
    # If cache_folder is not provided, try getting from environment
    if cache_folder is None:
        cache_folder = os.getenv("HUGGINGFACE_HUB_CACHE")
        
    return HuggingFaceEmbeddings(
        model_name=model_name,
        device=device,
        cache_folder=cache_folder
    ) 