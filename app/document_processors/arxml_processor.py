"""
ARXML Document Processor

This module provides functionality to process ARXML (AUTOSAR XML) files and extract 
relevant information for the vector database.
"""

import os
import xml.etree.ElementTree as ET
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document

from .base_processor import BaseProcessor

class ARXMLProcessor(BaseProcessor):
    """
    Processor for ARXML (AUTOSAR XML) files.
    
    This class extracts data from ARXML files, which are XML files used in automotive 
    software development based on the AUTOSAR standard.
    """
    
    def __init__(self, domain: str = "unknown"):
        """
        Initialize the ARXML processor.
        
        Args:
            domain: The semantic domain for the ARXML documents
        """
        super().__init__(domain)
        self.text_splitter = CharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            separator="\n"
        )
        
    def process_file(self, file_path: str) -> list[Document]:
        """
        Process a single ARXML file and convert it to Document objects.
        
        Args:
            file_path: Path to the ARXML file
            
        Returns:
            List of Document objects with text and metadata
        """
        try:
            # Extract basic file metadata
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Parse the ARXML file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract namespace
            ns = {'ar': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
            
            # Extract meaningful content as text
            content_parts = []
            
            # Process SHORT-NAME elements (typically represent interface names)
            for short_name in root.findall('.//ar:SHORT-NAME', ns) if ns else root.findall('.//SHORT-NAME'):
                parent = short_name.getparent() if hasattr(short_name, 'getparent') else None
                parent_tag = parent.tag.split('}')[-1] if parent is not None and '}' in parent.tag else "Unknown"
                content_parts.append(f"{parent_tag}: {short_name.text}")
                
            # Process DEFINITION elements (typically contain interface descriptions)
            for definition in root.findall('.//ar:DEFINITION', ns) if ns else root.findall('.//DEFINITION'):
                content_parts.append(f"Definition: {definition.text}")
                
            # Process DESC elements (descriptions)
            for desc in root.findall('.//ar:DESC', ns) if ns else root.findall('.//DESC'):
                content_parts.append(f"Description: {desc.text}")
            
            # Combine all content parts
            full_content = "\n".join([part for part in content_parts if part])
            
            # If we couldn't extract meaningful content, use a basic representation
            if not full_content:
                # Create a simple text representation of the XML structure
                def element_to_text(elem, indent=0):
                    result = " " * indent + elem.tag.split('}')[-1]
                    if elem.text and elem.text.strip():
                        result += ": " + elem.text.strip()
                    result += "\n"
                    for child in elem:
                        result += element_to_text(child, indent + 2)
                    return result
                
                full_content = element_to_text(root)
            
            # Split the content into chunks
            texts = self.text_splitter.split_text(full_content)
            
            # Create metadata for the document
            metadata = {
                "source": file_path,
                "filename": file_name,
                "filetype": "arxml",
                "filesize": file_size,
                "domain": self.domain,
            }
            
            # Create Document objects for each chunk
            documents = []
            for i, text in enumerate(texts):
                doc_metadata = metadata.copy()
                doc_metadata["chunk"] = i
                doc_metadata["chunk_count"] = len(texts)
                
                documents.append(Document(page_content=text, metadata=doc_metadata))
                
            return documents
            
        except Exception as e:
            raise Exception(f"Error processing ARXML file {file_path}: {str(e)}") 