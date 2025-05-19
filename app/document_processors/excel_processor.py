import os
import pandas as pd
from typing import List, Dict, Any
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

from .base_processor import BaseProcessor


class ExcelProcessor(BaseProcessor):
    """Processor for Excel documents.
    
    Handles loading and processing Excel files, including data extraction,
    chunking, and metadata enrichment.
    """
    
    def __init__(self, domain: str = "unknown", chunk_size: int = 2000, chunk_overlap: int = 200):
        """Initialize the Excel processor.
        
        Args:
            domain: The semantic domain for the Excel documents
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
        """Process an Excel file and return a list of Document objects.
        
        Each sheet is processed separately, and each row is converted into a document
        with appropriate metadata. For large Excel files, content may be chunked.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        
        try:
            documents = []
            
            # Try to load all sheets from the Excel file
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Process each sheet
            for sheet_name in sheet_names:
                # Read the Excel sheet into a pandas DataFrame
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    documents.append(Document(
                        page_content=f"Sheet '{sheet_name}' is empty",
                        metadata={
                            "source": filename,
                            "source_type": "excel",
                            "sheet": sheet_name,
                            "domain": self.domain,
                            "note": "Empty sheet"
                        }
                    ))
                    continue
                
                # Process each row
                for i, row in df.iterrows():
                    # Format the row content as key-value pairs
                    content = ""
                    for column in df.columns:
                        content += f"{column}: {row[column]}\n"
                    
                    # Create row metadata
                    row_metadata = {
                        "source": filename,
                        "source_type": "excel",
                        "sheet": sheet_name,
                        "domain": self.domain,
                        "row_num": i + 2  # +2 because Excel is 1-indexed and row 1 is the header
                    }
                    
                    # Check if the content needs to be split (for very large rows)
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
            
            # If no documents were created (all sheets empty)
            if not documents:
                documents.append(Document(
                    page_content=f"Excel file contains only empty sheets",
                    metadata={
                        "source": filename,
                        "source_type": "excel",
                        "domain": self.domain,
                        "sheets": ",".join(sheet_names)
                    }
                ))
                
            return documents
        
        except Exception as e:
            # Return a single document with error information
            error_doc = Document(
                page_content=f"Error processing Excel file: {str(e)}",
                metadata={
                    "source": filename,
                    "source_type": "excel",
                    "domain": self.domain,
                    "error": str(e)
                }
            )
            return [error_doc] 