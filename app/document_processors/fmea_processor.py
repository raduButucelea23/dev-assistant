import os
import json
from typing import List, Dict, Any, Optional
from langchain_core.documents.base import Document
from pathlib import Path

# Try relative imports first
try:
    from .base_processor import BaseProcessor
    from .json_processor import JSONProcessor
except ImportError:
    # Fall back to absolute imports if relative imports fail
    from app.document_processors.base_processor import BaseProcessor
    from app.document_processors.json_processor import JSONProcessor


class FMEAProcessor(JSONProcessor):
    """Processor for FMEA (Failure Mode and Effects Analysis) JSON documents.
    
    Specialized processor that handles the unique structure of FMEA documents,
    with optimized chunking strategies for improved retrieval in RAG applications.
    """
    
    def __init__(self, domain: str = "engineering"):
        """Initialize the FMEA processor with the engineering domain.
        
        Args:
            domain: The semantic domain for FMEA documents (default: "engineering")
        """
        super().__init__(domain)
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process an FMEA file and return a list of semantically chunked Document objects.
        
        Creates specialized chunks based on FMEA document sections to improve
        retrieval performance in RAG applications.
        
        Args:
            file_path: Path to the FMEA JSON file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        print(f"DEBUG - FMEAProcessor: Processing {filename}")
        
        try:
            # Load the JSON file
            with open(file_path, 'r') as f:
                fmea_data = json.load(f)
            
            # Extract FMEA metadata
            metadata = self.extract_fmea_metadata(fmea_data)
            
            # Add source information to metadata
            metadata["source"] = filename
            metadata["source_type"] = "fmea"
            metadata["domain"] = self.domain
            
            # Create FMEA-specific chunks
            documents = self.create_fmea_chunks(fmea_data, metadata)
            
            print(f"DEBUG - FMEAProcessor: Successfully created {len(documents)} chunks for {filename}")
            for i, doc in enumerate(documents):
                print(f"DEBUG - FMEAProcessor: Document {i} section: {doc.metadata.get('content_section', 'unknown')}")
                
            return documents
            
        except Exception as e:
            # Return a single document with error information
            error_msg = f"Error processing FMEA file: {str(e)}"
            print(f"DEBUG - FMEAProcessor: {error_msg}")
            error_doc = Document(
                page_content=error_msg,
                metadata={
                    "source": filename,
                    "source_type": "fmea",
                    "domain": self.domain,
                    "error": str(e)
                }
            )
            return [error_doc]
    
    def extract_fmea_metadata(self, fmea_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from FMEA document for improved retrieval.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            
        Returns:
            Dictionary of metadata extracted from the FMEA document
        """
        metadata = {}
        
        # Extract basic document metadata
        metadata["document_type"] = "FMEA"
        metadata["document_title"] = fmea_data.get("documentTitle", "")
        metadata["document_id"] = fmea_data.get("documentId", "")
        metadata["document_version"] = fmea_data.get("documentVersion", "")
        metadata["document_date"] = fmea_data.get("documentDate", "")
        
        # Extract FMEA type
        metadata["fmea_type"] = fmea_data.get("fmeaType", "")
        
        # Extract system/product information
        system_info = fmea_data.get("systemInformation", {})
        metadata["system_name"] = system_info.get("systemName", "")
        metadata["system_description"] = system_info.get("systemDescription", "")
        
        # Extract highest severity and RPN
        failure_modes = fmea_data.get("failureModes", [])
        highest_severity = 0
        highest_rpn = 0
        critical_count = 0
        mode_names = []
        
        for mode in failure_modes:
            severity = int(mode.get("severity", 0))
            rpn = int(mode.get("rpn", 0))
            mode_names.append(mode.get("failureModeName", ""))
            
            if severity > highest_severity:
                highest_severity = severity
            
            if rpn > highest_rpn:
                highest_rpn = rpn
                
            # Count critical failures (typically RPN > 100 or severity >= 9)
            if rpn > 100 or severity >= 9:
                critical_count += 1
        
        metadata["highest_severity"] = highest_severity
        metadata["highest_rpn"] = highest_rpn
        metadata["critical_failure_count"] = critical_count
        
        # Only add failure_modes if not empty
        if mode_names:
            metadata["failure_modes"] = "; ".join(mode_names)
        
        return metadata
    
    def create_fmea_chunks(self, fmea_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[Document]:
        """Create specialized semantic chunks from FMEA data.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of Document objects representing semantic chunks
        """
        documents = []
        print(f"DEBUG - FMEAProcessor: Starting to create chunks for {metadata.get('source', 'unknown')}")
        
        # Create document summary chunk
        summary_content = self.create_summary_content(fmea_data, metadata)
        summary_doc = Document(
            page_content=summary_content,
            metadata={**metadata, "content_section": "summary"}
        )
        documents.append(summary_doc)
        print(f"DEBUG - FMEAProcessor: Created summary chunk")
        
        # Create system information chunk
        system_content = self.create_system_info_content(fmea_data, metadata)
        if system_content:
            system_doc = Document(
                page_content=system_content,
                metadata={**metadata, "content_section": "system_information"}
            )
            documents.append(system_doc)
            print(f"DEBUG - FMEAProcessor: Created system info chunk")
        
        # Create individual failure mode chunks for better retrieval
        failure_docs = self.create_failure_mode_chunks(fmea_data, metadata)
        documents.extend(failure_docs)
        print(f"DEBUG - FMEAProcessor: Created {len(failure_docs)} failure mode chunks")
        
        # Create recommended actions chunk
        actions_content = self.create_recommended_actions_content(fmea_data, metadata)
        if actions_content:
            actions_doc = Document(
                page_content=actions_content,
                metadata={**metadata, "content_section": "recommended_actions"}
            )
            documents.append(actions_doc)
            print(f"DEBUG - FMEAProcessor: Created recommended actions chunk")
        
        # Create detection methods chunk
        detection_content = self.create_detection_methods_content(fmea_data, metadata)
        if detection_content:
            detection_doc = Document(
                page_content=detection_content,
                metadata={**metadata, "content_section": "detection_methods"}
            )
            documents.append(detection_doc)
            print(f"DEBUG - FMEAProcessor: Created detection methods chunk")
        
        # Create common terms/key terms chunk for improved search
        terms_content = self.create_key_terms_content(fmea_data, metadata)
        if terms_content:
            terms_doc = Document(
                page_content=terms_content,
                metadata={**metadata, "content_section": "key_terms"}
            )
            documents.append(terms_doc)
            print(f"DEBUG - FMEAProcessor: Created key terms chunk")
        
        print(f"DEBUG - FMEAProcessor: Finished creating {len(documents)} chunks total")
        return documents
    
    def create_summary_content(self, fmea_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create a summary of the FMEA document.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with summary content
        """
        content = "# FMEA DOCUMENT SUMMARY\n\n"
        
        # Add document metadata
        content += f"Document Title: {metadata.get('document_title', 'N/A')}\n"
        content += f"Document ID: {metadata.get('document_id', 'N/A')}\n"
        content += f"Version: {metadata.get('document_version', 'N/A')}\n"
        content += f"Date: {metadata.get('document_date', 'N/A')}\n\n"
        
        # Add FMEA type
        content += f"FMEA Type: {metadata.get('fmea_type', 'N/A')}\n\n"
        
        # Add system information
        content += f"System/Product: {metadata.get('system_name', 'N/A')}\n\n"
        
        # Add critical metrics
        content += f"Highest Severity: {metadata.get('highest_severity', 'Unknown')}\n"
        content += f"Highest RPN: {metadata.get('highest_rpn', 'Unknown')}\n"
        content += f"Number of Critical Failure Modes: {metadata.get('critical_failure_count', 0)}\n"
        content += f"Total Failure Modes: {len(metadata.get('failure_modes', []))}\n\n"
        
        # Add purpose statement
        purpose = fmea_data.get("purpose", "")
        if purpose:
            content += f"Purpose:\n{purpose}\n\n"
        
        # Add scope statement
        scope = fmea_data.get("scope", "")
        if scope:
            content += f"Scope:\n{scope}\n"
        
        return content
    
    def create_system_info_content(self, fmea_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for system information section.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with system information content
        """
        system_info = fmea_data.get("systemInformation", {})
        if not system_info:
            return ""
        
        content = "# SYSTEM INFORMATION\n\n"
        content += f"System/Product Name: {system_info.get('systemName', 'N/A')}\n"
        content += f"System Description: {system_info.get('systemDescription', 'N/A')}\n\n"
        
        # Add functional requirements
        requirements = system_info.get("functionalRequirements", [])
        if requirements:
            content += "Functional Requirements:\n"
            for req in requirements:
                content += f"- {req.get('requirementName', 'N/A')}: {req.get('description', 'N/A')}\n"
            content += "\n"
        
        # Add system components
        components = system_info.get("systemComponents", [])
        if components:
            content += "System Components:\n"
            for component in components:
                content += f"- {component.get('componentName', 'N/A')}: {component.get('description', 'N/A')}\n"
            content += "\n"
        
        # Add operation conditions
        conditions = system_info.get("operationConditions", [])
        if conditions:
            content += "Operation Conditions:\n"
            for condition in conditions:
                content += f"- {condition}\n"
            content += "\n"
        
        # Add assumptions
        assumptions = system_info.get("assumptions", [])
        if assumptions:
            content += "Assumptions:\n"
            for assumption in assumptions:
                content += f"- {assumption}\n"
            content += "\n"
        
        # Add limitations
        limitations = system_info.get("limitations", [])
        if limitations:
            content += "Limitations:\n"
            for limitation in limitations:
                content += f"- {limitation}\n"
        
        return content
    
    def create_failure_mode_chunks(self, fmea_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[Document]:
        """Create individual document chunks for each failure mode.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            List of Document objects for failure modes
        """
        documents = []
        
        # Handle both direct structure and nested structure formats
        failure_modes = []
        
        # Check for nested structure (inside fmeaAnalysis)
        if "fmeaAnalysis" in fmea_data and "failureModes" in fmea_data["fmeaAnalysis"]:
            print(f"DEBUG - FMEAProcessor: Found nested failure modes structure")
            failure_modes = fmea_data["fmeaAnalysis"].get("failureModes", [])
        # Check for root-level structure
        elif "failureModes" in fmea_data:
            print(f"DEBUG - FMEAProcessor: Found root-level failure modes structure")
            failure_modes = fmea_data.get("failureModes", [])
        else:
            print(f"DEBUG - FMEAProcessor: No failure modes found in data structure!")
            return documents
        
        print(f"DEBUG - FMEAProcessor: Found {len(failure_modes)} failure modes to process")
        
        if not failure_modes:
            return documents
        
        # Create a base summary for context in each failure mode document
        base_summary = f"# FMEA DOCUMENT: {metadata.get('document_title', 'N/A')}\n"
        base_summary += f"System/Product: {metadata.get('system_name', 'N/A')}\n\n"
        
        for mode in failure_modes:
            mode_name = mode.get("failureModeName", mode.get("description", "N/A"))
            mode_id = mode.get("failureModeId", mode.get("id", "N/A"))
            
            print(f"DEBUG - FMEAProcessor: Processing failure mode {mode_id}: {mode_name}")
            
            content = f"{base_summary}# FAILURE MODE: {mode_name}\n\n"
            content += f"Failure Mode ID: {mode_id}\n"
            content += f"Description: {mode.get('description', 'N/A')}\n\n"
            
            # Add related component - adapt to handle different schemas
            component = mode.get("component", "N/A")
            function = mode.get("function", "N/A")
            
            # If function is not available directly, check for function in item section 
            # (for nested structures like in hvac-control-fmea.json)
            if function == "N/A" and "fmeaAnalysis" in fmea_data and "item" in fmea_data["fmeaAnalysis"]:
                function = fmea_data["fmeaAnalysis"]["item"].get("function", "N/A")
                
            content += f"Component: {component}\n"
            content += f"Function: {function}\n\n"
            
            # Add effects - handle both direct and nested structures
            if "failureEffects" in mode:
                effects = [{"localEffect": mode["failureEffects"].get("local", "N/A"),
                           "systemEffect": mode["failureEffects"].get("nextLevel", "N/A"),
                           "endEffect": mode["failureEffects"].get("endEffect", "N/A")}]
                content += "Effects:\n"
                for effect in effects:
                    content += f"- Local Effect: {effect.get('localEffect', 'N/A')}\n"
                    content += f"  System Effect: {effect.get('systemEffect', 'N/A')}\n"
                    content += f"  End Effect: {effect.get('endEffect', 'N/A')}\n\n"
            elif "effects" in mode:
                effects = mode.get("effects", [])
                if effects:
                    content += "Effects:\n"
                    for effect in effects:
                        content += f"- Local Effect: {effect.get('localEffect', 'N/A')}\n"
                        content += f"  System Effect: {effect.get('systemEffect', 'N/A')}\n"
                        content += f"  End Effect: {effect.get('endEffect', 'N/A')}\n\n"
            
            # Add causes - handle different possible structures
            causes = []
            if "causes" in mode:
                causes = mode.get("causes", [])
                if causes:
                    content += "Causes:\n"
                    for cause in causes:
                        if isinstance(cause, dict):
                            content += f"- Cause: {cause.get('causeName', 'N/A')}\n"
                            content += f"  Description: {cause.get('causeDescription', 'N/A')}\n\n"
                        else:
                            content += f"- Cause: {cause}\n\n"
            elif "potentialCauses" in mode:
                potential_causes = mode.get("potentialCauses", [])
                if potential_causes:
                    content += "Potential Causes:\n"
                    for cause in potential_causes:
                        content += f"- {cause}\n"
                    content += "\n"
            
            # Add severity, occurrence, detection and RPN
            content += f"Severity Rating: {mode.get('severity', mode.get('severityRating', 'N/A'))}\n"
            content += f"Occurrence Rating: {mode.get('occurrence', mode.get('occurrenceRating', 'N/A'))}\n"
            content += f"Detection Rating: {mode.get('detection', mode.get('detectionRating', 'N/A'))}\n"
            content += f"Risk Priority Number (RPN): {mode.get('rpn', mode.get('riskPriorityNumber', 'N/A'))}\n\n"
            
            # Add ASIL rating if available (common in automotive FMEAs)
            if "asilRating" in mode:
                content += f"ASIL Rating: {mode.get('asilRating', 'N/A')}\n\n"
            
            # Add current controls or preventive measures
            current_controls = mode.get("currentControls", [])
            prevention = mode.get("prevention", [])
            detection_methods = mode.get("detection", [])
            
            if current_controls:
                content += "Current Controls:\n"
                for control in current_controls:
                    content += f"- Prevention: {control.get('preventionControl', 'N/A')}\n"
                    content += f"  Detection: {control.get('detectionControl', 'N/A')}\n\n"
            elif prevention or detection_methods:
                content += "Controls:\n"
                if prevention:
                    content += "Prevention:\n"
                    for p in prevention:
                        content += f"- {p}\n"
                    content += "\n"
                if detection_methods:
                    content += "Detection:\n"
                    for d in detection_methods:
                        content += f"- {d}\n"
                    content += "\n"
            
            # Add mitigations if available
            mitigations = mode.get("mitigations", [])
            if mitigations:
                content += "Mitigations:\n"
                for mitigation in mitigations:
                    if isinstance(mitigation, dict):
                        content += f"- {mitigation.get('description', 'N/A')}\n"
                        content += f"  Type: {mitigation.get('type', 'N/A')}\n"
                        content += f"  Effectiveness: {mitigation.get('effectiveness', 'N/A')}\n\n"
                    else:
                        content += f"- {mitigation}\n"
                content += "\n"
            
            # Add recommended actions or safety requirements
            recommended_actions = mode.get("recommendedActions", [])
            safety_requirements = mode.get("safetyRequirements", [])
            
            if recommended_actions:
                content += "Recommended Actions:\n"
                for action in recommended_actions:
                    content += f"- Action: {action.get('actionDescription', 'N/A')}\n"
                    content += f"  Responsibility: {action.get('responsibility', 'N/A')}\n"
                    content += f"  Target Date: {action.get('targetDate', 'N/A')}\n"
                    content += f"  Status: {action.get('status', 'N/A')}\n\n"
            
            if safety_requirements:
                content += "Safety Requirements:\n"
                for req in safety_requirements:
                    content += f"- ID: {req.get('id', 'N/A')}\n"
                    content += f"  Description: {req.get('description', 'N/A')}\n"
                    content += f"  Type: {req.get('type', 'N/A')}\n"
                    content += f"  Verification: {req.get('verification', 'N/A')}\n\n"
            
            # Create failure mode-specific metadata
            mode_metadata = {
                **metadata,
                "content_section": "failure_mode",
                "failure_mode_name": mode_name,
                "failure_mode_id": mode_id,
                "component": component,
                "severity": str(mode.get("severity", mode.get("severityRating", ""))),
                "occurrence": str(mode.get("occurrence", mode.get("occurrenceRating", ""))),
                "detection": str(mode.get("detection", mode.get("detectionRating", ""))),
                "rpn": str(mode.get("rpn", mode.get("riskPriorityNumber", "")))
            }
            
            mode_doc = Document(
                page_content=content,
                metadata=mode_metadata
            )
            documents.append(mode_doc)
        
        return documents
    
    def create_recommended_actions_content(self, fmea_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for recommended actions section.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with recommended actions content
        """
        failure_modes = fmea_data.get("failureModes", [])
        if not failure_modes:
            return ""
        
        content = "# RECOMMENDED ACTIONS\n\n"
        
        # Extract and consolidate all recommended actions
        all_actions = []
        for mode in failure_modes:
            mode_name = mode.get("failureModeName", "N/A")
            mode_id = mode.get("failureModeId", "N/A")
            severity = mode.get("severity", "N/A")
            rpn = mode.get("rpn", "N/A")
            
            for action in mode.get("recommendedActions", []):
                all_actions.append({
                    "mode_name": mode_name,
                    "mode_id": mode_id,
                    "severity": severity,
                    "rpn": rpn,
                    "action": action.get("actionDescription", "N/A"),
                    "responsibility": action.get("responsibility", "N/A"),
                    "target_date": action.get("targetDate", "N/A"),
                    "status": action.get("status", "N/A")
                })
        
        if not all_actions:
            return ""
        
        # Sort actions by RPN (descending) to prioritize highest risk items
        all_actions.sort(key=lambda x: int(x["rpn"]) if str(x["rpn"]).isdigit() else 0, reverse=True)
        
        # Format the consolidated actions
        for action in all_actions:
            content += f"Failure Mode: {action['mode_name']} (ID: {action['mode_id']})\n"
            content += f"Severity: {action['severity']}, RPN: {action['rpn']}\n"
            content += f"Action: {action['action']}\n"
            content += f"Responsibility: {action['responsibility']}\n"
            content += f"Target Date: {action['target_date']}\n"
            content += f"Status: {action['status']}\n\n"
        
        return content
    
    def create_detection_methods_content(self, fmea_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for detection methods section.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with detection methods content
        """
        failure_modes = fmea_data.get("failureModes", [])
        if not failure_modes:
            return ""
        
        content = "# DETECTION METHODS\n\n"
        
        # Extract and consolidate all detection methods
        detection_methods = set()
        mode_to_detection = {}
        
        for mode in failure_modes:
            mode_name = mode.get("failureModeName", "N/A")
            
            for control in mode.get("currentControls", []):
                detection = control.get("detectionControl", "")
                if detection and detection != "N/A":
                    detection_methods.add(detection)
                    
                    if detection not in mode_to_detection:
                        mode_to_detection[detection] = []
                    
                    mode_to_detection[detection].append(mode_name)
        
        if not detection_methods:
            return ""
        
        # Format the detection methods
        content += "Common Detection Methods:\n\n"
        
        for method in sorted(detection_methods):
            content += f"Detection Method: {method}\n"
            content += "Used for Failure Modes:\n"
            
            for mode in mode_to_detection.get(method, []):
                content += f"- {mode}\n"
            
            content += "\n"
        
        return content
    
    def create_key_terms_content(self, fmea_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content with key terms and synonyms to improve search.
        
        Args:
            fmea_data: The parsed FMEA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with key terms content
        """
        content = "# KEY TERMS AND COMMON SYNONYMS\n\n"
        
        # Add document and system info for context
        content += f"Document: {metadata.get('document_title', 'N/A')}\n"
        content += f"System/Product: {metadata.get('system_name', 'N/A')}\n\n"
        
        # Add generic FMEA-related terms to improve retrievability
        content += "This document contains information about:\n"
        content += "- Failure Mode and Effects Analysis (FMEA)\n"
        content += "- Failure modes, effects, and causes\n"
        content += "- Risk Priority Numbers (RPN)\n"
        content += "- Severity, Occurrence, and Detection ratings\n"
        content += "- Recommended actions and current controls\n\n"
        
        # Add document-specific key terms
        content += "Document-specific key terms:\n"
        
        # Add failure modes as key terms
        for mode in metadata.get('failure_modes', []):
            content += f"- Failure Mode: {mode}\n"
        
        # Add components mentioned in the document
        components = set()
        for mode in fmea_data.get("failureModes", []):
            component = mode.get("component", "")
            if component and component not in components:
                components.add(component)
                content += f"- Component: {component}\n"
        
        # Add functions mentioned in the document
        functions = set()
        for mode in fmea_data.get("failureModes", []):
            function = mode.get("function", "")
            if function and function not in functions:
                functions.add(function)
                content += f"- Function: {function}\n"
        
        return content 