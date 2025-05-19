import os
import json
from typing import List, Dict, Any
from langchain_core.documents.base import Document
import re

# Try relative imports first
try:
    from .base_processor import BaseProcessor
    from ..utils.text_processing import extract_json_content, create_semantic_chunks
    from ..utils.metadata_extraction import extract_json_metadata
except ImportError:
    # Fall back to absolute imports if relative imports fail
    from app.document_processors.base_processor import BaseProcessor
    from app.utils.text_processing import extract_json_content, create_semantic_chunks
    from app.utils.metadata_extraction import extract_json_metadata


class JSONProcessor(BaseProcessor):
    """Processor for JSON documents.
    
    Handles loading and processing JSON files, with special handling for
    service definitions and technical specifications.
    """
    
    def __init__(self, domain: str = "unknown"):
        """Initialize the JSON processor.
        
        Args:
            domain: The semantic domain for the JSON documents
        """
        super().__init__(domain)
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process a JSON file and return a list of Document objects.
        
        This method uses semantic chunking instead of naive text chunking to
        preserve the relationships in structured JSON data.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        
        try:
            # Load the JSON file
            with open(file_path, 'r') as f:
                json_content = json.load(f)
            
            # Extract formatted content for better searchability
            formatted_content = extract_json_content(json_content)
            
            # Extract metadata for improved retrieval
            metadata = extract_json_metadata(json_content)
            
            # Add source information to metadata
            metadata["source"] = filename
            metadata["source_type"] = "json"
            metadata["domain"] = self.domain
            
            # Use the improved create_semantic_chunks function with the JSON data
            try:
                documents = create_semantic_chunks(formatted_content, metadata, json_content)
                
                # Add debug code to check the returned documents
                print(f"DEBUG - JSONProcessor: Got {len(documents)} documents from create_semantic_chunks")
                for i, doc in enumerate(documents):
                    print(f"DEBUG - JSONProcessor: Document {i} type: {type(doc).__name__}")
                    if not isinstance(doc, Document):
                        print(f"DEBUG - JSONProcessor: Document {i} is not a Document object! It's a {type(doc).__name__}")
                
                # Validate documents before returning
                documents = self.validate_documents(documents)
                
                return documents
            except Exception as e:
                # If there's an error in the chunking process, fall back to a simple document
                print(f"Error during semantic chunking: {str(e)}")
                simple_doc = Document(
                    page_content=formatted_content,
                    metadata=metadata
                )
                return [simple_doc]
        
        except Exception as e:
            # Return a single document with error information
            error_doc = Document(
                page_content=f"Error processing JSON file: {str(e)}",
                metadata={
                    "source": filename,
                    "source_type": "json",
                    "domain": self.domain,
                    "error": str(e)
                }
            )
            return [error_doc]
