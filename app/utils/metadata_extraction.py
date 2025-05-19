import re
import json


def safe_get(data, key, default=""):
    """Safely get a value from a dictionary or return default if not found."""
    if isinstance(data, dict) and key in data:
        value = data.get(key)
        return default if value is None else value
    return default


def extract_json_metadata(json_data):
    """Extract key fields as metadata from JSON content for more accurate retrieval."""
    # Basic metadata extraction
    metadata = {
        "data_object_name": safe_get(json_data, "DataObjectName"),
        "object_type": safe_get(json_data, "ObjectType"),
        "source_device": safe_get(json_data, "SourceDevice"),
        "destination_device": safe_get(json_data, "DestinationDevice"),
        "source_application": safe_get(json_data, "SourceAplication"),  # Note the typo in original JSON
        "destination_application": safe_get(json_data, "DestinationApplication"),
        "transport_protocol": safe_get(json_data, "TransportProtocol"),
    }
    
    # Create normalized and alias fields for better matching with natural language queries
    data_object_name = safe_get(json_data, "DataObjectName")
    if data_object_name:
        # Normalize the name (lowercase, remove spaces)
        normalized_name = data_object_name.lower().replace(" ", "")
        metadata["normalized_name"] = normalized_name
        
        # Extract potential keywords from camelCase or PascalCase names
        # For example: "FileTransferAgent" -> ["file", "transfer", "agent"]
        keywords = re.findall(r'[A-Z][a-z]*', data_object_name)
        if keywords:
            metadata["name_keywords"] = " ".join([k.lower() for k in keywords])
    
    # Add service info to metadata if available
    service = json_data.get("Service", {})
    if service:
        service_name = safe_get(service, "Name")
        metadata.update({
            "service_name": service_name,
            "service_id": safe_get(service, "ServiceID"),
            "instance_id": safe_get(service, "InstanceId"),
            "service_role": safe_get(service, "Role")
        })
        
        # Add normalized service name for better matching
        if service_name:
            normalized_service = service_name.lower().replace(" ", "")
            metadata["normalized_service_name"] = normalized_service
            
            # Extract keywords from service name (similar to data object name)
            service_keywords = re.findall(r'[A-Z][a-z]*', service_name)
            if service_keywords:
                metadata["service_keywords"] = " ".join([k.lower() for k in service_keywords])
        
        # Extract common aliases for well-known services
        # This helps bridge the gap between technical names and natural language
        aliases = []
        service_name_lower = service_name.lower() if service_name else ""
        
        # Map common service patterns to their colloquial names
        if "filetransfer" in service_name_lower or "filemanagement" in service_name_lower:
            aliases.extend(["file transfer", "file sharing", "file manager"])
        
        if "diagnostic" in service_name_lower:
            aliases.extend(["diagnostics", "troubleshooting", "fault detection"])
            
        if "update" in service_name_lower or "software" in service_name_lower:
            aliases.extend(["software update", "firmware update", "OTA"])
            
        if aliases:
            metadata["service_aliases"] = " ".join(aliases)
        
        # Extract method IDs and names for search
        methods = service.get("Methods", [])
        if methods:
            method_ids = [str(safe_get(method, "MethodId")) for method in methods]
            metadata["method_ids"] = ",".join(method_ids)
            
            method_names = [safe_get(method, "MethodName") for method in methods]
            metadata["method_names"] = ",".join(method_names)
            
            # Also create a space-separated string of method names for better text matching
            metadata["method_names_text"] = " ".join(method_names)
            
            # Store request/response message information
            method_request_msgs = {}
            for method in methods:
                method_name = safe_get(method, "MethodName")
                request_msg = safe_get(method, "RequestMessage")
                if method_name and request_msg:
                    method_request_msgs[method_name] = request_msg
            
            if method_request_msgs:
                metadata["method_request_messages"] = json.dumps(method_request_msgs)
            
            # Extract keywords from method names for better matching
            all_method_keywords = []
            for method_name in method_names:
                if method_name:
                    keywords = re.findall(r'[A-Z][a-z]*', method_name)
                    all_method_keywords.extend([k.lower() for k in keywords])
            if all_method_keywords:
                metadata["method_keywords"] = " ".join(all_method_keywords)
        
        # Extract event information
        event_groups = service.get('EventGroups', [])
        if event_groups:
            all_events = []
            for group in event_groups:
                for event in group.get('Events', []):
                    event_name = safe_get(event, 'EventMessage')
                    if event_name:
                        all_events.append(event_name)
            if all_events:
                metadata["event_names"] = " ".join(all_events)
    
    # Filter out None values
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    return metadata
