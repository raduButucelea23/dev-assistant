import re


def preprocess_query(query):
    """Enhance the user query to improve retrieval results.
    
    This function processes natural language queries to make them more compatible
    with technical document retrieval by:
    1. Identifying technical terms and potential service names
    2. Expanding common abbreviations 
    3. Adding relevant technical terms for known concepts
    """
    # Lowercase the query for consistent matching
    processed_query = query.lower()
    
    # Create a list to store expanded terms
    expanded_terms = []
    
    # Expand common abbreviations and add technical terms
    if "file transfer" in processed_query or "file sharing" in processed_query or "file management" in processed_query:
        expanded_terms.extend(["FileTransferAgent", "FileTransferService", "FileManagement"])
    
    if "diagnostic" in processed_query or "diagnostics" in processed_query or "troubleshoot" in processed_query:
        expanded_terms.extend(["DiagnosticService", "DiagnosticSession", "DiagnosticTool"])
    
    if "update" in processed_query or "ota" in processed_query or "over the air" in processed_query:
        expanded_terms.extend(["SoftwareUpdate", "FirmwareUpdate", "UpdateManager"])
    
    # Extract potential technical terms using camelCase/PascalCase patterns
    camel_case_pattern = r'\b[a-z]+([A-Z][a-z]+)+'  # matches camelCase
    pascal_case_pattern = r'\b([A-Z][a-z]+)+'       # matches PascalCase
    
    camel_case_matches = re.findall(camel_case_pattern, query)
    pascal_case_matches = re.findall(pascal_case_pattern, query)
    
    # Add extracted technical terms if they exist
    if camel_case_matches or pascal_case_matches:
        technical_terms = []
        for match in camel_case_matches + pascal_case_matches:
            if isinstance(match, str) and len(match) > 2:  # Avoid single letter matches
                technical_terms.append(match)
        
        if technical_terms:
            expanded_terms.extend(technical_terms)
    
    # Combine the original query with expanded terms
    if expanded_terms:
        enhanced_query = f"{processed_query} {' '.join(expanded_terms)}"
        return enhanced_query
    
    return processed_query


def extract_technical_terms(query):
    """Extract potential technical terms from a user query.
    
    This function identifies technical identifiers, camelCase/PascalCase terms,
    and other potential service or object names from the query.
    """
    # Extract technical identifiers using regex patterns
    technical_terms = []
    
    # Match CamelCase and PascalCase patterns
    camel_case_pattern = r'\b[a-z]+([A-Z][a-z]+)+'  # matches camelCase
    pascal_case_pattern = r'\b([A-Z][a-z]+){2,}'    # matches PascalCase with at least 2 components
    
    # Also match potential service names like "X Service" or "X Manager"
    service_pattern = r'\b[A-Z][a-zA-Z]*\s+(Service|Manager|Agent|API)\b'
    
    # Find all matches
    camel_case_matches = re.findall(camel_case_pattern, query)
    pascal_case_matches = re.findall(pascal_case_pattern, query)
    service_matches = re.findall(service_pattern, query)
    
    # Extract full matches for camelCase and PascalCase
    # For camelCase, we need to find the full match, not just the capturing group
    for match in re.finditer(camel_case_pattern, query):
        if match.group(0) and len(match.group(0)) > 3:  # Ensure it's not too short
            technical_terms.append(match.group(0))
    
    # For PascalCase, we need to find the full match
    for match in re.finditer(pascal_case_pattern, query):
        if match.group(0) and len(match.group(0)) > 3:  # Ensure it's not too short
            technical_terms.append(match.group(0))
    
    # For service names, extract the full match
    for match in re.finditer(service_pattern, query):
        if match.group(0):
            technical_terms.append(match.group(0))
    
    # Also extract quoted terms, which might be exact identifiers
    quoted_pattern = r'"([^"]+)"|\'([^\']+)\''
    for match in re.finditer(quoted_pattern, query):
        quoted_term = match.group(1) or match.group(2)
        if quoted_term:
            technical_terms.append(quoted_term)
    
    return technical_terms
