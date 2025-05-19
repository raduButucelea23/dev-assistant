import os
import sys
import pytest
import tempfile
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

@pytest.fixture(scope="function")
def save_env():
    """Save and restore environment variables."""
    old_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(old_env)

@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception:
        pass

@pytest.fixture(scope="function")
def mock_huggingface_config():
    """Return a mock HuggingFace configuration."""
    return {
        "embedding_provider": "huggingface",
        "embedding_model": "BAAI/bge-large-en-v1.5",
        "llm_provider": "huggingface",
        "llm_model": "meta-llama/Llama-3.3-70B-Instruct"
    }

@pytest.fixture(scope="function")
def mock_openai_config():
    """Return a mock OpenAI configuration."""
    return {
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-large",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini"
    }

@pytest.fixture(scope="function")
def test_documents():
    """Create a set of test documents."""
    from langchain_core.documents.base import Document
    
    return [
        Document(
            page_content="This is a test document about automotive systems.",
            metadata={"source": "test1.txt", "domain": "automotive"}
        ),
        Document(
            page_content="Another document about vehicle diagnostics.",
            metadata={"source": "test2.txt", "domain": "automotive"}
        ),
        Document(
            page_content="Information about engine control units.",
            metadata={"source": "test3.txt", "domain": "automotive"}
        )
    ]

@pytest.fixture(scope="function")
def mock_document():
    """Create a mock document for tests."""
    from langchain_core.documents.base import Document
    
    return Document(
        page_content="This is a test document content.",
        metadata={
            "source": "test_source.txt",
            "domain": "test_domain",
            "file_type": "txt",
            "page": 1
        }
    )

@pytest.fixture(scope="function")
def mock_documents():
    """Create a list of mock documents for tests."""
    from langchain_core.documents.base import Document
    
    return [
        Document(
            page_content=f"This is test document {i} content.",
            metadata={
                "source": f"test_source_{i}.txt",
                "domain": "test_domain",
                "file_type": "txt",
                "page": i
            }
        )
        for i in range(5)
    ] 