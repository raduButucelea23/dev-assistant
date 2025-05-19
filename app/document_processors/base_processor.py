from abc import ABC, abstractmethod
from typing import List, Dict, Any
from langchain_core.documents.base import Document


class BaseProcessor(ABC):
    """Abstract base class for document processors.
    
    All document processors should inherit from this class and implement
    the process_document method to handle specific document formats.
    """
    
    def __init__(self, domain: str = "unknown"):
        """Initialize the document processor.
        
        Args:
            domain: The semantic domain for the documents to be processed
        """
        self.domain = domain
    
    @abstractmethod
    def process_file(self, file_path: str) -> List[Document]:
        """Process a document file and return a list of Document objects.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of Document objects with content and metadata
        """
        pass
    
    def add_metadata(self, document: Document, metadata: Dict[str, Any]) -> Document:
        """Add metadata to a document.
        
        Args:
            document: The document to add metadata to
            metadata: The metadata to add
            
        Returns:
            Document with added metadata
        """
        # Add domain if not already present
        if 'domain' not in metadata:
            metadata['domain'] = self.domain
        
        # Update document metadata
        if not hasattr(document, 'metadata'):
            document.metadata = metadata
        else:
            document.metadata.update(metadata)
        
        return document
    
    def add_metadata_to_documents(self, documents: List[Document], metadata: Dict[str, Any]) -> List[Document]:
        """Add metadata to a list of documents.
        
        Args:
            documents: List of documents to add metadata to
            metadata: The metadata to add
            
        Returns:
            List of documents with added metadata
        """
        return [self.add_metadata(doc, metadata) for doc in documents]
        
    def validate_documents(self, documents: List) -> List[Document]:
        """Validate and clean a list of documents to ensure they are all proper Document objects.
        
        Args:
            documents: List of potential Document objects
            
        Returns:
            List containing only valid Document objects
        """
        valid_documents = []
        for i, doc in enumerate(documents):
            if not isinstance(doc, Document):
                print(f"WARNING: Document at index {i} is not a Document object. Type: {type(doc).__name__}")
                # Skip invalid documents
                continue
                
            valid_documents.append(doc)
                
        if len(valid_documents) < len(documents):
            print(f"WARNING: Filtered out {len(documents) - len(valid_documents)} invalid documents")
            
        return valid_documents
