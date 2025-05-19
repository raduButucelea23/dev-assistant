import os
import json
from typing import List, Dict, Any
from langchain_core.documents.base import Document
import re

# Try relative imports first
try:
    from .json_processor import JSONProcessor
    from ..utils.text_processing import create_semantic_chunks
except ImportError:
    # Fall back to absolute imports if relative imports fail
    from app.document_processors.json_processor import JSONProcessor
    from app.utils.text_processing import create_semantic_chunks


class SignalDatabaseProcessor(JSONProcessor):
    """Processor for Signal Database JSON documents.
    
    Handles loading and processing signal database files, with specialized
    handling for the signal array structure.
    """
    
    def __init__(self, domain: str = "signal"):
        """Initialize the Signal Database processor.
        
        Args:
            domain: The semantic domain for the signal database documents
        """
        super().__init__(domain)
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process a signal database file and return a list of Document objects.
        
        This method extracts signal information and creates semantic chunks
        appropriate for signal database retrieval.
        
        Args:
            file_path: Path to the signal database JSON file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Extract the filename from the path
        filename = os.path.basename(file_path)
        
        try:
            # Load the JSON file
            with open(file_path, 'r') as f:
                json_content = json.load(f)
            
            # Extract formatted content for signal database
            formatted_content = self.extract_signal_database_content(json_content)
            
            # Extract metadata for signal database
            metadata = self.extract_signal_database_metadata(json_content)
            
            # Add source information to metadata
            metadata["source"] = filename
            metadata["source_type"] = "signal_database"
            metadata["domain"] = self.domain
            
            # Create documents from the formatted content
            documents = self.create_signal_database_documents(formatted_content, metadata, json_content)
            
            print(f"DEBUG - SignalDatabaseProcessor: Created {len(documents)} documents from signal database")
            return documents
        
        except Exception as e:
            # Return a single document with error information
            error_doc = Document(
                page_content=f"Error processing signal database file: {str(e)}",
                metadata={
                    "source": filename,
                    "source_type": "signal_database",
                    "domain": self.domain,
                    "error": str(e)
                }
            )
            return [error_doc]
    
    def extract_signal_database_content(self, json_data: Dict[str, Any]) -> str:
        """Extract readable content from signal database JSON structure.
        
        Args:
            json_data: The parsed JSON data
            
        Returns:
            Formatted string representation of the signal database content
        """
        # Start with a summary section
        content = "# SIGNAL DATABASE SUMMARY\n"
        
        # Get database info
        db_version = json_data.get("database_info", {}).get("version", "Unknown")
        content += f"Signal Database Version: {db_version}\n"
        
        # Get signals
        signals = json_data.get("signals", [])
        content += f"Total Signal Count: {len(signals)}\n\n"
        
        # Add signal sources summary
        signal_sources = set()
        signal_targets = set()
        bus_types = set()
        
        for signal in signals:
            if "source" in signal:
                signal_sources.add(signal["source"])
            if "targets" in signal and isinstance(signal["targets"], list):
                for target in signal["targets"]:
                    signal_targets.add(target)
            if "bus_type" in signal:
                bus_types.add(signal["bus_type"])
        
        content += f"Signal Sources: {', '.join(sorted(signal_sources))}\n"
        content += f"Signal Targets: {', '.join(sorted(signal_targets))}\n"
        content += f"Bus Types: {', '.join(sorted(bus_types))}\n"
        
        # Add a section with all signals
        content += "\n# SIGNALS\n"
        
        # Format each signal
        for signal in signals:
            name = signal.get("name", "Unnamed Signal")
            content += f"## {name}\n"
            content += f"Description: {signal.get('description', 'No description')}\n"
            content += f"Bus Type: {signal.get('bus_type', 'Unknown')}\n"
            content += f"Source: {signal.get('source', 'Unknown')}\n"
            
            # Format targets as a list
            targets = signal.get("targets", [])
            if isinstance(targets, list) and targets:
                content += f"Targets: {', '.join(targets)}\n"
            else:
                content += "Targets: None\n"
            
            content += f"Value Description: {signal.get('value_description', 'Unknown')}\n"
            
            # Format cycle time
            cycle_time = signal.get("cycle_time_ms")
            if cycle_time is not None:
                content += f"Cycle Time: {cycle_time} ms\n"
            else:
                content += "Cycle Time: Event-triggered (no fixed cycle)\n"
            
            content += "\n"
        
        return content
    
    def extract_signal_database_metadata(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from signal database JSON structure.
        
        Args:
            json_data: The parsed JSON data
            
        Returns:
            Dictionary of metadata for the signal database
        """
        # Basic metadata
        metadata = {
            "database_version": json_data.get("database_info", {}).get("version", "Unknown"),
            "signal_count": len(json_data.get("signals", [])),
        }
        
        # Extract signal names for search
        signal_names = []
        signal_sources = []
        signal_targets = []
        signal_bus_types = []
        
        for signal in json_data.get("signals", []):
            if "name" in signal:
                signal_names.append(signal["name"])
            if "source" in signal:
                signal_sources.append(signal["source"])
            if "targets" in signal and isinstance(signal["targets"], list):
                for target in signal["targets"]:
                    signal_targets.append(target)
            if "bus_type" in signal:
                signal_bus_types.append(signal["bus_type"])
        
        # Add to metadata (limit string length for large databases)
        metadata["signal_names"] = ", ".join(signal_names)[:1000]
        metadata["signal_sources"] = ", ".join(list(set(signal_sources)))
        metadata["signal_targets"] = ", ".join(list(set(signal_targets)))
        metadata["signal_bus_types"] = ", ".join(list(set(signal_bus_types)))
        
        return metadata
    
    def create_signal_database_documents(
        self, formatted_content: str, metadata: Dict[str, Any], json_data: Dict[str, Any]
    ) -> List[Document]:
        """Create semantic documents for the signal database.
        
        This creates multiple documents:
        - One overview document with database summary
        - Individual documents for each signal for targeted retrieval
        
        Args:
            formatted_content: The formatted content
            metadata: The database metadata
            json_data: The original JSON data
            
        Returns:
            List of Document objects
        """
        documents = []
        
        # Extract the summary section for context
        summary_pattern = r'# SIGNAL DATABASE SUMMARY(.*?)(?=\n# |$)'
        summary_match = re.search(summary_pattern, formatted_content, re.DOTALL)
        summary_content = ""
        if summary_match:
            summary_content = "# SIGNAL DATABASE SUMMARY" + summary_match.group(1)
        
        # Create a document for the overall database summary
        summary_doc = Document(
            page_content=summary_content,
            metadata={**metadata, "content_section": "database_summary"}
        )
        documents.append(summary_doc)
        
        # Create individual documents for each signal
        signals = json_data.get("signals", [])
        for i, signal in enumerate(signals):
            signal_name = signal.get("name", f"Signal_{i}")
            
            # Create signal-specific content
            signal_content = f"{summary_content}\n\n# SIGNAL: {signal_name}\n"
            signal_content += f"Description: {signal.get('description', 'No description')}\n"
            signal_content += f"Bus Type: {signal.get('bus_type', 'Unknown')}\n"
            signal_content += f"Source: {signal.get('source', 'Unknown')}\n"
            
            # Format targets
            targets = signal.get("targets", [])
            if isinstance(targets, list) and targets:
                signal_content += f"Targets: {', '.join(targets)}\n"
            else:
                signal_content += "Targets: None\n"
            
            signal_content += f"Value Description: {signal.get('value_description', 'Unknown')}\n"
            
            # Format cycle time
            cycle_time = signal.get("cycle_time_ms")
            if cycle_time is not None:
                signal_content += f"Cycle Time: {cycle_time} ms\n"
            else:
                signal_content += "Cycle Time: Event-triggered (no fixed cycle)\n"
            
            # Create signal-specific metadata
            signal_metadata = {
                **metadata,
                "content_section": "signal_details",
                "signal_name": signal_name,
                "signal_source": signal.get("source", ""),
                "signal_bus_type": signal.get("bus_type", ""),
            }
            
            # Create the document
            signal_doc = Document(
                page_content=signal_content,
                metadata=signal_metadata
            )
            documents.append(signal_doc)
        
        return documents 