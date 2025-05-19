import os
import json
import re
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


class TARAProcessor(JSONProcessor):
    """Processor for TARA (Threat Analysis and Risk Assessment) JSON documents.
    
    Specialized processor that handles the unique structure of TARA documents
    across three phases (impact-analysis, risk-assessment, threat-scenarios),
    with optimized chunking strategies for improved retrieval in RAG applications.
    """
    
    def __init__(self, domain: str = "security"):
        """Initialize the TARA processor with the security domain.
        
        Args:
            domain: The semantic domain for TARA documents (default: "security")
        """
        super().__init__(domain)
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process a TARA file and return a list of semantically chunked Document objects.
        
        Creates specialized chunks based on TARA document sections to improve
        retrieval performance in RAG applications.
        
        Args:
            file_path: Path to the TARA JSON file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        print(f"DEBUG - TARAProcessor: Processing {filename}")
        
        # Determine TARA phase from filename
        phase = self._determine_tara_phase(filename)
        if not phase:
            error_msg = f"Unable to determine TARA phase from filename: {filename}"
            print(f"DEBUG - TARAProcessor: {error_msg}")
            error_doc = Document(
                page_content=error_msg,
                metadata={
                    "source": filename,
                    "source_type": "tara",
                    "domain": self.domain,
                    "error": error_msg
                }
            )
            return [error_doc]
        
        print(f"DEBUG - TARAProcessor: Detected TARA phase: {phase}")
        
        try:
            # Load the JSON file
            with open(file_path, 'r') as f:
                tara_data = json.load(f)
            
            # Extract TARA metadata
            metadata = self.extract_tara_metadata(tara_data, phase)
            
            # Add source information to metadata
            metadata["source"] = filename
            metadata["source_type"] = "tara"
            metadata["tara_phase"] = phase
            metadata["domain"] = self.domain
            
            # Create TARA-specific chunks based on the phase
            documents = self.create_phase_specific_chunks(tara_data, metadata, phase)
            
            print(f"DEBUG - TARAProcessor: Successfully created {len(documents)} chunks for {filename}")
            for i, doc in enumerate(documents):
                print(f"DEBUG - TARAProcessor: Document {i} section: {doc.metadata.get('content_section', 'unknown')}")
                
            return documents
            
        except Exception as e:
            # Return a single document with error information
            error_msg = f"Error processing TARA file: {str(e)}"
            print(f"DEBUG - TARAProcessor: {error_msg}")
            error_doc = Document(
                page_content=error_msg,
                metadata={
                    "source": filename,
                    "source_type": "tara",
                    "tara_phase": phase,
                    "domain": self.domain,
                    "error": str(e)
                }
            )
            return [error_doc]
    
    def _determine_tara_phase(self, filename: str) -> Optional[str]:
        """Determine the TARA phase from the filename.
        
        Args:
            filename: The filename to analyze
            
        Returns:
            TARA phase as string or None if not determinable
        """
        if not filename.startswith("tara-"):
            return None
            
        if "impact-analysis" in filename:
            return "impact-analysis"
        elif "risk-assessment" in filename:
            return "risk-assessment"
        elif "threat-scenarios" in filename:
            return "threat-scenarios"
        
        return None
    
    def extract_tara_metadata(self, tara_data: Dict[str, Any], phase: str) -> Dict[str, Any]:
        """Extract metadata from TARA document for improved retrieval.
        
        Args:
            tara_data: The parsed TARA JSON data
            phase: The TARA phase
            
        Returns:
            Dictionary of metadata extracted from the TARA document
        """
        metadata = {}
        
        # Extract metadata section if available
        doc_metadata = tara_data.get("metadata", {})
        
        # Extract basic document metadata
        metadata["document_type"] = "TARA"
        metadata["document_title"] = doc_metadata.get("documentId", "")
        metadata["document_id"] = doc_metadata.get("documentId", "")
        metadata["document_version"] = doc_metadata.get("version", "")
        metadata["document_date"] = doc_metadata.get("creationDate", "")
        metadata["document_status"] = doc_metadata.get("status", "")
        metadata["tara_standard"] = doc_metadata.get("standard", "")
        
        # Extract system information
        metadata["system"] = doc_metadata.get("system", "")
        metadata["subsystem"] = doc_metadata.get("subsystem", "")
        
        # Add asset information if available
        sections = tara_data.get("sections", {})
        if "assetIdentification" in sections:
            asset = sections.get("assetIdentification", {})
            metadata["asset_name"] = asset.get("assetName", "")
            metadata["asset_type"] = asset.get("assetType", "")
            
        return metadata
    
    def create_phase_specific_chunks(self, tara_data: Dict[str, Any], metadata: Dict[str, Any], phase: str) -> List[Document]:
        """Create specialized semantic chunks from TARA data based on phase.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata to attach to each chunk
            phase: The TARA phase
            
        Returns:
            List of Document objects representing semantic chunks
        """
        if phase == "impact-analysis":
            return self.process_impact_analysis(tara_data, metadata)
        elif phase == "risk-assessment":
            return self.process_risk_assessment(tara_data, metadata)
        elif phase == "threat-scenarios":
            return self.process_threat_scenarios(tara_data, metadata)
        else:
            # Return a minimal document if phase is unknown
            error_msg = f"Unknown TARA phase: {phase}"
            error_doc = Document(
                page_content=error_msg,
                metadata=metadata
            )
            return [error_doc]
    
    def process_impact_analysis(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[Document]:
        """Process an Impact Analysis TARA document.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of Document objects with specialized chunks
        """
        documents = []
        print(f"DEBUG - TARAProcessor: Processing Impact Analysis document")
        
        # Create a summary chunk
        summary_content = self.create_summary_content(tara_data, metadata)
        summary_doc = Document(
            page_content=summary_content,
            metadata={**metadata, "content_section": "summary"}
        )
        documents.append(summary_doc)
        print(f"DEBUG - TARAProcessor: Created summary chunk")
        
        # Create asset information chunk
        asset_content = self.create_asset_information(tara_data, metadata)
        if asset_content:
            asset_doc = Document(
                page_content=asset_content,
                metadata={**metadata, "content_section": "asset_information"}
            )
            documents.append(asset_doc)
            print(f"DEBUG - TARAProcessor: Created asset information chunk")
        
        # Create individual damage scenario chunks
        sections = tara_data.get("sections", {})
        damage_scenarios = sections.get("damageScenarios", [])
        
        # Handle case where damage_scenarios might not be a list
        if not isinstance(damage_scenarios, list) and isinstance(damage_scenarios, dict):
            # If it's a dictionary with scenarios as values, convert to list
            damage_scenarios = list(damage_scenarios.values())
        
        if isinstance(damage_scenarios, list):
            for scenario in damage_scenarios:
                if isinstance(scenario, dict):  # Ensure it's a dictionary before processing
                    scenario_doc = self.create_damage_scenario_chunk(scenario, tara_data, metadata)
                    documents.append(scenario_doc)
            print(f"DEBUG - TARAProcessor: Created {len(damage_scenarios)} damage scenario chunks")
        
        # Create asset value assessment chunk
        asset_value = sections.get("assetValueAssessment", None)
        if asset_value is not None:
            asset_value_content = self.create_asset_value_content(asset_value, tara_data, metadata)
            if asset_value_content:
                asset_value_doc = Document(
                    page_content=asset_value_content,
                    metadata={**metadata, "content_section": "asset_value_assessment"}
                )
                documents.append(asset_value_doc)
                print(f"DEBUG - TARAProcessor: Created asset value assessment chunk")
        
        # Create cybersecurity goals chunk
        cs_goals = sections.get("cybersecurityGoals", None)
        if cs_goals is not None:
            cs_goals_content = self.create_cybersecurity_goals_content(cs_goals, tara_data, metadata)
            if cs_goals_content:
                cs_goals_doc = Document(
                    page_content=cs_goals_content,
                    metadata={**metadata, "content_section": "cybersecurity_goals"}
                )
                documents.append(cs_goals_doc)
                print(f"DEBUG - TARAProcessor: Created cybersecurity goals chunk")
        
        # Create key terms chunk for improved search
        terms_content = self.create_key_terms_content(tara_data, metadata)
        if terms_content:
            terms_doc = Document(
                page_content=terms_content,
                metadata={**metadata, "content_section": "key_terms"}
            )
            documents.append(terms_doc)
            print(f"DEBUG - TARAProcessor: Created key terms chunk")
        
        return documents
        
    def create_summary_content(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create a summary of the TARA document.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with summary content
        """
        content = "# TARA DOCUMENT SUMMARY\n\n"
        
        # Add document metadata
        doc_metadata = tara_data.get("metadata", {})
        content += f"Document ID: {doc_metadata.get('documentId', 'N/A')}\n"
        content += f"Document Type: TARA - {metadata.get('tara_phase', 'Unknown').title()}\n"
        content += f"Standard: {doc_metadata.get('standard', 'N/A')}\n"
        content += f"Version: {doc_metadata.get('version', 'N/A')}\n"
        content += f"Date: {doc_metadata.get('creationDate', 'N/A')}\n"
        content += f"Status: {doc_metadata.get('status', 'N/A')}\n\n"
        
        # Add system information
        content += f"System/Subsystem: {doc_metadata.get('system', 'N/A')} / {doc_metadata.get('subsystem', 'N/A')}\n\n"
        
        # Add phase-specific overview
        if metadata.get('tara_phase') == "impact-analysis":
            sections = tara_data.get("sections", {})
            damage_scenarios = sections.get("damageScenarios", [])
            content += f"Impact Analysis Overview:\n"
            content += f"Number of Damage Scenarios: {len(damage_scenarios)}\n"
            
            # Add severity counts if available
            severe_count = sum(1 for scenario in damage_scenarios if scenario.get("overallImpactRating") == "Severe")
            moderate_count = sum(1 for scenario in damage_scenarios if scenario.get("overallImpactRating") == "Moderate")
            low_count = sum(1 for scenario in damage_scenarios if scenario.get("overallImpactRating") == "Low")
            
            content += f"Severity Distribution: {severe_count} Severe, {moderate_count} Moderate, {low_count} Low\n\n"
            
            # Add asset value if available
            asset_value = sections.get("assetValueAssessment", {})
            if asset_value:
                content += f"Overall Asset Value: {asset_value.get('overallAssetValue', 'N/A')}\n\n"
            
            # Add cybersecurity goals count
            cs_goals = sections.get("cybersecurityGoals", [])
            content += f"Number of Cybersecurity Goals: {len(cs_goals)}\n"
        
        return content
    
    def create_asset_information(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for asset information section.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with asset information content
        """
        sections = tara_data.get("sections", {})
        asset_info = sections.get("assetIdentification", {})
        if not asset_info:
            return ""
        
        content = "# ASSET INFORMATION\n\n"
        content += f"Asset Name: {asset_info.get('assetName', 'N/A')}\n"
        content += f"Asset Type: {asset_info.get('assetType', 'N/A')}\n"
        content += f"Asset Description: {asset_info.get('assetDescription', 'N/A')}\n\n"
        
        # Add related components
        components = asset_info.get("relatedComponents", [])
        if components:
            content += "Related Components:\n"
            for component in components:
                content += f"- {component}\n"
            content += "\n"
        
        return content
    
    def create_damage_scenario_chunk(self, scenario: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> Document:
        """Create a document chunk for a single damage scenario.
        
        Args:
            scenario: The damage scenario data
            tara_data: The full TARA document data for context
            metadata: Base metadata to extend
            
        Returns:
            Document object with scenario content and metadata
        """
        scenario_id = scenario.get("id", "unknown")
        scenario_title = scenario.get("title", "unknown")
        
        # Create a content string for this scenario
        content = f"# DAMAGE SCENARIO: {scenario_title}\n\n"
        content += f"ID: {scenario_id}\n"
        content += f"Description: {scenario.get('description', 'N/A')}\n\n"
        
        # Add impact areas - handle both dictionary and list structures
        impact_areas = scenario.get("impactAreas", {})
        if impact_areas:
            content += "## Impact Areas\n\n"
            
            if isinstance(impact_areas, dict):
                # Handle dictionary-style impact areas (key-value pairs of areas)
                for area, impact_info in impact_areas.items():
                    if isinstance(impact_info, dict):
                        rating = impact_info.get("rating", "unknown")
                        justification = impact_info.get("justification", "N/A")
                        
                        content += f"### {area.title()} Impact: {rating}\n"
                        content += f"Justification: {justification}\n\n"
                    elif isinstance(impact_info, str):
                        # Handle simple string values
                        content += f"### {area.title()} Impact: {impact_info}\n\n"
            elif isinstance(impact_areas, list):
                # Handle list-style impact areas
                for impact in impact_areas:
                    if isinstance(impact, dict):
                        area = impact.get("area", "unknown")
                        rating = impact.get("impactRating", "unknown")
                        description = impact.get("description", "N/A")
                        justification = impact.get("justification", "N/A")
                        
                        content += f"### {area} Impact: {rating}\n"
                        content += f"Description: {description}\n"
                        content += f"Justification: {justification}\n\n"
        
        # Add overall impact rating
        overall_impact = scenario.get("overallImpactRating", {})
        content += f"## Overall Impact Assessment\n\n"
        
        if isinstance(overall_impact, dict):
            content += f"Overall Impact Rating: {overall_impact.get('rating', 'N/A')}\n"
            content += f"Justification: {overall_impact.get('justification', 'N/A')}\n\n"
        elif isinstance(overall_impact, str):
            content += f"Overall Impact Rating: {overall_impact}\n"
            content += f"Justification: {scenario.get('justification', 'N/A')}\n\n"
        
        # Add ASIL rating if available
        asil_rating = scenario.get("asilRating", None)
        if asil_rating:
            if isinstance(asil_rating, dict):
                content += f"ASIL Rating: {asil_rating.get('rating', 'N/A')}\n"
                content += f"ASIL Justification: {asil_rating.get('justification', 'N/A')}\n\n"
            elif isinstance(asil_rating, str):
                content += f"ASIL Rating: {asil_rating}\n"
                content += f"ASIL Justification: {scenario.get('asilJustification', 'N/A')}\n\n"
        
        # Add FMEA rating if available
        fmea = scenario.get("fmeaRating", {})
        if fmea:
            content += "## FMEA Rating\n\n"
            if isinstance(fmea, dict):
                content += f"Severity: {fmea.get('severity', 'N/A')}\n"
                content += f"Occurrence: {fmea.get('occurrence', 'N/A')}\n"
                content += f"Detection: {fmea.get('detection', 'N/A')}\n"
                content += f"RPN: {fmea.get('rpn', 'N/A')}\n"
        
        # Create scenario-specific metadata
        scenario_metadata = {
            **metadata,
            "content_section": "damage_scenario",
            "damage_scenario_id": scenario_id,
            "damage_scenario_title": scenario_title,
        }
        
        # Add optional fields with type checking
        if isinstance(overall_impact, dict) and "rating" in overall_impact:
            scenario_metadata["impact_rating"] = overall_impact.get("rating", "")
        elif isinstance(overall_impact, str):
            scenario_metadata["impact_rating"] = overall_impact
            
        if isinstance(asil_rating, dict) and "rating" in asil_rating:
            scenario_metadata["asil_rating"] = asil_rating.get("rating", "")
        elif isinstance(asil_rating, str):
            scenario_metadata["asil_rating"] = asil_rating
        
        # Add FMEA metadata if available with type checking
        if isinstance(fmea, dict):
            severity = fmea.get("severity", "")
            rpn = fmea.get("rpn", "")
            if severity:
                scenario_metadata["fmea_severity"] = str(severity)
            if rpn:
                scenario_metadata["fmea_rpn"] = str(rpn)
        
        return Document(
            page_content=content,
            metadata=scenario_metadata
        )
    
    def create_asset_value_content(self, asset_value: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for asset value assessment section.
        
        Args:
            asset_value: Asset value assessment data
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with asset value content
        """
        if not asset_value:
            return ""
        
        content = "# ASSET VALUE ASSESSMENT\n\n"
        
        # Add methodology information
        methodology = asset_value.get("methodology", {})
        if methodology:
            content += f"Methodology: {methodology.get('name', 'N/A')}\n"
            content += f"Description: {methodology.get('description', 'N/A')}\n\n"
        
        # Add value factors
        value_factors = asset_value.get("valueFactors", [])
        if value_factors:
            content += "## Value Factors\n\n"
            for factor in value_factors:
                content += f"### {factor.get('factor', 'unknown')}: {factor.get('rating', 'unknown')}\n"
                content += f"Justification: {factor.get('justification', 'N/A')}\n\n"
        
        # Add overall asset value
        content += "## Overall Asset Value\n\n"
        content += f"Overall Value: {asset_value.get('overallAssetValue', 'N/A')}\n"
        content += f"Justification: {asset_value.get('justification', 'N/A')}\n"
        
        return content
    
    def create_cybersecurity_goals_content(self, cs_goals: List[Dict[str, Any]], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for cybersecurity goals section.
        
        Args:
            cs_goals: List of cybersecurity goals
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with cybersecurity goals content
        """
        if not cs_goals:
            return ""
        
        content = "# CYBERSECURITY GOALS\n\n"
        
        for goal in cs_goals:
            goal_id = goal.get("id", "unknown")
            goal_title = goal.get("title", "unknown")
            
            content += f"## {goal_id}: {goal_title}\n\n"
            content += f"Description: {goal.get('description', 'N/A')}\n"
            
            # Add related damage scenarios
            damage_scenarios = goal.get("damageScenarios", [])
            if damage_scenarios:
                content += "Related Damage Scenarios:\n"
                for ds in damage_scenarios:
                    content += f"- {ds}\n"
                content += "\n"
            
            content += f"Security Property: {goal.get('securityProperty', 'N/A')}\n"
            content += f"ASIL Rating: {goal.get('asilRating', 'N/A')}\n\n"
        
        return content

    def process_risk_assessment(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[Document]:
        """Process a Risk Assessment TARA document.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of Document objects with specialized chunks
        """
        documents = []
        print(f"DEBUG - TARAProcessor: Processing Risk Assessment document")
        
        # Create a summary chunk
        summary_content = self.create_risk_assessment_summary(tara_data, metadata)
        summary_doc = Document(
            page_content=summary_content,
            metadata={**metadata, "content_section": "summary"}
        )
        documents.append(summary_doc)
        print(f"DEBUG - TARAProcessor: Created summary chunk")
        
        # Create asset information chunk
        asset_content = self.create_asset_information(tara_data, metadata)
        if asset_content:
            asset_doc = Document(
                page_content=asset_content,
                metadata={**metadata, "content_section": "asset_information"}
            )
            documents.append(asset_doc)
            print(f"DEBUG - TARAProcessor: Created asset information chunk")
        
        # Create risk methodology chunk
        sections = tara_data.get("sections", {})
        risk_methodology = sections.get("riskMethodology", {})
        if risk_methodology:
            methodology_content = self.create_risk_methodology_content(risk_methodology, tara_data, metadata)
            methodology_doc = Document(
                page_content=methodology_content,
                metadata={**metadata, "content_section": "risk_methodology"}
            )
            documents.append(methodology_doc)
            print(f"DEBUG - TARAProcessor: Created risk methodology chunk")
        
        # Create individual risk assessment chunks
        # Try both singular and plural forms of the section names
        risks = []
        risk_assessment = sections.get("riskAssessment", {})
        
        # Handle both structures: if it's a dict with a "risks" key or if it's an array directly
        if isinstance(risk_assessment, dict):
            risks = risk_assessment.get("risks", [])
        elif isinstance(risk_assessment, list):
            # In some files, the riskAssessment is an array directly
            risks = risk_assessment
        
        # Also try alternative plural form "riskAssessments"
        if not risks:
            risk_assessments = sections.get("riskAssessments", [])
            if isinstance(risk_assessments, list):
                risks = risk_assessments
        
        if risks:
            for risk in risks:
                if isinstance(risk, dict):  # Ensure it's a dictionary before processing
                    risk_doc = self.create_risk_chunk(risk, tara_data, metadata)
                    documents.append(risk_doc)
            print(f"DEBUG - TARAProcessor: Created {len(risks)} risk assessment chunks")
        
        # Create security controls/mitigation chunk
        mitigation_strategy = sections.get("mitigationStrategy", None)
        if mitigation_strategy is not None:
            # Pass it to the function regardless of type - handling is done there
            controls_content = self.create_security_controls_content(mitigation_strategy, tara_data, metadata)
            if controls_content:
                controls_doc = Document(
                    page_content=controls_content,
                    metadata={**metadata, "content_section": "security_controls"}
                )
                documents.append(controls_doc)
                print(f"DEBUG - TARAProcessor: Created security controls chunk")
        
        # Create residual risk assessment chunk
        residual_risk = sections.get("residualRiskAssessment", None)
        if residual_risk is not None:
            # Pass it to the function regardless of type - handling is done there
            residual_content = self.create_residual_risk_content(residual_risk, tara_data, metadata)
            if residual_content:
                residual_doc = Document(
                    page_content=residual_content,
                    metadata={**metadata, "content_section": "residual_risk_assessment"}
                )
                documents.append(residual_doc)
                print(f"DEBUG - TARAProcessor: Created residual risk assessment chunk")
        
        # Create key terms chunk for improved search
        terms_content = self.create_key_terms_content(tara_data, metadata)
        if terms_content:
            terms_doc = Document(
                page_content=terms_content,
                metadata={**metadata, "content_section": "key_terms"}
            )
            documents.append(terms_doc)
            print(f"DEBUG - TARAProcessor: Created key terms chunk")
        
        return documents
    
    def create_risk_assessment_summary(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create a summary of the Risk Assessment TARA document.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with summary content
        """
        content = "# TARA RISK ASSESSMENT SUMMARY\n\n"
        
        # Add document metadata
        doc_metadata = tara_data.get("metadata", {})
        content += f"Document ID: {doc_metadata.get('documentId', 'N/A')}\n"
        content += f"Document Type: TARA - Risk Assessment\n"
        content += f"Standard: {doc_metadata.get('standard', 'N/A')}\n"
        content += f"Version: {doc_metadata.get('version', 'N/A')}\n"
        content += f"Date: {doc_metadata.get('creationDate', 'N/A')}\n"
        content += f"Status: {doc_metadata.get('status', 'N/A')}\n\n"
        
        # Add system information
        content += f"System/Subsystem: {doc_metadata.get('system', 'N/A')} / {doc_metadata.get('subsystem', 'N/A')}\n\n"
        
        # Add risk assessment overview
        sections = tara_data.get("sections", {})
        
        # Try different formats of risk assessment
        risks = []
        risk_assessment = sections.get("riskAssessment", {})
        
        # Handle both structures: if it's a dict with a "risks" key or if it's an array directly
        if isinstance(risk_assessment, dict):
            risks = risk_assessment.get("risks", [])
        elif isinstance(risk_assessment, list):
            risks = risk_assessment
            
        # Also try alternative plural form "riskAssessments"
        if not risks:
            risk_assessments = sections.get("riskAssessments", [])
            if isinstance(risk_assessments, list):
                risks = risk_assessments
        
        content += f"Risk Assessment Overview:\n"
        content += f"Number of Risks: {len(risks)}\n"
        
        # Add risk distribution if available - with type checking
        if risks and all(isinstance(risk, dict) for risk in risks):
            critical_count = sum(1 for risk in risks if isinstance(risk, dict) and risk.get("riskRating") == "Critical")
            high_count = sum(1 for risk in risks if isinstance(risk, dict) and risk.get("riskRating") == "High")
            medium_count = sum(1 for risk in risks if isinstance(risk, dict) and risk.get("riskRating") == "Medium")
            low_count = sum(1 for risk in risks if isinstance(risk, dict) and risk.get("riskRating") == "Low")
            
            # Alternative field names - check risk level inside riskLevel structure
            if critical_count == 0 and high_count == 0 and medium_count == 0 and low_count == 0:
                critical_count = sum(1 for risk in risks 
                                   if isinstance(risk, dict) 
                                   and isinstance(risk.get("riskLevel"), dict) 
                                   and risk.get("riskLevel", {}).get("riskRating") == "Critical")
                high_count = sum(1 for risk in risks 
                               if isinstance(risk, dict) 
                               and isinstance(risk.get("riskLevel"), dict)
                               and risk.get("riskLevel", {}).get("riskRating") == "High")
                medium_count = sum(1 for risk in risks 
                                 if isinstance(risk, dict) 
                                 and isinstance(risk.get("riskLevel"), dict)
                                 and risk.get("riskLevel", {}).get("riskRating") == "Medium")
                low_count = sum(1 for risk in risks 
                              if isinstance(risk, dict) 
                              and isinstance(risk.get("riskLevel"), dict)
                              and risk.get("riskLevel", {}).get("riskRating") == "Low")
            
            content += f"Risk Distribution: {critical_count} Critical, {high_count} High, {medium_count} Medium, {low_count} Low\n\n"
        
        # Add security controls count
        mitigation_strategy = sections.get("mitigationStrategy", {})
        controls = []
        if isinstance(mitigation_strategy, dict):
            controls = mitigation_strategy.get("securityControls", [])
        content += f"Number of Security Controls: {len(controls)}\n\n"
        
        # Add residual risk assessment overview
        residual_risk = sections.get("residualRiskAssessment", {})
        if isinstance(residual_risk, dict):
            residual_risks = residual_risk.get("residualRisks", [])
            content += f"Residual Risk Overview:\n"
            content += f"Number of Residual Risks: {len(residual_risks)}\n"
            
            # Add acceptance status if available
            acceptance = residual_risk.get("acceptanceDecision", {})
            if isinstance(acceptance, dict):
                content += f"Risk Acceptance Status: {acceptance.get('acceptanceStatus', 'N/A')}\n"
        
        return content
    
    def create_risk_methodology_content(self, methodology: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for risk methodology section.
        
        Args:
            methodology: Risk methodology data
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with risk methodology content
        """
        if not methodology:
            return ""
        
        content = "# RISK ASSESSMENT METHODOLOGY\n\n"
        content += f"Methodology Name: {methodology.get('name', 'N/A')}\n"
        content += f"Description: {methodology.get('description', 'N/A')}\n\n"
        
        # Add risk levels
        risk_levels = methodology.get("riskLevels", [])
        if risk_levels:
            content += "## Risk Levels\n\n"
            for level in risk_levels:
                content += f"- {level}\n"
            content += "\n"
        
        # Add impact rating scale
        impact_scale = methodology.get("impactRatingScale", {})
        if impact_scale:
            content += "## Impact Rating Scale\n\n"
            for rating, description in impact_scale.items():
                content += f"### {rating}\n"
                content += f"{description}\n\n"
        
        # Add feasibility rating scale
        feasibility_scale = methodology.get("feasibilityRatingScale", {})
        if feasibility_scale:
            content += "## Feasibility Rating Scale\n\n"
            for rating, description in feasibility_scale.items():
                content += f"### {rating}\n"
                content += f"{description}\n\n"
        
        # Add risk matrix
        risk_matrix = methodology.get("riskMatrix", {})
        if risk_matrix:
            content += "## Risk Matrix\n\n"
            content += f"{risk_matrix.get('description', '')}\n\n"
            
            matrix_levels = risk_matrix.get("levels", [])
            if matrix_levels:
                content += "Impact | Feasibility | Risk\n"
                content += "-------|------------|------\n"
                
                for level in matrix_levels:
                    impact = level.get("impact", "")
                    feasibility = level.get("feasibility", "")
                    risk = level.get("risk", "")
                    content += f"{impact} | {feasibility} | {risk}\n"
                content += "\n"
        
        return content
    
    def create_risk_chunk(self, risk: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> Document:
        """Create a document chunk for a single risk assessment.
        
        Args:
            risk: The risk assessment data
            tara_data: The full TARA document data for context
            metadata: Base metadata to extend
            
        Returns:
            Document object with risk content and metadata
        """
        # Get risk ID and title with fallbacks
        risk_id = risk.get("id", "unknown")
        risk_title = risk.get("title", "unknown")
        
        # Get threat ID with fallbacks for different field names
        threat_id = risk.get("threatId", risk.get("threatScenarioIds", []))
        if isinstance(threat_id, list) and threat_id:
            threat_id = threat_id[0]  # Take first ID if it's a list
        elif not isinstance(threat_id, str):
            threat_id = "unknown"
            
        # Get threat ID from assessment references if available
        assessment_refs = risk.get("assessmentReferences", {})
        if isinstance(assessment_refs, dict):
            if not threat_id or threat_id == "unknown":
                threat_id = assessment_refs.get("threatScenarioId", "unknown")
        
        # Create a content string for this risk
        content = f"# RISK ASSESSMENT: {risk_title}\n\n"
        content += f"Risk ID: {risk_id}\n"
        content += f"Related Threat ID: {threat_id}\n"
        content += f"Description: {risk.get('description', 'N/A')}\n\n"
        
        # Add impact assessment - handle different structures
        content += "## Impact Assessment\n\n"
        
        # Handle nested risk level structure vs. direct fields
        impact_rating = "N/A"
        impact_justification = "N/A"
        
        risk_level = risk.get("riskLevel", {})
        if isinstance(risk_level, dict):
            # Structure 1: Nested risk level
            impact_rating = risk_level.get("impactLevel", risk_level.get("impactRating", "N/A"))
            impact_justification = risk_level.get("justification", "N/A")
        else:
            # Structure 2: Direct fields
            impact_rating = risk.get("impactRating", "N/A")
            impact_justification = risk.get("impactJustification", "N/A")
            
            # Structure 3: Look in risk calculation
            if impact_rating == "N/A":
                risk_calc = risk.get("riskCalculation", {})
                if isinstance(risk_calc, dict):
                    params = risk_calc.get("parameters", {})
                    if isinstance(params, dict):
                        impact_val = params.get("impactRating")
                        if impact_val:
                            impact_rating = str(impact_val)
        
        content += f"Impact Rating: {impact_rating}\n"
        content += f"Justification: {impact_justification}\n\n"
        
        # Add feasibility assessment - handle different structures
        content += "## Attack Feasibility Assessment\n\n"
        
        # Get feasibility rating with fallbacks
        feasibility_rating = "N/A"
        feasibility_justification = "N/A"
        
        if isinstance(risk_level, dict):
            # Structure 1: Nested risk level
            feasibility_rating = risk_level.get("attackFeasibilityLevel", "N/A")
            # If justification is shared, don't duplicate
            if risk_level.get("justification") != impact_justification:
                feasibility_justification = risk_level.get("justification", "N/A")
        else:
            # Structure 2: Direct fields
            feasibility_rating = risk.get("feasibilityRating", risk.get("attackFeasibilityRating", "N/A"))
            feasibility_justification = risk.get("feasibilityJustification", "N/A")
            
            # Structure 3: Look in risk calculation
            if feasibility_rating == "N/A":
                risk_calc = risk.get("riskCalculation", {})
                if isinstance(risk_calc, dict):
                    params = risk_calc.get("parameters", {})
                    if isinstance(params, dict):
                        feasibility_val = params.get("attackFeasibilityRating")
                        if feasibility_val:
                            feasibility_rating = str(feasibility_val)
        
        content += f"Feasibility Rating: {feasibility_rating}\n"
        content += f"Justification: {feasibility_justification}\n\n"
        
        # Add overall risk assessment - handle different structures
        content += "## Overall Risk Assessment\n\n"
        
        # Get risk rating with fallbacks
        risk_rating = "N/A"
        risk_justification = "N/A"
        
        if isinstance(risk_level, dict):
            # Structure 1: Nested risk level
            risk_rating = risk_level.get("riskRating", "N/A")
            risk_justification = risk_level.get("justification", "N/A")
        else:
            # Structure 2: Direct fields
            risk_rating = risk.get("riskRating", "N/A")
            risk_justification = risk.get("riskJustification", "N/A")
            
            # Structure 3: Look in risk calculation
            if risk_rating == "N/A":
                risk_calc = risk.get("riskCalculation", {})
                if isinstance(risk_calc, dict):
                    risk_rating = risk_calc.get("riskLevel", risk_calc.get("riskValue", "N/A"))
                    if isinstance(risk_rating, (int, float)):
                        risk_rating = str(risk_rating)
        
        content += f"Risk Rating: {risk_rating}\n"
        content += f"Justification: {risk_justification}\n\n"
        
        # Add risk treatment information if available
        risk_treatment = risk.get("riskTreatment", {})
        if isinstance(risk_treatment, dict):
            content += "## Risk Treatment\n\n"
            
            # Get strategy and description with fallbacks
            strategy = risk_treatment.get("strategy", risk_treatment.get("decision", "N/A"))
            treatment_desc = risk_treatment.get("description", risk_treatment.get("justification", "N/A"))
            
            content += f"Treatment Strategy: {strategy}\n"
            content += f"Description: {treatment_desc}\n\n"
            
            # Add security controls summary if available
            controls = risk_treatment.get("recommendedControls", risk_treatment.get("securityControls", []))
            if isinstance(controls, list) and controls:
                content += "Recommended Controls:\n"
                for control in controls:
                    if isinstance(control, dict):
                        control_id = control.get("id", "unknown")
                        control_name = control.get("name", control.get("title", "unknown"))
                        content += f"- {control_id}: {control_name}\n"
                    elif isinstance(control, str):
                        content += f"- {control}\n"
                content += "\n"
        
        # Create risk-specific metadata
        risk_metadata = {
            **metadata,
            "content_section": "risk_assessment",
            "risk_id": risk_id,
            "risk_title": risk_title,
            "threat_id": threat_id if isinstance(threat_id, str) else "multiple" 
        }
        
        # Add optional fields if available
        if risk_rating != "N/A":
            risk_metadata["risk_rating"] = risk_rating
        
        if impact_rating != "N/A":
            risk_metadata["impact_rating"] = impact_rating
            
        if feasibility_rating != "N/A":
            risk_metadata["feasibility_rating"] = feasibility_rating
        
        return Document(
            page_content=content,
            metadata=risk_metadata
        )
    
    def create_security_controls_content(self, mitigation: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for security controls/mitigation section.
        
        Args:
            mitigation: Mitigation strategy data
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with security controls content
        """
        if not mitigation:
            return ""
        
        content = "# SECURITY CONTROLS\n\n"
        
        # Add security controls - handle both list and dict structures
        controls = []
        if isinstance(mitigation, dict):
            controls = mitigation.get("securityControls", [])
        elif isinstance(mitigation, list):
            # In some files, mitigation might be a list of controls directly
            controls = mitigation
            
        if controls:
            if isinstance(controls, list):
                for control in controls:
                    if isinstance(control, dict):
                        control_id = control.get("id", "unknown")
                        control_title = control.get("title", control.get("name", "unknown"))
                        
                        content += f"## {control_id}: {control_title}\n\n"
                        content += f"Description: {control.get('description', 'N/A')}\n\n"
                        
                        # Add targeted risks - handle both list and string
                        targeted_risks = control.get("targetedRisks", [])
                        if isinstance(targeted_risks, list) and targeted_risks:
                            content += "Targeted Risks:\n"
                            for risk in targeted_risks:
                                content += f"- {risk}\n"
                            content += "\n"
                        elif isinstance(targeted_risks, str) and targeted_risks:
                            content += f"Targeted Risks: {targeted_risks}\n\n"
                        
                        # Get other fields with safe access
                        control_type = control.get("controlType", control.get("type", "N/A"))
                        content += f"Control Type: {control_type}\n"
                        
                        # Try different field names for implementation priority
                        impl_priority = control.get("implementationPriority", 
                                                   control.get("priority", 
                                                              control.get("importance", "N/A")))
                        content += f"Implementation Priority: {impl_priority}\n"
                        
                        # Try different field names for implementation status
                        impl_status = control.get("implementationStatus", 
                                                 control.get("status", "N/A"))
                        content += f"Implementation Status: {impl_status}\n"
                        
                        # Try different field names for verification method
                        verif_method = control.get("verificationMethod", 
                                                  control.get("validationMethod", 
                                                             control.get("validation", "N/A")))
                        content += f"Verification Method: {verif_method}\n"
                        
                        # Try different field names for residual risk
                        residual = control.get("residualRiskAfterControl", 
                                              control.get("residualRisk", 
                                                         control.get("expectedRiskReduction", "N/A")))
                        content += f"Residual Risk After Control: {residual}\n\n"
            elif isinstance(controls, dict):
                # Handle case where controls is a dictionary mapping IDs to control objects
                for control_id, control in controls.items():
                    if isinstance(control, dict):
                        control_title = control.get("title", control.get("name", "unknown"))
                        
                        content += f"## {control_id}: {control_title}\n\n"
                        content += f"Description: {control.get('description', 'N/A')}\n\n"
                        
                        # Add remaining control details as in the list case
                        # (same code as above, simplified for brevity)
                        content += f"Control Type: {control.get('controlType', control.get('type', 'N/A'))}\n"
                        content += f"Implementation Status: {control.get('implementationStatus', control.get('status', 'N/A'))}\n\n"
                    else:
                        # Simple string description
                        content += f"## {control_id}\n\n"
                        content += f"Description: {control}\n\n"
        
        # Add risk treatment strategy
        treatment = {}
        if isinstance(mitigation, dict):
            treatment = mitigation.get("riskTreatmentStrategy", {})
        
        if treatment:
            content += "## Risk Treatment Strategy\n\n"
            
            if isinstance(treatment, dict):
                content += f"{treatment.get('summary', treatment.get('description', 'N/A'))}\n\n"
                content += f"Timeline: {treatment.get('timeline', 'N/A')}\n\n"
                
                # Handle responsible parties as either list or string
                responsible = treatment.get("responsibleParties", [])
                if isinstance(responsible, list):
                    content += "Responsible Parties:\n"
                    for party in responsible:
                        content += f"- {party}\n"
                    content += "\n"
                elif isinstance(responsible, str):
                    content += f"Responsible Parties: {responsible}\n\n"
            elif isinstance(treatment, str):
                content += f"{treatment}\n\n"
        
        return content
    
    def create_residual_risk_content(self, residual: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for residual risk assessment section.
        
        Args:
            residual: Residual risk assessment data
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with residual risk content
        """
        if not residual:
            return ""
        
        content = "# RESIDUAL RISK ASSESSMENT\n\n"
        
        # Add residual risks - handle both list and dict structures
        residual_risks = []
        if isinstance(residual, dict):
            residual_risks = residual.get("residualRisks", [])
        elif isinstance(residual, list):
            # In some files, residual might be a list of risks directly
            residual_risks = residual
        
        if residual_risks:
            if isinstance(residual_risks, list):
                for risk in residual_risks:
                    if isinstance(risk, dict):
                        # Get risk ID with fallbacks
                        risk_id = risk.get("riskId", risk.get("id", "unknown"))
                        
                        content += f"## Residual Risk for {risk_id}\n\n"
                        
                        # Add controls applied - handle list or string
                        controls = risk.get("controlsApplied", [])
                        if isinstance(controls, list) and controls:
                            content += "Controls Applied:\n"
                            for control in controls:
                                content += f"- {control}\n"
                            content += "\n"
                        elif isinstance(controls, str) and controls:
                            content += f"Controls Applied: {controls}\n\n"
                        
                        # Try different field names for residual risk rating
                        risk_rating = risk.get("residualRiskRating", 
                                             risk.get("riskRating", 
                                                    risk.get("rating", "N/A")))
                        content += f"Residual Risk Rating: {risk_rating}\n"
                        
                        # Try different field names for justification
                        justification = risk.get("justification", 
                                              risk.get("rationale", "N/A"))
                        content += f"Justification: {justification}\n\n"
            elif isinstance(residual_risks, dict):
                # Handle case where residual_risks is a dictionary mapping IDs to risk objects
                for risk_id, risk in residual_risks.items():
                    content += f"## Residual Risk for {risk_id}\n\n"
                    
                    if isinstance(risk, dict):
                        # Add controls and other fields as in the list case
                        content += f"Residual Risk Rating: {risk.get('residualRiskRating', risk.get('rating', 'N/A'))}\n"
                        content += f"Justification: {risk.get('justification', 'N/A')}\n\n"
                    else:
                        # Simple string description
                        content += f"Description: {risk}\n\n"
        
        # Add acceptance decision - handle dict and string structures
        acceptance = {}
        if isinstance(residual, dict):
            acceptance = residual.get("acceptanceDecision", {})
        
        if acceptance:
            content += "## Risk Acceptance Decision\n\n"
            
            if isinstance(acceptance, dict):
                content += f"Acceptance Status: {acceptance.get('acceptanceStatus', 'N/A')}\n"
                content += f"Conditions: {acceptance.get('conditions', 'N/A')}\n"
                content += f"Accepted By: {acceptance.get('acceptedBy', 'N/A')}\n"
                content += f"Acceptance Date: {acceptance.get('acceptanceDate', 'N/A')}\n"
            elif isinstance(acceptance, str):
                content += f"Acceptance Details: {acceptance}\n"
        
        return content

    def process_threat_scenarios(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[Document]:
        """Process a Threat Scenarios TARA document.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of Document objects with specialized chunks
        """
        documents = []
        print(f"DEBUG - TARAProcessor: Processing Threat Scenarios document")
        
        # Create a summary chunk
        summary_content = self.create_threat_scenarios_summary(tara_data, metadata)
        summary_doc = Document(
            page_content=summary_content,
            metadata={**metadata, "content_section": "summary"}
        )
        documents.append(summary_doc)
        print(f"DEBUG - TARAProcessor: Created summary chunk")
        
        # Create asset information chunk
        asset_content = self.create_asset_information(tara_data, metadata)
        if asset_content:
            asset_doc = Document(
                page_content=asset_content,
                metadata={**metadata, "content_section": "asset_information"}
            )
            documents.append(asset_doc)
            print(f"DEBUG - TARAProcessor: Created asset information chunk")
        
        # Create cybersecurity properties chunk
        sections = tara_data.get("sections", {})
        cs_properties = sections.get("cybersecurityProperties", None)
        if cs_properties is not None:
            properties_content = self.create_cybersecurity_properties_content(cs_properties, tara_data, metadata)
            if properties_content:
                properties_doc = Document(
                    page_content=properties_content,
                    metadata={**metadata, "content_section": "cybersecurity_properties"}
                )
                documents.append(properties_doc)
                print(f"DEBUG - TARAProcessor: Created cybersecurity properties chunk")
        
        # Create individual threat scenario chunks
        threat_scenarios = sections.get("threatScenarios", [])
        
        # Handle different structures of threat scenarios
        if not isinstance(threat_scenarios, list) and isinstance(threat_scenarios, dict):
            # If it's a dictionary with scenarios as values, convert to list
            threat_scenarios = list(threat_scenarios.values())
        
        if isinstance(threat_scenarios, list):
            for scenario in threat_scenarios:
                if isinstance(scenario, dict):  # Ensure it's a dictionary before processing
                    scenario_doc = self.create_threat_scenario_chunk(scenario, tara_data, metadata)
                    documents.append(scenario_doc)
            print(f"DEBUG - TARAProcessor: Created {len(threat_scenarios)} threat scenario chunks")
        
        # Create threat assessment methodology chunk
        threat_assessment = sections.get("threatAssessment", None)
        if threat_assessment is not None:
            if isinstance(threat_assessment, dict):
                methodology = threat_assessment.get("methodology", {})
                assessments = threat_assessment.get("threatAssessments", [])
                
                # Create methodology chunk
                if methodology:
                    methodology_content = self.create_threat_methodology_content(methodology, tara_data, metadata)
                    methodology_doc = Document(
                        page_content=methodology_content,
                        metadata={**metadata, "content_section": "threat_methodology"}
                    )
                    documents.append(methodology_doc)
                    print(f"DEBUG - TARAProcessor: Created threat methodology chunk")
                
                # Create threat assessments chunk
                if assessments:
                    assessments_content = self.create_threat_assessments_content(assessments, tara_data, metadata)
                    assessments_doc = Document(
                        page_content=assessments_content,
                        metadata={**metadata, "content_section": "threat_assessments"}
                    )
                    documents.append(assessments_doc)
                    print(f"DEBUG - TARAProcessor: Created threat assessments chunk")
            elif isinstance(threat_assessment, list):
                # If threat_assessment is a list, assume it's a list of assessment items
                assessments_content = self.create_threat_assessments_content(threat_assessment, tara_data, metadata)
                if assessments_content:
                    assessments_doc = Document(
                        page_content=assessments_content,
                        metadata={**metadata, "content_section": "threat_assessments"}
                    )
                    documents.append(assessments_doc)
                    print(f"DEBUG - TARAProcessor: Created threat assessments chunk")
        
        # Create key terms chunk for improved search
        terms_content = self.create_key_terms_content(tara_data, metadata)
        if terms_content:
            terms_doc = Document(
                page_content=terms_content,
                metadata={**metadata, "content_section": "key_terms"}
            )
            documents.append(terms_doc)
            print(f"DEBUG - TARAProcessor: Created key terms chunk")
        
        return documents
    
    def create_threat_scenarios_summary(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create a summary of the Threat Scenarios TARA document.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with summary content
        """
        content = "# TARA THREAT SCENARIOS SUMMARY\n\n"
        
        # Add document metadata
        doc_metadata = tara_data.get("metadata", {})
        content += f"Document ID: {doc_metadata.get('documentId', 'N/A')}\n"
        content += f"Document Type: TARA - Threat Scenarios\n"
        content += f"Standard: {doc_metadata.get('standard', 'N/A')}\n"
        content += f"Version: {doc_metadata.get('version', 'N/A')}\n"
        content += f"Date: {doc_metadata.get('creationDate', 'N/A')}\n"
        content += f"Status: {doc_metadata.get('status', 'N/A')}\n\n"
        
        # Add system information
        content += f"System/Subsystem: {doc_metadata.get('system', 'N/A')} / {doc_metadata.get('subsystem', 'N/A')}\n\n"
        
        # Add threat scenarios overview
        sections = tara_data.get("sections", {})
        threat_scenarios = sections.get("threatScenarios", [])
        
        # Handle case where threat_scenarios might not be a list
        if not isinstance(threat_scenarios, list):
            if isinstance(threat_scenarios, dict):
                # If it's a dictionary with scenarios as values
                threat_scenarios = list(threat_scenarios.values())
            else:
                # If it's something else, treat as empty list
                threat_scenarios = []
        
        content += f"Threat Scenarios Overview:\n"
        content += f"Number of Threat Scenarios: {len(threat_scenarios)}\n\n"
        
        # Add security properties - handle different formats
        cs_properties = sections.get("cybersecurityProperties", {})
        if cs_properties:
            content += "Security Properties:\n"
            
            if isinstance(cs_properties, dict):
                # Format 1: Dictionary with property types as keys
                for prop, data in cs_properties.items():
                    if isinstance(data, dict):
                        content += f"- {prop.title()}: {data.get('goal', 'N/A')}\n"
                    elif isinstance(data, list) and data:
                        content += f"- {prop.title()}: {len(data)} items\n"
                    else:
                        content += f"- {prop.title()}\n"
            elif isinstance(cs_properties, list):
                # Format 2: List of property definitions
                for prop in cs_properties:
                    if isinstance(prop, dict):
                        prop_name = prop.get("property", "Unknown")
                        content += f"- {prop_name}\n"
                    else:
                        content += f"- Property item\n"
            
            content += "\n"
        
        # Add threat assessment overview
        threat_assessment = sections.get("threatAssessment", {})
        if isinstance(threat_assessment, dict):
            assessments = threat_assessment.get("threatAssessments", [])
            if isinstance(assessments, list):
                content += f"Threat Assessments: {len(assessments)}\n"
            else:
                content += "Threat Assessments: Available\n"
        elif isinstance(threat_assessment, list):
            content += f"Threat Assessments: {len(threat_assessment)}\n"
        
        return content
    
    def create_cybersecurity_properties_content(self, properties: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for cybersecurity properties section.
        
        Args:
            properties: Cybersecurity properties data
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with cybersecurity properties content
        """
        if not properties:
            return ""
        
        content = "# CYBERSECURITY PROPERTIES\n\n"
        
        # Handle different formats of cybersecurity properties
        if isinstance(properties, dict):
            # Format 1: Dictionary with property types as keys
            for prop, data in properties.items():
                content += f"## {prop.title()}\n\n"
                
                if isinstance(data, dict):
                    # Single property definition
                    content += f"Goal: {data.get('goal', 'N/A')}\n"
                    content += f"Description: {data.get('description', 'N/A')}\n\n"
                elif isinstance(data, list):
                    # List of property goals
                    for item in data:
                        if isinstance(item, dict):
                            item_id = item.get("id", "")
                            description = item.get("description", "N/A")
                            content += f"- {item_id}: {description}\n"
                    content += "\n"
        elif isinstance(properties, list):
            # Format 2: List of property definitions
            for prop in properties:
                if isinstance(prop, dict):
                    prop_name = prop.get("property", "Unknown")
                    description = prop.get("description", "N/A")
                    
                    content += f"## {prop_name}\n\n"
                    content += f"Description: {description}\n\n"
        
        return content
    
    def create_threat_scenario_chunk(self, scenario: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> Document:
        """Create a document chunk for a single threat scenario.
        
        Args:
            scenario: The threat scenario data
            tara_data: The full TARA document data for context
            metadata: Base metadata to extend
            
        Returns:
            Document object with scenario content and metadata
        """
        scenario_id = scenario.get("id", "unknown")
        scenario_title = scenario.get("title", "unknown")
        
        # Create a content string for this scenario
        content = f"# THREAT SCENARIO: {scenario_title}\n\n"
        content += f"ID: {scenario_id}\n"
        content += f"Description: {scenario.get('description', 'N/A')}\n\n"
        
        # Add attack vectors - handle both list and dictionary formats
        attack_vectors = scenario.get("attackVectors", [])
        if attack_vectors:
            content += "## Attack Vectors\n\n"
            
            if isinstance(attack_vectors, list):
                for vector in attack_vectors:
                    if isinstance(vector, dict):
                        # Handle structured attack vector
                        vector_name = vector.get("vector", "unknown")
                        vector_desc = vector.get("description", "N/A")
                        
                        content += f"### {vector_name}\n"
                        content += f"{vector_desc}\n\n"
                    else:
                        # Handle simple string attack vector
                        content += f"- {vector}\n"
            elif isinstance(attack_vectors, dict):
                # Handle dictionary format
                for name, desc in attack_vectors.items():
                    content += f"### {name}\n"
                    content += f"{desc}\n\n"
                    
            content += "\n"
        
        # Add attack steps - handle both list and dictionary formats
        attack_steps = scenario.get("attackSteps", [])
        if attack_steps:
            content += "## Attack Steps\n\n"
            
            if isinstance(attack_steps, list):
                for i, step in enumerate(attack_steps):
                    if isinstance(step, dict):
                        step_num = step.get("step", i+1)
                        step_desc = step.get("description", "N/A")
                        content += f"{step_num}. {step_desc}\n"
                        
                        # Add prerequisites if available
                        prereqs = step.get("prerequisites", [])
                        if prereqs and isinstance(prereqs, list):
                            content += "   Prerequisites:\n"
                            for prereq in prereqs:
                                content += f"   - {prereq}\n"
                        
                        # Add difficulty if available
                        difficulty = step.get("difficulty", "")
                        if difficulty:
                            content += f"   Difficulty: {difficulty}\n"
                    else:
                        # Simple string or number step
                        content += f"{i+1}. {step}\n"
            elif isinstance(attack_steps, dict):
                # Handle dictionary format
                for step_id, step_info in attack_steps.items():
                    if isinstance(step_info, dict):
                        content += f"{step_id}. {step_info.get('description', 'N/A')}\n"
                    else:
                        content += f"{step_id}. {step_info}\n"
                        
            content += "\n"
        
        # Add STPA analysis if available - handle both list and dictionary formats
        stpa = scenario.get("stpaAnalysis", {})
        if stpa and isinstance(stpa, dict):
            content += "## STPA Analysis\n\n"
            
            # Add unsafe control actions - handle both list and dictionary formats
            unsafe_actions = stpa.get("unsafeControlActions", [])
            if unsafe_actions:
                content += "### Unsafe Control Actions\n\n"
                
                if isinstance(unsafe_actions, list):
                    for action in unsafe_actions:
                        if isinstance(action, dict):
                            content += f"Control Action: {action.get('controlAction', 'N/A')}\n"
                            content += f"Hazardous Condition: {action.get('hazardousCondition', 'N/A')}\n"
                            content += f"Hazard Type: {action.get('hazardType', 'N/A')}\n\n"
                        else:
                            # Simple string
                            content += f"- {action}\n"
                elif isinstance(unsafe_actions, dict):
                    for action_id, action_info in unsafe_actions.items():
                        content += f"Control Action: {action_id}\n"
                        if isinstance(action_info, dict):
                            content += f"Details: {action_info.get('description', 'N/A')}\n\n"
                        else:
                            content += f"Details: {action_info}\n\n"
            
            # Add control flaws - handle both list and dictionary formats
            control_flaws = stpa.get("controlFlaws", [])
            if control_flaws:
                content += "### Control Flaws\n\n"
                
                if isinstance(control_flaws, list):
                    for flaw in control_flaws:
                        if isinstance(flaw, dict):
                            content += f"Flaw: {flaw.get('flaw', 'N/A')}\n"
                            content += f"Description: {flaw.get('description', 'N/A')}\n\n"
                        else:
                            # Simple string
                            content += f"- {flaw}\n"
                elif isinstance(control_flaws, dict):
                    for flaw_id, flaw_info in control_flaws.items():
                        content += f"Flaw: {flaw_id}\n"
                        if isinstance(flaw_info, dict):
                            content += f"Description: {flaw_info.get('description', 'N/A')}\n\n"
                        else:
                            content += f"Description: {flaw_info}\n\n"
                            
            # Handle controller constraints if present
            controller_constraints = stpa.get("controllerConstraints", [])
            if controller_constraints:
                content += "### Controller Constraints\n\n"
                
                if isinstance(controller_constraints, list):
                    for constraint in controller_constraints:
                        if isinstance(constraint, dict):
                            content += f"- {constraint.get('description', 'N/A')}\n"
                        else:
                            content += f"- {constraint}\n"
                elif isinstance(controller_constraints, dict):
                    for constraint_id, constraint_info in controller_constraints.items():
                        if isinstance(constraint_info, dict):
                            content += f"- {constraint_id}: {constraint_info.get('description', 'N/A')}\n"
                        else:
                            content += f"- {constraint_id}: {constraint_info}\n"
        
        # Add impact reference and security property violation with safe access
        content += "## Impact and Security Property References\n\n"
        
        # Safely handle all fields
        impact_ref = scenario.get("impactReference", "N/A")
        sec_property = scenario.get("securityPropertyViolated", "N/A")
        cs_goal = scenario.get("cybersecurityGoalViolated", "N/A")
        
        content += f"Impact Reference: {impact_ref}\n"
        content += f"Security Property Violated: {sec_property}\n"
        content += f"Cybersecurity Goal Violated: {cs_goal}\n"
        
        # Create scenario-specific metadata with safe access
        scenario_metadata = {
            **metadata,
            "content_section": "threat_scenario",
            "threat_id": scenario_id,
            "threat_title": scenario_title,
            "security_property_violated": sec_property,
            "cybersecurity_goal_violated": cs_goal,
            "impact_reference": impact_ref
        }
        
        return Document(
            page_content=content,
            metadata=scenario_metadata
        )
    
    def create_threat_methodology_content(self, methodology: Dict[str, Any], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for threat assessment methodology section.
        
        Args:
            methodology: Threat assessment methodology data
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with threat methodology content
        """
        if not methodology:
            return ""
        
        content = "# THREAT ASSESSMENT METHODOLOGY\n\n"
        
        # Handle different formats of methodology
        if isinstance(methodology, dict):
            content += f"Methodology Name: {methodology.get('name', 'N/A')}\n"
            content += f"Description: {methodology.get('description', 'N/A')}\n\n"
            
            # Add feasibility levels
            feasibility_levels = methodology.get("feasibilityLevels", [])
            if isinstance(feasibility_levels, list) and feasibility_levels:
                content += "## Feasibility Levels\n\n"
                for level in feasibility_levels:
                    if isinstance(level, dict):
                        level_name = level.get("level", "unknown")
                        level_desc = level.get("description", "N/A")
                        content += f"- {level_name}: {level_desc}\n"
                    else:
                        content += f"- {level}\n"
                content += "\n"
            
            # Add additional methodology information if available
            for key, value in methodology.items():
                if key not in ['name', 'description', 'feasibilityLevels'] and value:
                    if isinstance(value, list):
                        content += f"## {key.replace('_', ' ').title()}\n\n"
                        for item in value:
                            if isinstance(item, dict):
                                item_name = next(iter(item.values()), "unknown")
                                content += f"- {item_name}\n"
                            else:
                                content += f"- {item}\n"
                        content += "\n"
                    elif isinstance(value, dict):
                        content += f"## {key.replace('_', ' ').title()}\n\n"
                        for sub_key, sub_value in value.items():
                            content += f"- {sub_key}: {sub_value}\n"
                        content += "\n"
        elif isinstance(methodology, str):
            # Handle case where methodology is just a string
            content += methodology + "\n\n"
        elif isinstance(methodology, list):
            # Handle case where methodology is a list
            content += "## Methodology Elements\n\n"
            for item in methodology:
                if isinstance(item, dict):
                    item_name = next(iter(item.values()), "unknown")
                    content += f"- {item_name}\n"
                else:
                    content += f"- {item}\n"
            content += "\n"
        
        return content
    
    def create_threat_assessments_content(self, assessments: List[Dict[str, Any]], tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content for threat assessments section.
        
        Args:
            assessments: List of threat assessments
            tara_data: The full TARA document data for context
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with threat assessments content
        """
        if not assessments:
            return ""
        
        content = "# THREAT ASSESSMENTS\n\n"
        
        # Handle different formats of assessments
        if isinstance(assessments, list):
            for assessment in assessments:
                if isinstance(assessment, dict):
                    # Get threat ID with fallbacks
                    threat_id = assessment.get("threatId", "unknown")
                    
                    # Check if it's a list (some documents use lists for IDs)
                    if isinstance(threat_id, list) and threat_id:
                        threat_id = threat_id[0]  # Use the first ID
                    
                    content += f"## Threat Assessment for {threat_id}\n\n"
                    
                    # Handle attack vector complexity with type checking
                    attack_vector = assessment.get("attackVectorComplexity", {})
                    if isinstance(attack_vector, dict):
                        content += "### Attack Vector Complexity\n\n"
                        content += f"Attack Vector: {attack_vector.get('attackVector', 'N/A')}\n"
                        content += f"Description: {attack_vector.get('description', 'N/A')}\n"
                        content += f"Rating: {attack_vector.get('rating', 'N/A')}\n\n"
                    elif isinstance(attack_vector, str):
                        content += "### Attack Vector Complexity\n\n"
                        content += f"Rating: {attack_vector}\n\n"
                    
                    # Handle attack complexity with type checking
                    attack_complexity = assessment.get("attackComplexity", {})
                    if isinstance(attack_complexity, dict):
                        content += "### Attack Complexity\n\n"
                        content += f"Description: {attack_complexity.get('description', 'N/A')}\n"
                        content += f"Rating: {attack_complexity.get('rating', 'N/A')}\n\n"
                    elif isinstance(attack_complexity, str):
                        content += "### Attack Complexity\n\n"
                        content += f"Rating: {attack_complexity}\n\n"
                    
                    # Handle privileges required with type checking
                    privileges = assessment.get("privilegesRequired", {})
                    if isinstance(privileges, dict):
                        content += "### Privileges Required\n\n"
                        content += f"Description: {privileges.get('description', 'N/A')}\n"
                        content += f"Rating: {privileges.get('rating', 'N/A')}\n\n"
                    elif isinstance(privileges, str):
                        content += "### Privileges Required\n\n"
                        content += f"Rating: {privileges}\n\n"
                    
                    # Handle user interaction with type checking
                    user_interaction = assessment.get("userInteraction", {})
                    if isinstance(user_interaction, dict):
                        content += "### User Interaction\n\n"
                        content += f"Description: {user_interaction.get('description', 'N/A')}\n"
                        content += f"Rating: {user_interaction.get('rating', 'N/A')}\n\n"
                    elif isinstance(user_interaction, str):
                        content += "### User Interaction\n\n"
                        content += f"Rating: {user_interaction}\n\n"
                    
                    # Handle overall feasibility with type checking
                    overall_feasibility = assessment.get("overallFeasibility", "N/A")
                    justification = assessment.get("justification", "N/A")
                    
                    content += "### Overall Feasibility\n\n"
                    content += f"Rating: {overall_feasibility}\n"
                    content += f"Justification: {justification}\n"
                elif isinstance(assessment, str):
                    # Handle the case where the assessment itself is a string
                    content += f"## Assessment\n\n"
                    content += f"{assessment}\n\n"
        elif isinstance(assessments, dict):
            # Handle the case where assessments is a dictionary mapping threat IDs to assessments
            for threat_id, assessment in assessments.items():
                content += f"## Threat Assessment for {threat_id}\n\n"
                
                if isinstance(assessment, dict):
                    # Add assessment details similar to the list case
                    content += f"Overall Feasibility: {assessment.get('overallFeasibility', 'N/A')}\n"
                    content += f"Justification: {assessment.get('justification', 'N/A')}\n\n"
                else:
                    # Simple string or other type
                    content += f"{assessment}\n\n"
        elif isinstance(assessments, str):
            # Handle the case where the entire assessments is a string
            content += assessments + "\n\n"
        
        return content
    
    def create_key_terms_content(self, tara_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create content with key terms and synonyms to improve search.
        
        Args:
            tara_data: The parsed TARA JSON data
            metadata: Metadata associated with the document
            
        Returns:
            Formatted string with key terms content
        """
        content = "# KEY TERMS AND COMMON SYNONYMS\n\n"
        
        # Add document and system info for context
        doc_metadata = tara_data.get("metadata", {})
        content += f"Document: {doc_metadata.get('documentId', 'N/A')}\n"
        content += f"System/Subsystem: {doc_metadata.get('system', 'N/A')} / {doc_metadata.get('subsystem', 'N/A')}\n\n"
        
        # Add generic TARA-related terms to improve retrievability
        content += "This document contains information about:\n"
        content += "- Threat Analysis and Risk Assessment (TARA)\n"
        content += f"- TARA Phase: {metadata.get('tara_phase', 'unknown').title()}\n"
        content += f"- Standard: {doc_metadata.get('standard', 'N/A')}\n\n"
        
        # Add phase-specific key terms
        content += "Document-specific key terms:\n"
        
        tara_phase = metadata.get('tara_phase', '')
        sections = tara_data.get("sections", {})
        
        if tara_phase == "impact-analysis":
            # Add damage scenario IDs and titles
            scenarios = sections.get("damageScenarios", [])
            if isinstance(scenarios, list):
                for scenario in scenarios:
                    if isinstance(scenario, dict):
                        scenario_id = scenario.get('id', '')
                        scenario_title = scenario.get('title', '')
                        if scenario_id or scenario_title:
                            content += f"- Damage Scenario: {scenario_id} - {scenario_title}\n"
            
            # Add cybersecurity goals
            goals = sections.get("cybersecurityGoals", [])
            if isinstance(goals, list):
                for goal in goals:
                    if isinstance(goal, dict):
                        goal_id = goal.get('id', '')
                        goal_title = goal.get('title', '')
                        if goal_id or goal_title:
                            content += f"- Cybersecurity Goal: {goal_id} - {goal_title}\n"
        
        elif tara_phase == "risk-assessment":
            # Add risk IDs and titles - handle different structures
            risks = []
            risk_assessment = sections.get("riskAssessment", {})
            
            if isinstance(risk_assessment, dict):
                risks = risk_assessment.get("risks", [])
            elif isinstance(risk_assessment, list):
                risks = risk_assessment
                
            # Also check alternate field name "riskAssessments"
            if not risks and isinstance(sections.get("riskAssessments"), list):
                risks = sections.get("riskAssessments", [])
                
            if isinstance(risks, list):
                for risk in risks:
                    if isinstance(risk, dict):
                        risk_id = risk.get('id', '')
                        risk_title = risk.get('title', '')
                        if risk_id or risk_title:
                            content += f"- Risk: {risk_id} - {risk_title}\n"
            
            # Add security control IDs and titles - handle different structures
            controls = []
            mitigation_strategy = sections.get("mitigationStrategy", {})
            
            if isinstance(mitigation_strategy, dict):
                controls = mitigation_strategy.get("securityControls", [])
            elif isinstance(mitigation_strategy, list):
                controls = mitigation_strategy
                
            # Check relationship mapping for controls
            relationship_mapping = tara_data.get("relationshipMapping", {})
            if isinstance(relationship_mapping, dict):
                control_mapping = relationship_mapping.get("mitigationToControlMapping", [])
                if isinstance(control_mapping, list) and not controls:
                    controls = control_mapping
            
            if isinstance(controls, list):
                for control in controls:
                    if isinstance(control, dict):
                        control_id = control.get('id', control.get('securityControlId', ''))
                        control_title = control.get('title', control.get('name', ''))
                        if control_id or control_title:
                            content += f"- Security Control: {control_id} - {control_title}\n"
            elif isinstance(controls, dict):
                for control_id, control in controls.items():
                    if isinstance(control, dict):
                        control_title = control.get('title', control.get('name', ''))
                        content += f"- Security Control: {control_id} - {control_title}\n"
                    else:
                        content += f"- Security Control: {control_id}\n"
        
        elif tara_phase == "threat-scenarios":
            # Add threat scenario IDs and titles
            scenarios = sections.get("threatScenarios", [])
            if isinstance(scenarios, list):
                for scenario in scenarios:
                    if isinstance(scenario, dict):
                        scenario_id = scenario.get('id', '')
                        scenario_title = scenario.get('title', '')
                        if scenario_id or scenario_title:
                            content += f"- Threat Scenario: {scenario_id} - {scenario_title}\n"
            elif isinstance(scenarios, dict):
                for scenario_id, scenario in scenarios.items():
                    if isinstance(scenario, dict):
                        scenario_title = scenario.get('title', '')
                        content += f"- Threat Scenario: {scenario_id} - {scenario_title}\n"
                    else:
                        content += f"- Threat Scenario: {scenario_id}\n"
            
            # Add attack vectors
            attack_vectors = set()
            
            # Only attempt to iterate if scenarios is a list
            if isinstance(scenarios, list):
                for scenario in scenarios:
                    if not isinstance(scenario, dict):
                        continue
                        
                    vectors = scenario.get("attackVectors", [])
                    if isinstance(vectors, list):
                        for vector in vectors:
                            if isinstance(vector, dict):
                                vector_name = vector.get("vector", "")
                                if vector_name:
                                    attack_vectors.add(vector_name)
                            elif isinstance(vector, str):
                                attack_vectors.add(vector)
            
            for vector in attack_vectors:
                content += f"- Attack Vector: {vector}\n"
                
        # Add key terms from dedicated keyTerms section if available
        key_terms = tara_data.get("keyTerms", {})
        if isinstance(key_terms, dict):
            content += "\nGlossary of terms used in this document:\n"
            for term, definition in key_terms.items():
                content += f"- {term}: {definition}\n"
                
        # Add search terms if available
        search_terms = tara_data.get("searchTerms", [])
        if isinstance(search_terms, list) and search_terms:
            content += "\nSearch terms related to this document:\n"
            for term in search_terms:
                if isinstance(term, str):
                    content += f"- {term}\n"
        
        return content 