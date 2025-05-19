from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import hashlib
import os
import datetime
from langchain_core.documents.base import Document


@dataclass
class DocumentTraceability:
    """Track source document information for embeddings."""
    
    # Document identification
    doc_id: str                # Unique identifier (hash of content)
    source_path: str           # Original file path
    filename: str              # Original filename
    file_type: str             # File extension/type (pdf, json, etc.)
    
    # Processing metadata
    embedding_model: str       # Model used for embeddings
    embedding_provider: str    # Provider used for embeddings (openai, huggingface)
    embedding_date: str        # Date/time when embedding was created
    chunk_id: Optional[int] = None  # Chunk number if document was split
    domain: str = "unknown"    # Semantic domain
    
    # Document stats
    file_size: int = 0         # Size in bytes
    chunk_count: int = 1       # Total chunks the document was split into
    
    @classmethod
    def from_document(cls, doc: Document, embedding_model: str, embedding_provider: str = "openai", source_path: str = None) -> 'DocumentTraceability':
        """Create traceability info from a Document object."""
        # Generate a unique document ID based on content
        doc_id = hashlib.md5(doc.page_content.encode()).hexdigest()
        
        # Extract filename from path or metadata
        if source_path:
            filename = os.path.basename(source_path)
        else:
            source_path = doc.metadata.get("source", "unknown")
            filename = os.path.basename(source_path)
        
        # Get file type from extension or metadata
        file_type = doc.metadata.get("source_type", os.path.splitext(filename)[1].lstrip("."))
        
        # Get chunk info
        chunk_id = doc.metadata.get("chunk", None)
        chunk_count = doc.metadata.get("chunk_count", 1)
        
        # Get domain
        domain = doc.metadata.get("domain", "unknown")
        
        # Get file size if available
        file_size = doc.metadata.get("filesize", 0)
        
        return cls(
            doc_id=doc_id,
            source_path=source_path,
            filename=filename,
            file_type=file_type,
            embedding_model=embedding_model,
            embedding_provider=embedding_provider,
            embedding_date=datetime.datetime.now().isoformat(),
            chunk_id=chunk_id,
            domain=domain,
            file_size=file_size,
            chunk_count=chunk_count
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self) 