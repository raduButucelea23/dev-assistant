#!/usr/bin/env python3
"""
Startup script for auto-dev assistant.
Handles database initialization before launching Streamlit.
"""

import os
import sys
import time
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to Python path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(script_path)
app_dir = os.path.join(project_root, "app")
sys.path.append(project_root)

# Set up logging for startup process
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STARTUP - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_database():
    """
    Initialize the ChromaDB database by processing documents.
    Returns True if successful, False otherwise.
    """
    try:
        logger.info("=== DATABASE INITIALIZATION START ===")
        
        # Import required modules after path setup
        from dotenv import load_dotenv
        from app.embeddings import DBManager
        from app.utils.model_config import get_model_config
        from langchain_core.documents.base import Document
        
        # Import document processors
        from app.document_processors import (
            PDFProcessor, JSONProcessor, MarkdownProcessor, 
            ExcelProcessor, CSVProcessor, ARXMLProcessor, 
            ODXProcessor, FMEAProcessor, SignalDatabaseProcessor, 
            TARAProcessor
        )
        
        # Load environment variables
        load_dotenv()
        
        # Get model configuration
        model_config = get_model_config()
        
        # Initialize DBManager
        db_manager = DBManager(
            persist_directory=os.path.join(app_dir, "chroma_db"),
            embedding_provider=model_config["embedding_provider"],
            embedding_model=model_config["embedding_model"]
        )
        
        logger.info("Attempting to load existing database...")
        vector_db = db_manager.initialize_db()
        
        if vector_db:
            logger.info("✅ SUCCESS: Existing database found and loaded successfully")
            return True
        
        logger.info("No existing database found - creating new database...")
        
        # Process documents and create database
        data_dir = os.path.join(project_root, "data")
        logger.info(f"Looking for documents in: {data_dir}")
        
        # Define semantic domains
        domains = ["requirements", "catalogues", "standards"]
        logger.info(f"Processing domains: {domains}")
        
        # Process documents from each domain
        all_documents = []
        files_processed = 0
        
        for domain in domains:
            domain_dir = os.path.join(data_dir, domain)
            if not os.path.exists(domain_dir):
                logger.warning(f"Domain directory not found: {domain_dir}")
                continue
            
            logger.info(f"Processing domain directory: {domain_dir}")
            domain_files_processed = process_directory(domain_dir, domain, all_documents)
            files_processed += domain_files_processed
            logger.info(f"Processed {domain_files_processed} files in {domain} domain")
        
        logger.info(f"Total files processed: {files_processed}")
        logger.info(f"Total document chunks created: {len(all_documents)}")
        
        # Create database from documents
        if all_documents:
            logger.info("Creating database from processed documents...")
            vector_db, unique_doc_count = db_manager.create_db_from_documents(all_documents)
            
            if vector_db:
                logger.info(f"✅ SUCCESS: Database created with {unique_doc_count} unique documents")
                return True
            else:
                logger.error("❌ FAILURE: Database creation failed")
                return False
        else:
            logger.error("❌ FAILURE: No documents found to process")
            return False
            
    except Exception as e:
        logger.error(f"❌ FAILURE: Database initialization failed with error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def process_directory(directory_path, domain, all_documents):
    """
    Process all files in a directory and add documents to the list.
    Returns the number of files processed.
    """
    files_processed = 0
    
    try:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    processor = get_processor_for_file(file_path, domain)
                    if processor:
                        logger.info(f"Processing file: {file_path}")
                        documents = processor.process_file(file_path)  # FIXED: Changed from process() to process_file()
                        if documents:
                            all_documents.extend(documents)
                            files_processed += 1
                            logger.info(f"Added {len(documents)} chunks from {file}")
                        else:
                            logger.warning(f"No documents extracted from {file}")
                    else:
                        logger.info(f"No processor available for file: {file}")
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {str(e)}")
    
    return files_processed

def get_processor_for_file(file_path, domain):
    """
    Get the appropriate processor for a file based on its extension.
    """
    from app.document_processors import (
        PDFProcessor, JSONProcessor, MarkdownProcessor, 
        ExcelProcessor, CSVProcessor, ARXMLProcessor, 
        ODXProcessor, FMEAProcessor, SignalDatabaseProcessor, 
        TARAProcessor
    )
    
    file_extension = Path(file_path).suffix.lower()
    filename = Path(file_path).name.lower()
    
    # Map file extensions to processors
    if file_extension == '.pdf':
        return PDFProcessor(domain=domain)
    elif file_extension == '.json':
        if 'fmea' in filename:
            return FMEAProcessor(domain=domain)
        elif 'tara' in filename or 'threat' in filename or 'risk' in filename:
            return TARAProcessor(domain=domain)
        elif 'signal' in filename or 'database' in filename:
            return SignalDatabaseProcessor(domain=domain)
        else:
            return JSONProcessor(domain=domain)
    elif file_extension == '.md':
        return MarkdownProcessor(domain=domain)
    elif file_extension in ['.xlsx', '.xls']:
        return ExcelProcessor(domain=domain)
    elif file_extension == '.csv':
        return CSVProcessor(domain=domain)
    elif file_extension == '.arxml':
        return ARXMLProcessor(domain=domain)
    elif file_extension in ['.odx', '.odx-c']:
        return ODXProcessor(domain=domain)
    else:
        return None

def start_streamlit():
    """
    Start the Streamlit application.
    """
    logger.info("Starting Streamlit application...")
    
    try:
        # Start Streamlit with the same parameters as in Dockerfile
        cmd = [
            sys.executable, "-m", "streamlit", "run", "app/main.py",
            "--server.address=0.0.0.0",
            "--server.port=8501", 
            "--server.headless=true",
            "--browser.serverAddress=localhost",
            "--browser.serverPort=8502"
        ]
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        # Use exec to replace the current process with Streamlit
        os.execvp(sys.executable, cmd)
        
    except Exception as e:
        logger.error(f"Failed to start Streamlit: {str(e)}")
        sys.exit(1)

def health_check():
    """
    Simple health check endpoint for Docker.
    Returns 0 if database is ready, 1 otherwise.
    """
    try:
        from app.embeddings import DBManager
        from app.utils.model_config import get_model_config
        
        model_config = get_model_config()
        db_manager = DBManager(
            persist_directory=os.path.join(app_dir, "chroma_db"),
            embedding_provider=model_config["embedding_provider"],
            embedding_model=model_config["embedding_model"]
        )
        
        vector_db = db_manager.initialize_db()
        if vector_db:
            print("Database is ready")
            return 0
        else:
            print("Database not ready")
            return 1
            
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return 1

def main():
    """
    Main startup function.
    """
    # Check if this is a health check call
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        sys.exit(health_check())
    
    logger.info("🚀 Starting auto-dev assistant...")
    
    # Initialize database
    if initialize_database():
        logger.info("✅ Database initialization completed successfully")
        
        # Add a small delay to ensure everything is settled
        time.sleep(2)
        
        # Start Streamlit
        start_streamlit()
    else:
        logger.error("❌ Database initialization failed - cannot start application")
        sys.exit(1)

if __name__ == "__main__":
    main() 