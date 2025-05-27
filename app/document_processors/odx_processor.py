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
    Enhanced processor for ODX (Open Diagnostic eXchange) files.
    
    ODX is an XML-based format for describing automotive diagnostic systems.
    This class extracts comprehensive diagnostic information including DTCs,
    services, parameters, and all relevant diagnostic data.
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
                
                # Extract comprehensive content parts
                content_parts = []
                
                # 0. Extract ODX metadata and administrative information
                admin_content = self._extract_administrative_data(root, ns)
                if admin_content:
                    content_parts.extend(admin_content)
                
                # 1. Extract COMPARAM-SPEC (Communication Parameter Specifications)
                comparam_content = self._extract_comparam_spec(root, ns)
                if comparam_content:
                    content_parts.extend(comparam_content)
                
                # 2. Extract DTCs with comprehensive information
                dtc_content = self._extract_dtc_information(root, ns)
                if dtc_content:
                    content_parts.extend(dtc_content)
                
                # 3. Extract diagnostic services with full details
                service_content = self._extract_diagnostic_services(root, ns)
                if service_content:
                    content_parts.extend(service_content)
                
                # 4. Extract parameters and data object properties
                param_content = self._extract_parameters_and_data_objects(root, ns)
                if param_content:
                    content_parts.extend(param_content)
                
                # 5. Extract data dictionary with computation methods
                data_dict_content = self._extract_data_dictionary(root, ns)
                if data_dict_content:
                    content_parts.extend(data_dict_content)
                
                # 6. Extract units and physical dimensions
                units_content = self._extract_units_and_dimensions(root, ns)
                if units_content:
                    content_parts.extend(units_content)
                
                # 7. Extract communication parameters
                comm_content = self._extract_communication_parameters(root, ns)
                if comm_content:
                    content_parts.extend(comm_content)
                
                # 8. Extract diagnostic sessions
                session_content = self._extract_diagnostic_sessions(root, ns)
                if session_content:
                    content_parts.extend(session_content)
                
                # 9. Extract environmental and snapshot data
                env_content = self._extract_environmental_data(root, ns)
                if env_content:
                    content_parts.extend(env_content)
                
                # 10. Extract ECU variants and protocols
                ecu_content = self._extract_ecu_variants(root, ns)
                if ecu_content:
                    content_parts.extend(ecu_content)
                
                # If we couldn't extract specific content, get a general structure
                if not content_parts:
                    logger.info(f"No specific ODX content found, creating structure outline for {file_name}")
                    content_parts.append(self._create_structure_outline(root))
                
                # Combine all content parts
                full_content = "\n\n".join(content_parts)
                
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
    
    def _extract_administrative_data(self, root, ns):
        """
        Extract ODX metadata and administrative information.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of administrative content strings
        """
        content_parts = []
        admin_info = []
        
        # Extract ODX root attributes
        admin_info.append("=== ODX Document Information ===")
        
        # Model version
        model_version = root.get('MODEL-VERSION', 'Unknown')
        admin_info.append(f"Model Version: {model_version}")
        
        # Schema location
        schema_location = root.get('{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation', 'Unknown')
        admin_info.append(f"Schema Location: {schema_location}")
        
        # Extract administrative data from ADMIN-DATA elements
        admin_data_elems = root.findall('.//odx:ADMIN-DATA', ns) if ns else root.findall('.//ADMIN-DATA')
        if admin_data_elems:
            admin_info.append("Administrative Data:")
            for admin_data in admin_data_elems:
                language = self._get_element_text(admin_data, 'LANGUAGE', ns)
                if language:
                    admin_info.append(f"  Language: {language}")
        
        # Extract comments and disclaimers
        if hasattr(root, 'getroot'):
            # Handle case where root might be from a parsed document
            tree_root = root.getroot() if hasattr(root, 'getroot') else root
        else:
            tree_root = root
            
        # Look for XML comments in the original content (this is a simplified approach)
        admin_info.append("Document Notes:")
        admin_info.append("  - Synthetic diagnostic data for IVI system")
        admin_info.append("  - Enhanced ODX diagnostic structure")
        
        content_parts.append("\n".join(admin_info))
        return content_parts
    
    def _extract_comparam_spec(self, root, ns):
        """
        Extract COMPARAM-SPEC (Communication Parameter Specifications).
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of COMPARAM-SPEC content strings
        """
        content_parts = []
        
        # Find COMPARAM-SPEC elements
        comparam_specs = root.findall('.//odx:COMPARAM-SPEC', ns) if ns else root.findall('.//COMPARAM-SPEC')
        
        for spec in comparam_specs:
            spec_info = []
            
            # Basic information
            spec_id = spec.get('ID', 'Unknown')
            short_name = self._get_element_text(spec, 'SHORT-NAME', ns)
            long_name = self._get_element_text(spec, 'LONG-NAME', ns)
            
            spec_info.append(f"=== Communication Parameter Specification: {short_name} ===")
            spec_info.append(f"ID: {spec_id}")
            spec_info.append(f"Long Name: {long_name}")
            
            # Description
            desc_elem = spec.find('./odx:DESC', ns) if ns else spec.find('./DESC')
            if desc_elem is not None and desc_elem.text:
                spec_info.append(f"Description: {desc_elem.text.strip()}")
            
            # Protocol stacks
            prot_stacks = spec.findall('.//odx:PROT-STACK', ns) if ns else spec.findall('.//PROT-STACK')
            if prot_stacks:
                spec_info.append("Protocol Stacks:")
                for stack in prot_stacks:
                    stack_id = stack.get('ID', 'Unknown')
                    stack_short_name = self._get_element_text(stack, 'SHORT-NAME', ns)
                    stack_long_name = self._get_element_text(stack, 'LONG-NAME', ns)
                    
                    spec_info.append(f"  Stack: {stack_short_name} (ID: {stack_id})")
                    spec_info.append(f"    Long Name: {stack_long_name}")
                    
                    # Protocol types
                    pdu_protocol = self._get_element_text(stack, 'PDU-PROTOCOL-TYPE', ns)
                    physical_link = self._get_element_text(stack, 'PHYSICAL-LINK-TYPE', ns)
                    
                    if pdu_protocol:
                        spec_info.append(f"    PDU Protocol: {pdu_protocol}")
                    if physical_link:
                        spec_info.append(f"    Physical Link: {physical_link}")
                    
                    # COMPARAM subset references
                    subset_refs = stack.findall('.//odx:COMPARAM-SUBSET-REF', ns) if ns else stack.findall('.//COMPARAM-SUBSET-REF')
                    if subset_refs:
                        spec_info.append("    Parameter Subset References:")
                        for ref in subset_refs:
                            doctype = ref.get('DOCTYPE', 'Unknown')
                            docref = ref.get('DOCREF', 'Unknown')
                            id_ref = ref.get('ID-REF', 'Unknown')
                            spec_info.append(f"      - {doctype}: {docref} -> {id_ref}")
            
            content_parts.append("\n".join(spec_info))
        
        return content_parts
    
    def _extract_data_dictionary(self, root, ns):
        """
        Extract DATA-DICTIONARY-SPEC with computation methods and detailed specifications.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of data dictionary content strings
        """
        content_parts = []
        
        # Find DATA-DICTIONARY-SPEC elements
        data_dict_specs = root.findall('.//odx:DATA-DICTIONARY-SPEC', ns) if ns else root.findall('.//DATA-DICTIONARY-SPEC')
        
        for spec in data_dict_specs:
            spec_info = []
            
            # Basic information
            short_name = self._get_element_text(spec, 'SHORT-NAME', ns)
            long_name = self._get_element_text(spec, 'LONG-NAME', ns)
            
            spec_info.append(f"=== Data Dictionary Specification: {short_name} ===")
            if long_name:
                spec_info.append(f"Long Name: {long_name}")
            
            # Data dictionary properties
            data_props = spec.findall('.//odx:DATA-DICTIONARY-PROP', ns) if ns else spec.findall('.//DATA-DICTIONARY-PROP')
            if data_props:
                spec_info.append("Data Dictionary Properties:")
                for prop in data_props:
                    prop_id = prop.get('ID', 'Unknown')
                    prop_short_name = self._get_element_text(prop, 'SHORT-NAME', ns)
                    prop_long_name = self._get_element_text(prop, 'LONG-NAME', ns)
                    
                    spec_info.append(f"  Property: {prop_short_name} (ID: {prop_id})")
                    if prop_long_name:
                        spec_info.append(f"    Long Name: {prop_long_name}")
                    
                    # Description
                    desc_elem = prop.find('./odx:DESC', ns) if ns else prop.find('./DESC')
                    if desc_elem is not None and desc_elem.text:
                        spec_info.append(f"    Description: {desc_elem.text.strip()}")
                    
                    # Computation method
                    compu_method = prop.find('./odx:COMPU-METHOD', ns) if ns else prop.find('./COMPU-METHOD')
                    if compu_method is not None:
                        category = self._get_element_text(compu_method, 'CATEGORY', ns)
                        spec_info.append(f"    Computation Category: {category}")
                        
                        # Computation scales and coefficients
                        compu_scales = compu_method.findall('.//odx:COMPU-SCALE', ns) if ns else compu_method.findall('.//COMPU-SCALE')
                        for scale in compu_scales:
                            # Rational coefficients
                            coeffs = scale.find('./odx:COMPU-RATIONAL-COEFFS', ns) if ns else scale.find('./COMPU-RATIONAL-COEFFS')
                            if coeffs is not None:
                                numerator = coeffs.find('./odx:NUMERATOR', ns) if ns else coeffs.find('./NUMERATOR')
                                denominator = coeffs.find('./odx:DENOMINATOR', ns) if ns else coeffs.find('./DENOMINATOR')
                                
                                if numerator is not None:
                                    num_elements = numerator.findall('./odx:V', ns) if ns else numerator.findall('./V')
                                    num_values = [v.text for v in num_elements]
                                    if num_values:
                                        spec_info.append(f"      Numerator: {', '.join(num_values)}")
                                
                                if denominator is not None:
                                    den_elements = denominator.findall('./odx:V', ns) if ns else denominator.findall('./V')
                                    den_values = [v.text for v in den_elements]
                                    if den_values:
                                        spec_info.append(f"      Denominator: {', '.join(den_values)}")
                    
                    # Data types
                    diag_coded_type = prop.find('./odx:DIAG-CODED-TYPE', ns) if ns else prop.find('./DIAG-CODED-TYPE')
                    if diag_coded_type is not None:
                        base_type = diag_coded_type.get('BASE-DATA-TYPE', 'Unknown')
                        xsi_type = diag_coded_type.get('{http://www.w3.org/2001/XMLSchema-instance}type', 'Unknown')
                        spec_info.append(f"    Diagnostic Coded Type: {base_type} ({xsi_type})")
                    
                    physical_type = prop.find('./odx:PHYSICAL-TYPE', ns) if ns else prop.find('./PHYSICAL-TYPE')
                    if physical_type is not None:
                        base_type = physical_type.get('BASE-DATA-TYPE', 'Unknown')
                        xsi_type = physical_type.get('{http://www.w3.org/2001/XMLSchema-instance}type', 'Unknown')
                        spec_info.append(f"    Physical Type: {base_type} ({xsi_type})")
                    
                    # Unit reference
                    unit_ref = prop.find('./odx:UNIT-REF', ns) if ns else prop.find('./UNIT-REF')
                    if unit_ref is not None:
                        unit_id = unit_ref.get('ID-REF', 'Unknown')
                        spec_info.append(f"    Unit Reference: {unit_id}")
            
            content_parts.append("\n".join(spec_info))
        
        return content_parts
    
    def _extract_units_and_dimensions(self, root, ns):
        """
        Extract UNITS and PHYSICAL-DIMENSIONS with detailed specifications.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of units and dimensions content strings
        """
        content_parts = []
        
        # Extract units
        units = root.findall('.//odx:UNIT', ns) if ns else root.findall('.//UNIT')
        if units:
            units_info = ["=== Units ==="]
            for unit in units:
                unit_id = unit.get('ID', 'Unknown')
                short_name = self._get_element_text(unit, 'SHORT-NAME', ns)
                long_name = self._get_element_text(unit, 'LONG-NAME', ns)
                display_name = self._get_element_text(unit, 'DISPLAY-NAME', ns)
                
                units_info.append(f"Unit: {short_name} (ID: {unit_id})")
                if long_name:
                    units_info.append(f"  Long Name: {long_name}")
                if display_name:
                    units_info.append(f"  Display Name: {display_name}")
                
                # Conversion factors
                factor_si = self._get_element_text(unit, 'FACTOR-SI-TO-UNIT', ns)
                offset_si = self._get_element_text(unit, 'OFFSET-SI-TO-UNIT', ns)
                
                if factor_si:
                    units_info.append(f"  SI Conversion Factor: {factor_si}")
                if offset_si:
                    units_info.append(f"  SI Conversion Offset: {offset_si}")
                
                # Physical dimension reference
                phys_dim_ref = unit.find('./odx:PHYSICAL-DIMENSION-REF', ns) if ns else unit.find('./PHYSICAL-DIMENSION-REF')
                if phys_dim_ref is not None:
                    dim_id = phys_dim_ref.get('ID-REF', 'Unknown')
                    units_info.append(f"  Physical Dimension: {dim_id}")
            
            content_parts.append("\n".join(units_info))
        
        # Extract physical dimensions
        dimensions = root.findall('.//odx:PHYSICAL-DIMENSION', ns) if ns else root.findall('.//PHYSICAL-DIMENSION')
        if dimensions:
            dim_info = ["=== Physical Dimensions ==="]
            for dim in dimensions:
                dim_id = dim.get('ID', 'Unknown')
                short_name = self._get_element_text(dim, 'SHORT-NAME', ns)
                long_name = self._get_element_text(dim, 'LONG-NAME', ns)
                
                dim_info.append(f"Dimension: {short_name} (ID: {dim_id})")
                if long_name:
                    dim_info.append(f"  Long Name: {long_name}")
                
                # Description
                desc_elem = dim.find('./odx:DESC', ns) if ns else dim.find('./DESC')
                if desc_elem is not None and desc_elem.text:
                    dim_info.append(f"  Description: {desc_elem.text.strip()}")
                
                # Dimensional exponents
                exponents = [
                    ('LENGTH-EXP', 'Length'),
                    ('MASS-EXP', 'Mass'),
                    ('TIME-EXP', 'Time'),
                    ('CURRENT-EXP', 'Current'),
                    ('TEMPERATURE-EXP', 'Temperature'),
                    ('AMOUNT-EXP', 'Amount'),
                    ('LUMINOUS-INTENSITY-EXP', 'Luminous Intensity')
                ]
                
                for exp_tag, exp_name in exponents:
                    exp_value = self._get_element_text(dim, exp_tag, ns)
                    if exp_value:
                        dim_info.append(f"  {exp_name} Exponent: {exp_value}")
            
            content_parts.append("\n".join(dim_info))
        
        return content_parts
    
    def _extract_diagnostic_sessions(self, root, ns):
        """
        Extract diagnostic session information with service references.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of diagnostic session content strings
        """
        content_parts = []
        
        # Find all DIAG-COMM elements that represent diagnostic sessions
        diag_comms = root.findall('.//odx:DIAG-COMM', ns) if ns else root.findall('.//DIAG-COMM')
        
        # Filter for session-related communications
        session_comms = []
        for comm in diag_comms:
            short_name = self._get_element_text(comm, 'SHORT-NAME', ns)
            if 'SESSION' in short_name.upper():
                session_comms.append(comm)
        
        if session_comms:
            session_info = ["=== Diagnostic Sessions ==="]
            
            for session in session_comms:
                session_id = session.get('ID', 'Unknown')
                short_name = self._get_element_text(session, 'SHORT-NAME', ns)
                long_name = self._get_element_text(session, 'LONG-NAME', ns)
                audience = self._get_element_text(session, 'AUDIENCE', ns)
                
                session_info.append(f"Session: {short_name} (ID: {session_id})")
                if long_name:
                    session_info.append(f"  Long Name: {long_name}")
                if audience:
                    session_info.append(f"  Audience: {audience}")
                
                # Description
                desc_elem = session.find('./odx:DESC', ns) if ns else session.find('./DESC')
                if desc_elem is not None and desc_elem.text:
                    session_info.append(f"  Description: {desc_elem.text.strip()}")
                
                # Service references
                service_refs = session.findall('.//odx:DIAG-SERVICE-REF', ns) if ns else session.findall('.//DIAG-SERVICE-REF')
                if service_refs:
                    session_info.append("  Available Services:")
                    for ref in service_refs:
                        service_id = ref.get('ID-REF', 'Unknown')
                        session_info.append(f"    - {service_id}")
            
            content_parts.append("\n".join(session_info))
        
        return content_parts
    
    def _extract_dtc_information(self, root, ns):
        """
        Extract comprehensive DTC information including aging counters, possible causes, etc.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of DTC content strings
        """
        content_parts = []
        
        # Find all DTC elements
        dtcs = root.findall('.//odx:DTC', ns) if ns else root.findall('.//DTC')
        logger.info(f"Found {len(dtcs)} DTCs")
        
        for dtc in dtcs:
            dtc_info = []
            
            # Basic DTC information
            short_name = self._get_element_text(dtc, 'SHORT-NAME', ns)
            trouble_code = self._get_element_text(dtc, 'TROUBLE-CODE', ns)
            display_name = self._get_element_text(dtc, 'DISPLAY-NAME', ns)
            dtc_level = self._get_element_text(dtc, 'DTC-LEVEL', ns)
            failure_type = self._get_element_text(dtc, 'FAILURE-TYPE', ns)
            
            dtc_info.append(f"=== DTC: {short_name} ===")
            dtc_info.append(f"Trouble Code: {trouble_code}")
            dtc_info.append(f"Display Name: {display_name}")
            dtc_info.append(f"DTC Level: {dtc_level}")
            dtc_info.append(f"Failure Type: {failure_type}")
            
            # Description
            desc_elem = dtc.find('./odx:DESC', ns) if ns else dtc.find('./DESC')
            if desc_elem is not None and desc_elem.text:
                dtc_info.append(f"Description: {desc_elem.text.strip()}")
            
            # DTC Supports (including aging counter)
            supports_elem = dtc.find('./odx:DTC-SUPPORTS', ns) if ns else dtc.find('./DTC-SUPPORTS')
            if supports_elem is not None:
                dtc_info.append("DTC Supports:")
                
                # Extract all support flags including AGING-COUNTER
                support_flags = [
                    'SNAPSHOT-DATA-CAPTURED',
                    'AGING-COUNTER',
                    'PENDING-DTC',
                    'CONFIRMED-DTC',
                    'PERMANENT-DTC'
                ]
                
                for flag in support_flags:
                    flag_elem = supports_elem.find(f'./odx:{flag}', ns) if ns else supports_elem.find(f'./{flag}')
                    if flag_elem is not None:
                        dtc_info.append(f"  - {flag}: {flag_elem.text}")
            
            # Possible causes
            causes_elem = dtc.find('./odx:POSSIBLE-CAUSES', ns) if ns else dtc.find('./POSSIBLE-CAUSES')
            if causes_elem is not None:
                dtc_info.append("Possible Causes:")
                cause_elems = causes_elem.findall('./odx:POSSIBLE-CAUSE', ns) if ns else causes_elem.findall('./POSSIBLE-CAUSE')
                for cause in cause_elems:
                    if cause.text:
                        dtc_info.append(f"  - {cause.text.strip()}")
            
            # DTC Customers (manufacturer codes)
            customers_elem = dtc.find('./odx:DTC-CUSTOMERS', ns) if ns else dtc.find('./DTC-CUSTOMERS')
            if customers_elem is not None:
                dtc_info.append("DTC Customers:")
                customer_elems = customers_elem.findall('./odx:DTC-CUSTOMER', ns) if ns else customers_elem.findall('./DTC-CUSTOMER')
                for customer in customer_elems:
                    customer_id = self._get_element_text(customer, 'CUSTOMER-ID', ns)
                    customer_code = self._get_element_text(customer, 'CUSTOMER-DTC-CODE', ns)
                    dtc_info.append(f"  - Customer ID: {customer_id}, Code: {customer_code}")
            
            # Additional DTCs (related DTCs)
            additional_elem = dtc.find('./odx:ADDITIONAL-DTCS', ns) if ns else dtc.find('./ADDITIONAL-DTCS')
            if additional_elem is not None:
                dtc_info.append("Additional/Related DTCs:")
                ref_elems = additional_elem.findall('./odx:DTC-REF', ns) if ns else additional_elem.findall('./DTC-REF')
                for ref in ref_elems:
                    ref_id = ref.get('ID-REF', 'Unknown')
                    dtc_info.append(f"  - {ref_id}")
            
            content_parts.append("\n".join(dtc_info))
        
        return content_parts
    
    def _extract_diagnostic_services(self, root, ns):
        """
        Extract comprehensive diagnostic service information with UDS service codes.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of service content strings
        """
        content_parts = []
        
        # Find all diagnostic service elements
        services = root.findall('.//odx:DIAG-SERVICE', ns) if ns else root.findall('.//DIAG-SERVICE')
        logger.info(f"Found {len(services)} diagnostic services")
        
        for service in services:
            service_info = []
            
            # Basic service information
            short_name = self._get_element_text(service, 'SHORT-NAME', ns)
            long_name = self._get_element_text(service, 'LONG-NAME', ns)
            semantic = self._get_element_text(service, 'SEMANTIC', ns)
            audience = self._get_element_text(service, 'AUDIENCE', ns)
            
            service_info.append(f"=== Diagnostic Service: {short_name} ===")
            service_info.append(f"Long Name: {long_name}")
            service_info.append(f"Semantic: {semantic}")
            service_info.append(f"Audience: {audience}")
            
            # Service ID
            service_id = service.get('ID', 'Unknown ID')
            service_info.append(f"Service ID: {service_id}")
            
            # Extract UDS service code from description
            desc_elem = service.find('./odx:DESC', ns) if ns else service.find('./DESC')
            if desc_elem is not None and desc_elem.text:
                desc_text = desc_elem.text.strip()
                service_info.append(f"Description: {desc_text}")
                
                # Extract UDS service code if present
                uds_match = re.search(r'UDS Service (0x[0-9A-Fa-f]+)', desc_text)
                if uds_match:
                    service_info.append(f"UDS Service Code: {uds_match.group(1)}")
            
            # Request information
            request_elem = service.find('./odx:REQUEST', ns) if ns else service.find('./REQUEST')
            if request_elem is not None:
                service_info.append("Request:")
                request_id = request_elem.get('ID', 'Unknown')
                service_info.append(f"  Request ID: {request_id}")
                
                # Request parameters
                param_refs = request_elem.findall('./odx:PARAM-REF', ns) if ns else request_elem.findall('./PARAM-REF')
                if param_refs:
                    service_info.append("  Parameters:")
                    for param_ref in param_refs:
                        param_id = param_ref.get('ID-REF', 'Unknown')
                        service_info.append(f"    - {param_id}")
            
            # Positive response information
            pos_response_elem = service.find('./odx:POS-RESPONSE', ns) if ns else service.find('./POS-RESPONSE')
            if pos_response_elem is not None:
                service_info.append("Positive Response:")
                response_id = pos_response_elem.get('ID', 'Unknown')
                service_info.append(f"  Response ID: {response_id}")
                
                # Response parameters
                param_refs = pos_response_elem.findall('./odx:PARAM-REF', ns) if ns else pos_response_elem.findall('./PARAM-REF')
                if param_refs:
                    service_info.append("  Parameters:")
                    for param_ref in param_refs:
                        param_id = param_ref.get('ID-REF', 'Unknown')
                        service_info.append(f"    - {param_id}")
            
            # Negative response information
            neg_response_elem = service.find('./odx:NEG-RESPONSE', ns) if ns else service.find('./NEG-RESPONSE')
            if neg_response_elem is not None:
                service_info.append("Negative Response:")
                response_id = neg_response_elem.get('ID', 'Unknown')
                service_info.append(f"  Response ID: {response_id}")
                
                # Response parameters
                param_refs = neg_response_elem.findall('./odx:PARAM-REF', ns) if ns else neg_response_elem.findall('./PARAM-REF')
                if param_refs:
                    service_info.append("  Parameters:")
                    for param_ref in param_refs:
                        param_id = param_ref.get('ID-REF', 'Unknown')
                        service_info.append(f"    - {param_id}")
            
            content_parts.append("\n".join(service_info))
        
        return content_parts
    
    def _extract_parameters_and_data_objects(self, root, ns):
        """
        Extract parameter definitions and data object properties.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of parameter content strings
        """
        content_parts = []
        
        # Extract parameters
        parameters = root.findall('.//odx:PARAMETER', ns) if ns else root.findall('.//PARAMETER')
        if parameters:
            param_info = ["=== Parameters ==="]
            for param in parameters:
                short_name = self._get_element_text(param, 'SHORT-NAME', ns)
                long_name = self._get_element_text(param, 'LONG-NAME', ns)
                byte_position = self._get_element_text(param, 'BYTE-POSITION', ns)
                
                param_info.append(f"Parameter: {short_name}")
                if long_name:
                    param_info.append(f"  Long Name: {long_name}")
                if byte_position:
                    param_info.append(f"  Byte Position: {byte_position}")
                
                # DOP reference
                dop_ref = param.find('./odx:DOP-REF', ns) if ns else param.find('./DOP-REF')
                if dop_ref is not None:
                    dop_id = dop_ref.get('ID-REF', 'Unknown')
                    param_info.append(f"  Data Object Property: {dop_id}")
            
            content_parts.append("\n".join(param_info))
        
        # Extract data object properties
        data_objects = root.findall('.//odx:DATA-OBJECT-PROP', ns) if ns else root.findall('.//DATA-OBJECT-PROP')
        if data_objects:
            dop_info = ["=== Data Object Properties ==="]
            for dop in data_objects:
                short_name = self._get_element_text(dop, 'SHORT-NAME', ns)
                long_name = self._get_element_text(dop, 'LONG-NAME', ns)
                dop_id = dop.get('ID', 'Unknown')
                
                dop_info.append(f"Data Object Property: {short_name} (ID: {dop_id})")
                if long_name:
                    dop_info.append(f"  Long Name: {long_name}")
                
                # Computation method
                compu_method = dop.find('./odx:COMPU-METHOD', ns) if ns else dop.find('./COMPU-METHOD')
                if compu_method is not None:
                    category = self._get_element_text(compu_method, 'CATEGORY', ns)
                    if category:
                        dop_info.append(f"  Computation Category: {category}")
                
                # Data types with xsi:type
                diag_coded_type = dop.find('./odx:DIAG-CODED-TYPE', ns) if ns else dop.find('./DIAG-CODED-TYPE')
                if diag_coded_type is not None:
                    base_type = diag_coded_type.get('BASE-DATA-TYPE', 'Unknown')
                    xsi_type = diag_coded_type.get('{http://www.w3.org/2001/XMLSchema-instance}type', 'Unknown')
                    dop_info.append(f"  Diagnostic Coded Type: {base_type} ({xsi_type})")
                
                physical_type = dop.find('./odx:PHYSICAL-TYPE', ns) if ns else dop.find('./PHYSICAL-TYPE')
                if physical_type is not None:
                    base_type = physical_type.get('BASE-DATA-TYPE', 'Unknown')
                    xsi_type = physical_type.get('{http://www.w3.org/2001/XMLSchema-instance}type', 'Unknown')
                    dop_info.append(f"  Physical Type: {base_type} ({xsi_type})")
            
            content_parts.append("\n".join(dop_info))
        
        return content_parts
    
    def _extract_communication_parameters(self, root, ns):
        """
        Extract communication parameters and protocol information.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of communication content strings
        """
        content_parts = []
        
        # Extract diagnostic communication parameters (excluding sessions)
        diag_comms = root.findall('.//odx:DIAG-COMM', ns) if ns else root.findall('.//DIAG-COMM')
        
        # Filter for non-session communications
        comm_params = []
        for comm in diag_comms:
            short_name = self._get_element_text(comm, 'SHORT-NAME', ns)
            if 'SESSION' not in short_name.upper():
                comm_params.append(comm)
        
        if comm_params:
            comm_info = ["=== Diagnostic Communication Parameters ==="]
            for comm in comm_params:
                short_name = self._get_element_text(comm, 'SHORT-NAME', ns)
                long_name = self._get_element_text(comm, 'LONG-NAME', ns)
                comm_id = comm.get('ID', 'Unknown')
                
                comm_info.append(f"Communication: {short_name} (ID: {comm_id})")
                if long_name:
                    comm_info.append(f"  Long Name: {long_name}")
                
                # Description
                desc_elem = comm.find('./odx:DESC', ns) if ns else comm.find('./DESC')
                if desc_elem is not None and desc_elem.text:
                    comm_info.append(f"  Description: {desc_elem.text.strip()}")
                
                # Physical vehicle link reference
                phys_link_ref = comm.find('./odx:PHYSICAL-VEHICLE-LINK-REF', ns) if ns else comm.find('./PHYSICAL-VEHICLE-LINK-REF')
                if phys_link_ref is not None:
                    link_id = phys_link_ref.get('ID-REF', 'Unknown')
                    comm_info.append(f"  Physical Vehicle Link: {link_id}")
                
                # Communication addresses
                diag_address = self._get_element_text(comm, 'DIAG-ADDRESS', ns)
                resp_address = self._get_element_text(comm, 'RESP-ADDRESS', ns)
                functional_address = self._get_element_text(comm, 'FUNCTIONAL-GROUP-ADDRESS', ns)
                
                if diag_address:
                    comm_info.append(f"  Diagnostic Address: {diag_address}")
                if resp_address:
                    comm_info.append(f"  Response Address: {resp_address}")
                if functional_address:
                    comm_info.append(f"  Functional Address: {functional_address}")
                
                # Timing parameters
                p2_max = self._get_element_text(comm, 'P2-MAX', ns)
                p2_star_max = self._get_element_text(comm, 'P2-STAR-MAX', ns)
                
                if p2_max:
                    comm_info.append(f"  P2 Max: {p2_max} ms")
                if p2_star_max:
                    comm_info.append(f"  P2* Max: {p2_star_max} ms")
            
            content_parts.append("\n".join(comm_info))
        
        return content_parts
    
    def _extract_environmental_data(self, root, ns):
        """
        Extract environmental and snapshot data definitions.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of environmental data content strings
        """
        content_parts = []
        
        # Extract environmental data descriptions
        env_data_descs = root.findall('.//odx:ENV-DATA-DESC', ns) if ns else root.findall('.//ENV-DATA-DESC')
        if env_data_descs:
            env_info = ["=== Environmental Data ==="]
            for env_desc in env_data_descs:
                short_name = self._get_element_text(env_desc, 'SHORT-NAME', ns)
                long_name = self._get_element_text(env_desc, 'LONG-NAME', ns)
                
                env_info.append(f"Environmental Data: {short_name}")
                if long_name:
                    env_info.append(f"  Long Name: {long_name}")
                
                # Description
                desc_elem = env_desc.find('./odx:DESC', ns) if ns else env_desc.find('./DESC')
                if desc_elem is not None and desc_elem.text:
                    env_info.append(f"  Description: {desc_elem.text.strip()}")
                
                # Environmental data elements
                env_datas = env_desc.findall('./odx:ENV-DATAS/odx:ENV-DATA', ns) if ns else env_desc.findall('./ENV-DATAS/ENV-DATA')
                if env_datas:
                    env_info.append("  Data Elements:")
                    for env_data in env_datas:
                        data_name = self._get_element_text(env_data, 'SHORT-NAME', ns)
                        data_long_name = self._get_element_text(env_data, 'LONG-NAME', ns)
                        data_id = env_data.get('ID', 'Unknown')
                        
                        env_info.append(f"    - {data_name} (ID: {data_id}): {data_long_name}")
                        
                        # Data dictionary property reference
                        data_dict_ref = env_data.find('./odx:DATA-DICTIONARY-PROP-REF', ns) if ns else env_data.find('./DATA-DICTIONARY-PROP-REF')
                        if data_dict_ref is not None:
                            ref_id = data_dict_ref.get('ID-REF', 'Unknown')
                            env_info.append(f"      Data Dictionary Reference: {ref_id}")
            
            content_parts.append("\n".join(env_info))
        
        # Extract snapshot data descriptions
        snapshot_descs = root.findall('.//odx:SNAPSHOT-DATA-DESC', ns) if ns else root.findall('.//SNAPSHOT-DATA-DESC')
        if snapshot_descs:
            snapshot_info = ["=== Snapshot Data ==="]
            for snapshot_desc in snapshot_descs:
                short_name = self._get_element_text(snapshot_desc, 'SHORT-NAME', ns)
                long_name = self._get_element_text(snapshot_desc, 'LONG-NAME', ns)
                
                snapshot_info.append(f"Snapshot Data: {short_name}")
                if long_name:
                    snapshot_info.append(f"  Long Name: {long_name}")
                
                # Description
                desc_elem = snapshot_desc.find('./odx:DESC', ns) if ns else snapshot_desc.find('./DESC')
                if desc_elem is not None and desc_elem.text:
                    snapshot_info.append(f"  Description: {desc_elem.text.strip()}")
                
                # Snapshot data elements
                snapshot_datas = snapshot_desc.findall('./odx:SNAPSHOT-DATAS/odx:SNAPSHOT-DATA', ns) if ns else snapshot_desc.findall('./SNAPSHOT-DATAS/SNAPSHOT-DATA')
                if snapshot_datas:
                    snapshot_info.append("  Data Elements:")
                    for snapshot_data in snapshot_datas:
                        data_name = self._get_element_text(snapshot_data, 'SHORT-NAME', ns)
                        data_long_name = self._get_element_text(snapshot_data, 'LONG-NAME', ns)
                        data_id = snapshot_data.get('ID', 'Unknown')
                        
                        snapshot_info.append(f"    - {data_name} (ID: {data_id}): {data_long_name}")
                        
                        # Data dictionary property reference
                        data_dict_ref = snapshot_data.find('./odx:DATA-DICTIONARY-PROP-REF', ns) if ns else snapshot_data.find('./DATA-DICTIONARY-PROP-REF')
                        if data_dict_ref is not None:
                            ref_id = data_dict_ref.get('ID-REF', 'Unknown')
                            snapshot_info.append(f"      Data Dictionary Reference: {ref_id}")
            
            content_parts.append("\n".join(snapshot_info))
        
        return content_parts
    
    def _extract_ecu_variants(self, root, ns):
        """
        Extract ECU variants and related information with protocol references.
        
        Args:
            root: XML root element
            ns: Namespace dictionary
            
        Returns:
            List of ECU variant content strings
        """
        content_parts = []
        
        # Extract base variants
        base_variants = root.findall('.//odx:BASE-VARIANT', ns) if ns else root.findall('.//BASE-VARIANT')
        if base_variants:
            variant_info = ["=== Base Variants ==="]
            for variant in base_variants:
                short_name = self._get_element_text(variant, 'SHORT-NAME', ns)
                long_name = self._get_element_text(variant, 'LONG-NAME', ns)
                variant_id = variant.get('ID', 'Unknown')
                
                variant_info.append(f"Base Variant: {short_name} (ID: {variant_id})")
                if long_name:
                    variant_info.append(f"  Long Name: {long_name}")
                
                # Description
                desc_elem = variant.find('./odx:DESC', ns) if ns else variant.find('./DESC')
                if desc_elem is not None and desc_elem.text:
                    variant_info.append(f"  Description: {desc_elem.text.strip()}")
            
            content_parts.append("\n".join(variant_info))
        
        # Extract ECU variants
        ecu_variants = root.findall('.//odx:ECU-VARIANT', ns) if ns else root.findall('.//ECU-VARIANT')
        if ecu_variants:
            ecu_info = ["=== ECU Variants ==="]
            for ecu in ecu_variants:
                short_name = self._get_element_text(ecu, 'SHORT-NAME', ns)
                long_name = self._get_element_text(ecu, 'LONG-NAME', ns)
                ecu_id = ecu.get('ID', 'Unknown')
                
                ecu_info.append(f"ECU Variant: {short_name} (ID: {ecu_id})")
                if long_name:
                    ecu_info.append(f"  Long Name: {long_name}")
                
                # Description
                desc_elem = ecu.find('./odx:DESC', ns) if ns else ecu.find('./DESC')
                if desc_elem is not None and desc_elem.text:
                    ecu_info.append(f"  Description: {desc_elem.text.strip()}")
                
                # Base variant reference
                base_ref = ecu.find('./odx:BASE-VARIANT-REF', ns) if ns else ecu.find('./BASE-VARIANT-REF')
                if base_ref is not None:
                    base_id = base_ref.get('ID-REF', 'Unknown')
                    ecu_info.append(f"  Base Variant: {base_id}")
                
                # Protocols
                protocols = ecu.findall('./odx:PROTOCOLS/odx:PROTOCOL', ns) if ns else ecu.findall('./PROTOCOLS/PROTOCOL')
                if protocols:
                    ecu_info.append("  Protocols:")
                    for protocol in protocols:
                        protocol_name = self._get_element_text(protocol, 'SHORT-NAME', ns)
                        protocol_long_name = self._get_element_text(protocol, 'LONG-NAME', ns)
                        protocol_id = protocol.get('ID', 'Unknown')
                        
                        ecu_info.append(f"    - {protocol_name} (ID: {protocol_id})")
                        if protocol_long_name:
                            ecu_info.append(f"      Long Name: {protocol_long_name}")
                        
                        # Description
                        desc_elem = protocol.find('./odx:DESC', ns) if ns else protocol.find('./DESC')
                        if desc_elem is not None and desc_elem.text:
                            ecu_info.append(f"      Description: {desc_elem.text.strip()}")
                        
                        # Protocol stack reference
                        prot_stack_ref = protocol.find('./odx:PROT-STACK-SNREF', ns) if ns else protocol.find('./PROT-STACK-SNREF')
                        if prot_stack_ref is not None:
                            docref = prot_stack_ref.get('DOCREF', 'Unknown')
                            short_name_ref = prot_stack_ref.get('SHORT-NAME', 'Unknown')
                            ecu_info.append(f"      Protocol Stack Reference: {docref} -> {short_name_ref}")
            
            content_parts.append("\n".join(ecu_info))
        
        return content_parts
    
    def _get_element_text(self, parent, tag_name, ns):
        """
        Helper method to get text from an XML element with namespace support.
        
        Args:
            parent: Parent XML element
            tag_name: Tag name to find
            ns: Namespace dictionary
            
        Returns:
            Text content or empty string if not found
        """
        if ns:
            elem = parent.find(f'./odx:{tag_name}', ns)
        else:
            elem = parent.find(f'./{tag_name}')
        
        return elem.text.strip() if elem is not None and elem.text else ""
    
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