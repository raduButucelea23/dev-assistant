import os
from typing import List, Dict, Any
from langchain_core.documents.base import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter

from .base_processor import BaseProcessor


class PDFProcessor(BaseProcessor):
    """Processor for PDF documents.
    
    Handles loading and processing PDF files, including text extraction,
    chunking, and metadata enrichment.
    """
    
    def __init__(self, domain: str = "unknown", chunk_size: int = 2000, chunk_overlap: int = 200):
        """Initialize the PDF processor.
        
        Args:
            domain: The semantic domain for the PDF documents
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
        """Process a PDF file and return a list of Document objects.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        
        # Load the PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load_and_split()
        
        # Add basic metadata
        for doc in documents:
            doc.metadata["source_type"] = "pdf"
            doc.metadata["source"] = filename
            doc.metadata["domain"] = self.domain
        
        # Split the documents into chunks if they're too large
        chunked_docs = []
        for doc in documents:
            # Check if the document needs to be split
            if len(doc.page_content) > self.chunk_size:
                # Split the document
                chunks = self.text_splitter.split_text(doc.page_content)
                
                # Create new documents with the chunks
                for i, chunk in enumerate(chunks):
                    new_doc = Document(
                        page_content=chunk,
                        metadata=doc.metadata.copy()
                    )
                    # Add chunk information to metadata
                    new_doc.metadata["chunk"] = i
                    chunked_docs.append(new_doc)
            else:
                chunked_docs.append(doc)
        
        # Validate documents before returning
        chunked_docs = self.validate_documents(chunked_docs)
        
        return chunked_docs
