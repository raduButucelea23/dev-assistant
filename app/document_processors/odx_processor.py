"""
ODX Document Processor

This module provides functionality to process ODX (Open Diagnostic eXchange) files
and extract relevant information for the vector database.
"""

import os
import re
import time
import logging
import xml.etree.ElementTree as ET
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document

from .base_processor import BaseProcessor

# Set up logger
logger = logging.getLogger(__name__)

class XMLAwareTextSplitter:
    """
    A text splitter that is aware of XML structure and ensures chunks don't break XML elements.
    """
    
    def __init__(self, chunk_size=4000, chunk_overlap=400, max_processing_time=30):
        """
        Initialize the XML-aware text splitter.
        
        Args:
            chunk_size: Target size for each chunk (may exceed for XML integrity)
            chunk_overlap: Overlap between chunks to maintain context
            max_processing_time: Maximum time in seconds to spend on splitting before fallback
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_processing_time = max_processing_time
        
        # Compile regex patterns once for better performance
        self.open_tag_pattern = re.compile(r'<([^/][^>]*?)>')
        self.close_tag_pattern = re.compile(r'</([^>]+)>')
        self.tag_pattern = re.compile(r'<(/?)([^>]+)>')
    
    def split_text(self, text):
        """
        Split text respecting XML element boundaries.
        
        Args:
            text: XML text to split
            
        Returns:
            List of text chunks that preserve XML element integrity
        """
        # Start timer for timeout protection
        start_time = time.time()
        
        # If text is smaller than chunk size, return as is
        if len(text) <= self.chunk_size:
            return [text]
        
        # Try XML-aware splitting with timeout protection
        try:
            chunks = []
            remaining_text = text
            position_tracker = 0  # Track overall position to detect lack of progress
            
            while len(remaining_text) > 0:
                # Check for timeout
                if time.time() - start_time > self.max_processing_time:
                    logger.warning("XML-aware splitting timed out, falling back to simpler method")
                    return self._fallback_split(text)
                
                # Determine end position for this chunk
                end_pos = min(len(remaining_text), self.chunk_size)
                
                # If we're in the middle of an element, find the next closing tag
                if end_pos < len(remaining_text):
                    # Find the last complete element before chunk_size
                    text_segment = remaining_text[:end_pos]
                    last_close_tag = text_segment.rfind('>')
                    
                    if last_close_tag > 0:
                        end_pos = last_close_tag + 1  # Include the closing bracket
                    
                    # Check if we're splitting in the middle of a tag
                    open_tags = self.open_tag_pattern.findall(text_segment)
                    close_tags = self.close_tag_pattern.findall(text_segment)
                    
                    # If we have unclosed tags, try to find a better split point
                    if len(open_tags) > len(close_tags):
                        # Find a balanced point with faster tag matching
                        balanced_end_pos = self._find_balanced_end_point(text_segment)
                        if balanced_end_pos > 0:
                            end_pos = balanced_end_pos
                
                # Detect lack of progress (stuck in the same position)
                if end_pos == 0:
                    logger.warning("No progress made in XML splitting, falling back")
                    return self._fallback_split(text)
                
                # Add the chunk
                chunks.append(remaining_text[:end_pos])
                
                # Determine start of next chunk with overlap
                start_pos = max(0, end_pos - self.chunk_overlap)
                
                # Handle the case where we've processed everything
                if end_pos >= len(remaining_text):
                    break
                
                # Update the remaining text
                old_len = len(remaining_text)
                remaining_text = remaining_text[start_pos:]
                
                # Check if we're making progress
                if len(remaining_text) >= old_len and position_tracker == start_pos:
                    logger.warning("Splitting is not making progress, falling back")
                    return self._fallback_split(text)
                
                position_tracker = start_pos
            
            return chunks
            
        except Exception as e:
            logger.warning(f"Error in XML-aware splitting: {str(e)}. Falling back to simpler method.")
            return self._fallback_split(text)
    
    def _find_balanced_end_point(self, text):
        """
        Find a point where XML tags are balanced.
        Uses a more efficient algorithm that only tracks tag names.
        """
        try:
            # Track opened and closed tags
            tag_stack = []
            last_balanced_pos = 0
            
            # Use pre-compiled regex for better performance
            for match in self.tag_pattern.finditer(text):
                is_closing = match.group(1) == '/'
                tag_name = match.group(2).split()[0]  # Get tag name without attributes
                
                if is_closing:
                    if tag_stack and tag_stack[-1] == tag_name:
                        tag_stack.pop()
                        if not tag_stack:
                            last_balanced_pos = match.end()
                else:
                    # Skip self-closing tags like <tag/>
                    if not tag_name.endswith('/'):
                        tag_stack.append(tag_name)
            
            return last_balanced_pos
        except Exception:
            # If anything goes wrong, return 0 to trigger fallback
            return 0
    
    def _fallback_split(self, text):
        """
        Fallback method when XML-aware splitting fails or times out.
        Simply splits by newlines and approximate length.
        """
        # Use a basic splitter with newlines as separator
        fallback_splitter = CharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separator="\n"
        )
        
        return fallback_splitter.split_text(text)

class ODXProcessor(BaseProcessor):
    """
    Processor for ODX (Open Diagnostic eXchange) files.
    
    ODX is an XML-based format for describing automotive diagnostic systems.
    This class extracts diagnostic service information, parameters, and other
    relevant data from ODX files.
    """
    
    def __init__(self, domain: str = "unknown"):
        """
        Initialize the ODX processor.
        
        Args:
            domain: The semantic domain for the ODX documents
        """
        super().__init__(domain)
        # Use XML-aware text splitter with larger chunk size for XML files
        self.text_splitter = XMLAwareTextSplitter(
            chunk_size=4000,  # Increased chunk size for XML
            chunk_overlap=400  # Increased overlap for better context
        )
    
    def process_file(self, file_path: str) -> list[Document]:
        """
        Process a single ODX file and convert it to Document objects.
        
        Args:
            file_path: Path to the ODX file
            
        Returns:
            List of Document objects with text and metadata
        """
        try:
            logger.info(f"Processing ODX file: {file_path}")
            start_time = time.time()
            
            # Extract basic file metadata
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Read the ODX file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.info(f"Read {len(content)} bytes from {file_name}")
            
            # For extremely large files, use a simpler approach
            if len(content) > 10000000:  # 10MB threshold
                logger.warning(f"File {file_name} is very large ({file_size} bytes), using simplified processing")
                return self._process_large_file(file_path, content, file_name, file_size)
            
            # Try to parse as XML
            try:
                # Parse XML content
                logger.info(f"Parsing XML content for {file_name}")
                root = ET.fromstring(content)
                
                # Extract namespace
                ns = {'odx': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
                
                # Extract meaningful content parts
                content_parts = []
                
                # Process DIAG-SERVICE elements
                services = root.findall('.//odx:DIAG-SERVICE', ns) if ns else root.findall('.//DIAG-SERVICE')
                logger.info(f"Found {len(services)} diagnostic services in {file_name}")
                
                for service in services:
                    # Get service name
                    short_name = service.find('./odx:SHORT-NAME', ns) if ns else service.find('./SHORT-NAME')
                    service_name = short_name.text if short_name is not None and short_name.text else "Unknown Service"
                    
                    # Get service ID
                    service_id = "Unknown ID"
                    id_elem = service.find('./odx:ID', ns) if ns else service.find('./ID')
                    if id_elem is not None and id_elem.text:
                        service_id = id_elem.text
                    
                    # Get service description
                    desc = service.find('./odx:DESC', ns) if ns else service.find('./DESC')
                    service_desc = desc.text if desc is not None and desc.text else "No description"
                    
                    # Format the service information
                    service_info = f"Service: {service_name} (ID: {service_id})\nDescription: {service_desc}\n"
                    
                    # Get parameters if any
                    params = service.findall('.//odx:PARAM', ns) if ns else service.findall('.//PARAM')
                    if params:
                        service_info += "Parameters:\n"
                        for param in params:
                            # Get parameter name
                            param_name_elem = param.find('./odx:SHORT-NAME', ns) if ns else param.find('./SHORT-NAME')
                            param_name = param_name_elem.text if param_name_elem is not None and param_name_elem.text else "Unknown Parameter"
                            
                            # Get parameter description
                            param_desc_elem = param.find('./odx:DESC', ns) if ns else param.find('./DESC')
                            param_desc = param_desc_elem.text if param_desc_elem is not None and param_desc_elem.text else "No description"
                            
                            service_info += f"  - {param_name}: {param_desc}\n"
                    
                    content_parts.append(service_info)
                
                # If we couldn't extract specific diagnostic services, get a general structure
                if not content_parts:
                    logger.info(f"No diagnostic services found, creating structure outline for {file_name}")
                    # Create a simplified text representation without recursion
                    content_parts.append(self._create_structure_outline(root))
                
                # Combine all content parts
                full_content = "\n".join(content_parts)
                
            except ET.ParseError:
                # If XML parsing fails, treat as plain text
                logger.warning(f"XML parsing failed for {file_name}, treating as plain text")
                full_content = f"ODX File Content (non-XML format):\n\n{content[:50000]}"
                if len(content) > 50000:
                    full_content += "... (content truncated for processing)"
            
            # Split the content into chunks using XML-aware splitting
            logger.info(f"Splitting content for {file_name} ({len(full_content)} characters)")
            texts = self.text_splitter.split_text(full_content)
            logger.info(f"Split into {len(texts)} chunks")
            
            # Create metadata for the document
            metadata = {
                "source": file_path,
                "filename": file_name,
                "filetype": "odx",
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
            
            elapsed_time = time.time() - start_time
            logger.info(f"Processed {file_name} in {elapsed_time:.2f} seconds, created {len(documents)} documents")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error processing ODX file {file_path}: {str(e)}")
            raise Exception(f"Error processing ODX file {file_path}: {str(e)}")
    
    def _create_structure_outline(self, root, max_depth=3, max_children=50):
        """
        Create a non-recursive outline of the XML structure to avoid stack overflow.
        
        Args:
            root: The root XML element
            max_depth: Maximum depth to traverse
            max_children: Maximum children to process at each level
            
        Returns:
            Text representation of the XML structure
        """
        result = []
        
        def add_element(elem, depth, path):
            if depth > max_depth:
                return
            
            # Get tag name without namespace
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Add current element
            indent = "  " * depth
            element_text = f"{indent}{tag}"
            if elem.text and elem.text.strip():
                element_text += f": {elem.text.strip()[:100]}"
            result.append(element_text)
            
            # Process children with limit
            children = list(elem)[:max_children]
            if len(list(elem)) > max_children:
                result.append(f"{indent}  ... ({len(list(elem)) - max_children} more elements)")
            
            for child in children:
                add_element(child, depth + 1, path + [tag])
        
        add_element(root, 0, [])
        return "\n".join(result)
    
    def _process_large_file(self, file_path, content, file_name, file_size):
        """
        Simplified processing for very large ODX files.
        
        Args:
            file_path: Path to the file
            content: File content
            file_name: File name
            file_size: File size
            
        Returns:
            List of Document objects
        """
        logger.info(f"Using simplified processing for large file {file_name}")
        
        # Use a basic character splitter with newlines
        simple_splitter = CharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=400,
            separator="\n"
        )
        
        # Create a summary with file stats and initial content
        summary = (
            f"ODX File: {file_name}\n"
            f"Size: {file_size} bytes\n"
            f"Content preview:\n\n"
        )
        
        # Split the file and create documents
        texts = simple_splitter.split_text(summary + content[:100000])
        
        # Create documents
        documents = []
        metadata = {
            "source": file_path,
            "filename": file_name,
            "filetype": "odx",
            "filesize": file_size,
            "domain": self.domain,
            "processing": "simplified"
        }
        
        for i, text in enumerate(texts):
            doc_metadata = metadata.copy()
            doc_metadata["chunk"] = i
            doc_metadata["chunk_count"] = len(texts)
            documents.append(Document(page_content=text, metadata=doc_metadata))
        
        logger.info(f"Created {len(documents)} documents using simplified processing")
        return documents 