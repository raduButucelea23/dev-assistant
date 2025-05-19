import json
import re
from langchain_core.documents.base import Document
from .metadata_extraction import safe_get
from typing import Dict, Any, List
from langchain.text_splitter import RecursiveCharacterTextSplitter


def extract_json_content(json_data: Dict[str, Any]) -> str:
    """
    Extract readable content from JSON file structure with improved structure and contextual info.
    
    Args:
        json_data: The parsed JSON data
        
    Returns:
        Formatted string representation of the JSON content
    """
    # Start with a summary section that includes likely search terms
    content = "# SUMMARY\n"
    data_object_name = safe_get(json_data, 'DataObjectName')
    object_type = safe_get(json_data, 'ObjectType')
    
    content += f"This document describes the {data_object_name} {object_type}.\n\n"
    
    # Extract Service Name for prominent display
    service = json_data.get('Service', {})
    service_name = safe_get(service, 'Name')
    if service_name:
        content += f"Service: {service_name}\n"
    
    # Create a section for basic data object information
    content += "\n# BASIC INFORMATION\n"
    content += f"DataObjectName: {data_object_name}\n"
    content += f"ObjectType: {object_type}\n"
    content += f"Source: {safe_get(json_data, 'SourceDevice')} ({safe_get(json_data, 'SourceAplication')})\n"
    content += f"Destination: {safe_get(json_data, 'DestinationDevice')} ({safe_get(json_data, 'DestinationApplication')})\n"
    content += f"Protocol: {safe_get(json_data, 'TransportProtocol')}\n"
    
    # Create a dedicated service section
    if service:
        content += "\n# SERVICE DETAILS\n"
        content += f"Service Name: {service_name}\n"
        content += f"Service ID: {safe_get(service, 'ServiceID')}\n"
        content += f"Instance ID: {safe_get(service, 'InstanceId')}\n"
        content += f"Role: {safe_get(service, 'Role')}\n"
        
        # Add structured information about each method
        methods = service.get('Methods', [])
        if methods:
            content += "\n## METHODS\n"
            for method in methods:
                method_name = safe_get(method, 'MethodName', 'unnamed')
                method_id = safe_get(method, 'MethodId')
                content += f"### Method: {method_name} (ID: {method_id})\n"
                content += f"Request Message: {safe_get(method, 'RequestMessage')}\n"
                content += f"Response Message: {safe_get(method, 'ResponseMessage')}\n\n"
        
        # Add Events section
        event_groups = service.get('EventGroups', [])
        if event_groups:
            content += "\n## EVENTS\n"
            for group in event_groups:
                group_id = safe_get(group, 'EventGroupId')
                content += f"### Event Group ID: {group_id}\n"
                for event in group.get('Events', []):
                    event_message = safe_get(event, 'EventMessage')
                    event_id = safe_get(event, 'EventID')
                    content += f"Event: {event_message} (ID: {event_id})\n"
                content += "\n"
    
    # Add Data Types section - structured format for better retention
    data_types = safe_get(json_data, 'DataTypes')
    if data_types:
        content += "\n# DATA TYPES\n"
        # Handle data types carefully to avoid truncation of important information
        if isinstance(data_types, dict):
            # Format each data type definition
            for type_name, type_def in data_types.items():
                content += f"## {type_name}\n"
                if isinstance(type_def, dict):
                    for key, value in type_def.items():
                        # Limit individual value length
                        str_value = str(value)
                        if len(str_value) > 500:
                            str_value = str_value[:500] + "...(truncated)"
                        content += f"{key}: {str_value}\n"
                else:
                    content += f"{str(type_def)[:500]}...(truncated if longer)\n"
        else:
            # String representation with truncation
            data_types_str = str(data_types)
            if len(data_types_str) > 2000:
                content += data_types_str[:2000] + "...(truncated)"
            else:
                content += data_types_str
    
    # Add common synonyms section to improve search
    content += "\n# COMMON TERMS\n"
    
    # Add service-specific common terms
    if service_name:
        service_lower = service_name.lower()
        if "filetransfer" in service_lower or "filemanagement" in service_lower:
            content += "This service handles file transfer, file sharing, and file management operations.\n"
        elif "diagnostic" in service_lower:
            content += "This service provides diagnostic and troubleshooting capabilities.\n"
        elif "update" in service_lower:
            content += "This service handles software updates, firmware updates, and over-the-air (OTA) updates.\n"
    
    return content


