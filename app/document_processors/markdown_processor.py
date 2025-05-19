import os
from typing import List, Dict, Any
from langchain_core.documents.base import Document
from langchain.text_splitter import CharacterTextSplitter

from .base_processor import BaseProcessor


class MarkdownProcessor(BaseProcessor):
    """Processor for Markdown documents.
    
    Handles loading and processing markdown files, including text extraction,
    chunking, and metadata enrichment.
    """
    
    def __init__(self, domain: str = "unknown", chunk_size: int = 2000, chunk_overlap: int = 200):
        """Initialize the Markdown processor.
        
        Args:
            domain: The semantic domain for the markdown documents
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        super().__init__(domain)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = CharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process a markdown file and return a list of Document objects.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        
        try:
            # Load the markdown file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Create metadata
            metadata = {
                "source": filename,
                "source_type": "markdown",
                "domain": self.domain
            }
            
            # Check if the content needs to be split
            if len(content) > self.chunk_size:
                # Split the content
                chunks = self.text_splitter.split_text(content)
                
                # Create documents from chunks
                documents = []
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk"] = i
                    documents.append(
                        Document(
                            page_content=chunk,
                            metadata=chunk_metadata
                        )
                    )
                return self.validate_documents(documents)
            else:
                # Create a single document
                doc = Document(
                    page_content=content,
                    metadata=metadata
                )
                return self.validate_documents([doc])
        
        except Exception as e:
            # Return a single document with error information
            error_doc = Document(
                page_content=f"Error processing markdown file: {str(e)}",
                metadata={
                    "source": filename,
                    "source_type": "markdown",
                    "domain": self.domain,
                    "error": str(e)
                }
            )
            return self.validate_documents([error_doc])
