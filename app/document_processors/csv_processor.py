import os
import csv
from typing import List, Dict, Any
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

from .base_processor import BaseProcessor


class CSVProcessor(BaseProcessor):
    """Processor for CSV documents.
    
    Handles loading and processing CSV files, including data extraction,
    chunking, and metadata enrichment.
    """
    
    def __init__(self, domain: str = "unknown", chunk_size: int = 2000, chunk_overlap: int = 200):
        """Initialize the CSV processor.
        
        Args:
            domain: The semantic domain for the CSV documents
            chunk_size: Size of text chunks for splitting large content
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
        """Process a CSV file and return a list of Document objects.
        
        Each row of the CSV is converted into a document with appropriate
        metadata. For large CSV files, content may be chunked.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        
        try:
            documents = []
            
            # Load and process the CSV file
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                # Read CSV file
                csv_reader = csv.reader(f)
                headers = next(csv_reader, None)
                
                # If there are no headers, use column indices
                if not headers:
                    return [Document(
                        page_content="Error: CSV file has no headers or is empty",
                        metadata={
                            "source": filename,
                            "source_type": "csv",
                            "domain": self.domain,
                            "error": "Empty CSV file"
                        }
                    )]
                
                # Process each row
                for i, row in enumerate(csv_reader):
                    # Skip empty rows
                    if not any(row):
                        continue
                    
                    # Create row content - either a JSON-like string or formatted text
                    content = ""
                    for j, cell in enumerate(row):
                        if j < len(headers):
                            content += f"{headers[j]}: {cell}\n"
                    
                    # Create row metadata
                    row_metadata = {
                        "source": filename,
                        "source_type": "csv",
                        "domain": self.domain,
                        "row_num": i + 1  # +1 because we skip the header row
                    }
                    
                    # Check if the content needs to be split (for very large cells)
                    if len(content) > self.chunk_size:
                        chunks = self.text_splitter.split_text(content)
                        for chunk_idx, chunk in enumerate(chunks):
                            chunk_metadata = row_metadata.copy()
                            chunk_metadata["chunk"] = chunk_idx
                            documents.append(
                                Document(
                                    page_content=chunk,
                                    metadata=chunk_metadata
                                )
                            )
                    else:
                        documents.append(
                            Document(
                                page_content=content,
                                metadata=row_metadata
                            )
                        )
            
            # If no documents were created (empty CSV with just headers)
            if not documents:
                documents.append(Document(
                    page_content="CSV file contains only headers or empty rows",
                    metadata={
                        "source": filename,
                        "source_type": "csv",
                        "domain": self.domain,
                        "headers": ",".join(headers)
                    }
                ))
                
            return documents
        
        except Exception as e:
            # Return a single document with error information
            error_doc = Document(
                page_content=f"Error processing CSV file: {str(e)}",
                metadata={
                    "source": filename,
                    "source_type": "csv",
                    "domain": self.domain,
                    "error": str(e)
                }
            )
            return [error_doc] 