def create_semantic_chunks(content: str, metadata: Dict[str, Any], json_data: Dict[str, Any] = None) -> List[Document]:
    """
    Create semantic chunks from content while preserving relationships.
    
    This approach handles both generic text splitting and creating targeted
    JSON document chunks (if json_data is provided).
    
    Args:
        content: Text content to split
        metadata: Metadata to attach to each chunk
        json_data: Optional JSON data for specialized semantic chunking
        
    Returns:
        List of Document objects
    """
    print(f"DEBUG - create_semantic_chunks: content type: {type(content).__name__}, metadata type: {type(metadata).__name__}")
    
    # Ensure content is a string
    if not isinstance(content, str):
        print(f"DEBUG - create_semantic_chunks: WARNING - content is not a string! Converting to string.")
        try:
            content = str(content)
        except Exception as e:
            print(f"DEBUG - create_semantic_chunks: ERROR converting content to string: {e}")
            content = "Error: Invalid content type"
    
    # Ensure metadata is a dictionary
    if not isinstance(metadata, dict):
        print(f"DEBUG - create_semantic_chunks: WARNING - metadata is not a dict! It's: {metadata}")
        # Ensure metadata is a dict to avoid errors
        metadata = {"invalid_metadata": str(metadata)}
    
    # If json_data is provided, use specialized JSON semantic chunking
    if json_data:
        documents = []
        
        # Split the formatted content based on section headers
        sections = re.split(r'\n# ', content)
        
        # The first section is the summary, without the '# ' prefix
        summary_section = sections[0]
        remaining_sections = ["# " + section for section in sections[1:]]
        
        # Always include the summary section in each chunk for context
        base_content = summary_section
        
        # Create a document for basic information (summary + basic info)
        basic_info_pattern = r'# BASIC INFORMATION.*?(?=\n# |$)'
        basic_info_match = re.search(basic_info_pattern, content, re.DOTALL)
        
        if basic_info_match:
            basic_info = basic_info_match.group(0)
            basic_info_doc = Document(
                page_content=base_content + "\n" + basic_info,
                metadata={**metadata, "content_section": "basic_info"}
            )
            documents.append(basic_info_doc)
        
        # Create a document for service details
        service_details_pattern = r'# SERVICE DETAILS.*?(?=\n# |$)'
        service_match = re.search(service_details_pattern, content, re.DOTALL)
        
        if service_match:
            service_details = service_match.group(0)
            service_doc = Document(
                page_content=base_content + "\n" + service_details,
                metadata={**metadata, "content_section": "service_details"}
            )
            documents.append(service_doc)
        
        # Create separate documents for each method to improve retrieval precision
        service = json_data.get('Service', {})
        methods = service.get('Methods', [])
        
        if methods:
            for method in methods:
                method_name = safe_get(method, 'MethodName', 'unnamed')
                method_id = safe_get(method, 'MethodId')
                
                # Create method-specific content
                method_content = f"{base_content}\n\n# METHOD DETAILS\n"
                method_content += f"Method Name: {method_name}\n"
                method_content += f"Method ID: {method_id}\n"
                method_content += f"Request Message: {safe_get(method, 'RequestMessage')}\n"
                method_content += f"Response Message: {safe_get(method, 'ResponseMessage')}\n"
                
                # Add any common terms for searchability
                method_content += "\n# COMMON TERMS\n"
                method_content += f"This document describes the {method_name} method of the {metadata.get('service_name')} service.\n"
                
                # Create method-specific metadata
                method_metadata = {
                    **metadata,
                    "content_section": "method_details",
                    "method_name": method_name,
                    "method_id": str(method_id)
                }
                
                method_doc = Document(
                    page_content=method_content,
                    metadata=method_metadata
                )
                documents.append(method_doc)
        
        # Create a document for events if they exist
        events_pattern = r'## EVENTS.*?(?=\n# |$)'
        events_match = re.search(events_pattern, content, re.DOTALL)
        
        if events_match:
            events_content = events_match.group(0)
            events_doc = Document(
                page_content=base_content + "\n" + events_content,
                metadata={**metadata, "content_section": "events"}
            )
            documents.append(events_doc)
        
        # Create a document for data types if they exist
        data_types_pattern = r'# DATA TYPES.*?(?=\n# |$)'
        data_types_match = re.search(data_types_pattern, content, re.DOTALL)
        
        if data_types_match:
            data_types_content = data_types_match.group(0)
            data_types_doc = Document(
                page_content=base_content + "\n" + data_types_content,
                metadata={**metadata, "content_section": "data_types"}
            )
            documents.append(data_types_doc)
        
        # If no sections were found or no documents created, fallback to the full content
        if not documents:
            full_doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(full_doc)
        
        return documents
    
    # For generic text content without JSON data, use RecursiveCharacterTextSplitter
    else:
        # Create text splitter with reasonable defaults for semantic chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,           # Target chunk size
            chunk_overlap=200,         # Overlap between chunks to maintain context
            length_function=len,       # Function to measure chunk size
            separators=["\n\n", "\n", " ", ""]  # Separators in order of preference
        )
        
        # Split text into chunks
        texts = text_splitter.split_text(content)
        
        # Create documents
        documents = []
        for i, text in enumerate(texts):
            # Create a copy of metadata for each chunk and add chunk info
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk"] = i + 1
            chunk_metadata["total_chunks"] = len(texts)
            
            # Create document
            doc = Document(
                page_content=text,
                metadata=chunk_metadata
            )
            documents.append(doc)
        
        return documents
