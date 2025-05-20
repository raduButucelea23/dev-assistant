import os
import sys
import shutil
import time
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# Add project root to Python path when run directly
if __name__ == "__main__":
    script_path = os.path.abspath(__file__)
    app_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(app_dir)
    sys.path.append(project_root)

# Function to restart the Streamlit app completely
def restart_app():
    """Completely restart the Streamlit application by terminating the current process
    and starting a new one"""
    # Get the path to the current Python executable (already has the conda env activated)
    python_executable = sys.executable
    
    # Get the path to the current script
    script_path = os.path.abspath(__file__)
    
    print(f"Restarting app using: {python_executable} -m streamlit run {script_path}")
    
    try:
        # Start a new process directly with the current Python executable
        # which already has the conda environment activated
        subprocess.Popen([python_executable, "-m", "streamlit", "run", script_path])
        
        # Add a sleep to ensure the new process has time to start
        print("Waiting for new process to start...")
        time.sleep(2)
        
        # Exit the current process with success code
        print("Exiting current process...")
        os._exit(0)
    except Exception as e:
        print(f"Error in restart_app: {str(e)}")
        # If something goes wrong, we should still exit
        os._exit(1)

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd

# Import HuggingFace client
from app.api.huggingface_client import get_huggingface_client

# Import model configuration utility
from app.utils.model_config import get_model_config, EMBEDDING_PROVIDERS, LLM_PROVIDERS

# Import the generation parameters configuration
from app.utils.generation_config import get_config_manager, get_generation_params

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress specific Streamlit watcher error messages
logging.getLogger("streamlit.watcher.local_sources_watcher").setLevel(logging.ERROR)

# Load environment variables from .env file
load_dotenv()

# --- Database Management ---
from app.embeddings import DBManager

# --- Document Processing ---
from app.document_processors import PDFProcessor, JSONProcessor, MarkdownProcessor, ExcelProcessor, CSVProcessor, ARXMLProcessor, ODXProcessor, FMEAProcessor, SignalDatabaseProcessor, TARAProcessor
from langchain_core.documents.base import Document

# --- Retrieval Functions ---
from app.retrieval.query_preprocessing import preprocess_query
from app.retrieval.hybrid_search import hybrid_search

# --- API Functions ---
from app.api.document_tracing import document_tracing_ui, format_trace_info

# --- Initialize Session State Variables from Configuration ---
# Get model configuration from environment or config file
model_config = get_model_config()

# Set session state variables for models
if "embedding_provider" not in st.session_state:
    st.session_state["embedding_provider"] = model_config["embedding_provider"]

if "embedding_model" not in st.session_state:
    st.session_state["embedding_model"] = model_config["embedding_model"]

if "llm_provider" not in st.session_state:
    st.session_state["llm_provider"] = model_config["llm_provider"]

if "llm_model" not in st.session_state:
    st.session_state["llm_model"] = model_config["llm_model"]
    
# --- Streamlit UI Configuration ---
# Get absolute path to the images directory for favicon
script_path = os.path.abspath(__file__)
app_dir = os.path.dirname(script_path)
project_root = os.path.dirname(app_dir)
favicon_path = os.path.join(project_root, "images", "logo_2.png")

# This must be the first Streamlit command in the script
st.set_page_config(page_title="auto-dev-assistant", page_icon=favicon_path, layout="wide")

# Apply Comic Sans font to the entire app
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Comic+Neue:wght@300;400;700&display=swap');
    
    * {
        font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif !important;
        color: black;
    }
    
    h1 {
        font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif !important;
        font-weight: 700;
    }
    
    h2, h3 {
        font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif !important;
        font-weight: 700;
    }
    
    p {
        font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif !important;
        font-size: 1.1em;
    }
    
    .stTextInput, .stTextArea, .stButton>button {
        font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif !important;
    }
    
    .streamlit-expanderHeader {
        font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif !important;
    }
    
    .stChatInputContainer {
        border-radius: 15px;
    }
    
    .stChatMessage {
        border-radius: 15px;
    }
    
    /* Custom color scheme with white background */
    .main {
        background-color: white;
    }
    
    .stApp {
        background-color: white;
    }
    
    .css-1v3fvcr {
        background-color: white;
    }
    
    .title-container h1 {
        font-size: 2.5rem;
    }
    
    .title-container p {
        font-size: 1.2rem;
    }
    
    /* Custom styling for messages */
    .user-message {
        background-color: #F5F5F5 !important; /* Light grey background */
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
    }
    
    .assistant-message {
        background-color: transparent !important; /* No background color */
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Chat History ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- Header with Logo & Title ---
# Use the already defined paths for images
logo_path = os.path.join(project_root, "images", "logo.jpg")

# Create a two-column layout for the header
col1, col2, col3 = st.columns([1, 4, 1])

# Display logo in first column if it exists
if os.path.exists(logo_path):
    with col1:
        st.image(logo_path, width=180)

# Display title text in second column
with col2:
    st.markdown("""
        <div class='title-container' style='text-align: left; padding-top: 20px;'>
            <h1>auto-dev-assistant</h1>
            <p>AI-powered assistant for automotive development documentation</p>
        </div>
    """, unsafe_allow_html=True)

# Add settings and clear DB buttons in the third column
with col3:
    # Custom CSS for buttons that matches the UI style
    st.markdown("""
        <style>
        .config-btn {
            font-size: 0.9rem;
            padding: 0.3rem 0.6rem;
            border-radius: 5px;
            background-color: #FFE5D9;
            color: #333;
            border: 1px solid #ccc;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 10px;
            width: 100%;
            text-align: center;
            font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif;
        }
        .config-btn:hover {
            background-color: #D1E8E2;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Clear DB button
    if st.button("🗑️ Clear DB", key="clear_db_button", help="Clear the database and log files"):
        try:
            # Define the paths to clear
            chroma_db_dir = os.path.join(app_dir, "chroma_db")
            embeddings_log_dir = os.path.join(app_dir, "embeddings", "log")
            
            # Make sure we have necessary permissions
            def ensure_directory_permissions(directory):
                if os.path.exists(directory):
                    # First try to ensure write permissions
                    try:
                        print(f"Setting permissions on {directory}")
                        os.chmod(directory, 0o755)  # rwxr-xr-x
                        
                        # On Unix/Mac, try to ensure ownership
                        if os.name != 'nt':  # Not Windows
                            try:
                                uid = os.getuid()
                                gid = os.getgid()
                                os.chown(directory, uid, gid)
                            except Exception as owner_err:
                                print(f"Could not set ownership: {str(owner_err)}")
                    except Exception as perm_err:
                        print(f"Could not set permissions: {str(perm_err)}")
            
            # Ensure permissions before deleting
            ensure_directory_permissions(chroma_db_dir)
            ensure_directory_permissions(embeddings_log_dir)
            
            # Clean up tracking index to avoid issues with persistence
            tracking_dir = os.path.join(chroma_db_dir, "document_tracking")
            if os.path.exists(tracking_dir):
                print(f"Cleaning tracking directory: {tracking_dir}")
                ensure_directory_permissions(tracking_dir)
                for item in os.listdir(tracking_dir):
                    item_path = os.path.join(tracking_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.unlink(item_path)
                    except Exception as e:
                        print(f"Error removing file {item_path}: {e}")
            
            # Delete the chroma_db directory
            if os.path.exists(chroma_db_dir):
                try:
                    print(f"Deleting database directory: {chroma_db_dir}")
                    shutil.rmtree(chroma_db_dir)
                except Exception as e:
                    print(f"Error removing directory {chroma_db_dir}: {e}")
                    # Try item by item deletion as fallback
                    for item in os.listdir(chroma_db_dir):
                        item_path = os.path.join(chroma_db_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except Exception as e:
                            print(f"Error removing {item_path}: {e}")
            
            # Delete the embeddings/log directory
            if os.path.exists(embeddings_log_dir):
                print(f"Deleting log directory: {embeddings_log_dir}")
                shutil.rmtree(embeddings_log_dir, ignore_errors=True)
            
            # Clear session state to force DB reinitialization
            if "vector_db" in st.session_state:
                del st.session_state["vector_db"]
                
            # Show success message with improved explanation
            st.success("✅ Database and logs cleared successfully. Restarting the application to rebuild the database...")
            
            # Add a slightly longer delay to ensure the success message is displayed
            time.sleep(1.5)
            
            # Call the restart function instead of just rerunning
            restart_app()
                
        except Exception as e:
            st.error(f"❌ Error clearing database: {str(e)}")
            st.info("Please try again or manually delete the app/chroma_db directory")
    
    # Model Config button
    if st.button("⚙️ Model Config", key="model_config_button", help="Configure models"):
        st.session_state["show_model_settings"] = not st.session_state.get("show_model_settings", False)
        st.rerun()

# Add model settings sidebar
if "show_model_settings" not in st.session_state:
    st.session_state["show_model_settings"] = False

# Create a state variable to track if the utils section is expanded
if "show_utils" not in st.session_state:
    st.session_state["show_utils"] = False

st.markdown("""<br>""", unsafe_allow_html=True)  # Smaller spacer

# --- Handle Database Initialization ---
def get_processor_for_file(file_path, domain):
    """Determine the appropriate processor for a given file.
    
    This function examines the file path and optionally file content
    to determine which document processor to use.
    
    Args:
        file_path: Path to the file
        domain: The semantic domain of the file
        
    Returns:
        An instance of the appropriate processor
    """
    file_name = os.path.basename(file_path).lower()
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # First, handle by extension
    if file_ext == '.pdf':
        return PDFProcessor(domain=domain)
    elif file_ext in ['.xlsx', '.xls']:
        return ExcelProcessor(domain=domain)
    elif file_ext == '.csv':
        return CSVProcessor(domain=domain)
    elif file_ext in ['.md', '.markdown']:
        return MarkdownProcessor(domain=domain)
    elif file_ext == '.arxml' and 'ARXMLProcessor' in globals():
        return ARXMLProcessor(domain=domain)
    elif file_ext in ['.odx', '.odx-c'] and 'ODXProcessor' in globals():
        return ODXProcessor(domain=domain)
    elif file_ext == '.json':
        # Check for signal database files
        is_signal_db = ('signal' in file_name and 'database' in file_name)
        
        # For JSON files, check content patterns to determine type
        # Use standardized naming pattern for FMEA files (starts with 'fmea-')
        is_fmea = file_name.startswith('fmea-')
        
        # Check for TARA files (starts with 'tara-')
        is_tara = file_name.startswith('tara-')
        
        # If not clear from filename, peek at content
        if not (is_fmea or is_signal_db or is_tara):
            try:
                with open(file_path, 'r') as f:
                    content_peek = f.read(1000)  # Read just the beginning to check
                    
                    # Check for signal database pattern
                    if '"database_info"' in content_peek and '"signals"' in content_peek:
                        is_signal_db = True
                        print(f"DEBUG: Detected signal database by content inspection")
                    elif any(marker in content_peek for marker in ['"fmeaType"', '"failureModes"', '"systemInformation"', '"severity"', '"occurrence"']):
                        is_fmea = True
                        print(f"DEBUG: Detected FMEA document by content inspection")
                    elif any(marker in content_peek for marker in ['"taraPhase"', '"damageScenarios"', '"threatScenarios"', '"riskAssessment"']):
                        is_tara = True
                        print(f"DEBUG: Detected TARA document by content inspection")
            except Exception as peek_error:
                print(f"DEBUG: Error peeking into file content for {file_name}: {str(peek_error)}")
        
        # Use the appropriate processor based on content type
        if is_signal_db:
            print(f"DEBUG: Using SignalDatabaseProcessor for {file_name}")
            return SignalDatabaseProcessor(domain=domain)
        elif is_fmea:
            print(f"DEBUG: Using FMEAProcessor for {file_name}")
            return FMEAProcessor(domain=domain)
        elif is_tara:
            print(f"DEBUG: Using TARAProcessor for {file_name}")
            return TARAProcessor(domain=domain)
        else:
            return JSONProcessor(domain=domain)
            
    # Default to None if no appropriate processor found
    return None

def process_directory(directory_path, domain, all_documents):
    """Process all files in a directory and its subdirectories.
    
    Args:
        directory_path: Path to the directory to process
        domain: The semantic domain of the directory
        all_documents: List to append processed documents to
        
    Returns:
        Number of files processed
    """
    files_processed = 0
    
    # Walk the directory tree once
    for root, _, files in os.walk(directory_path):
        for file in files:
            # Skip backup files
            if file.endswith('.bak'):
                continue
                
            file_path = os.path.join(root, file)
            try:
                # Get the appropriate processor for this file
                processor = get_processor_for_file(file_path, domain)
                
                if processor:
                    print(f"DEBUG: Processing file: {file}")
                    documents = processor.process_file(file_path)
                    files_processed += 1
                    
                    # Validate returned documents
                    valid_docs = []
                    for i, doc in enumerate(documents):
                        if doc is None:
                            print(f"WARNING: Processor for {file} returned None document at index {i}")
                            continue
                            
                        # Convert string documents to Document objects
                        if isinstance(doc, str):
                            print(f"WARNING: Processor for {file} returned string instead of Document at index {i}, converting")
                            doc = Document(page_content=doc, metadata={"source": file, "domain": domain})
                        
                        # Ensure metadata exists
                        if not hasattr(doc, 'metadata') or doc.metadata is None:
                            print(f"WARNING: Document from {file} at index {i} has no metadata, adding default metadata")
                            doc.metadata = {"source": file, "domain": domain}
                        
                        # Ensure source and domain are set in metadata
                        if "source" not in doc.metadata:
                            doc.metadata["source"] = file
                        if "domain" not in doc.metadata:
                            doc.metadata["domain"] = domain
                            
                        valid_docs.append(doc)
                    
                    print(f"DEBUG: File {file} produced {len(documents)} documents, {len(valid_docs)} valid after checking")
                    all_documents.extend(valid_docs)
            except Exception as e:
                print(f"DEBUG: Error processing file {file}: {str(e)}")
                import traceback
                print(f"DEBUG: Stack trace:\n{traceback.format_exc()}")
                st.error(f"❌ Error processing file {file}: {str(e)}")
    
    return files_processed

# --- Model Configuration - Keep hidden to maintain existing UI ---
# The model configuration is now handled by the utils/model_config.py module

# --- Main App Initialization ---
# Initialize DBManager with the selected embedding provider and model
db_manager = DBManager(
    persist_directory=os.path.join(app_dir, "chroma_db"),
    embedding_provider=st.session_state["embedding_provider"],
    embedding_model=st.session_state["embedding_model"]
)

# Create sidebar for model settings if enabled
if st.session_state["show_model_settings"]:
    # Use the native Streamlit sidebar
    with st.sidebar:
        # Add some styling for the sidebar
        st.markdown("""
        <style>
        .sidebar-title {
            font-weight: bold;
            font-size: 1.2rem;
            margin-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        .stSelectbox label {
            font-weight: 600;
            color: #333;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Title with styling
        st.markdown('<div class="sidebar-title">Model Configuration</div>', unsafe_allow_html=True)
        
        # Get available providers and models
        from app.utils.model_config import get_model_config, get_available_models
        current_config = get_model_config()
        available_models = get_available_models()
        
        # Create a simplified form with just the dropdowns
        with st.form(key="model_settings_sidebar_form"):
            # Embedding model selection - combine provider and model
            embedding_options = {}
            for provider, provider_info in EMBEDDING_PROVIDERS.items():
                for model in provider_info["models"]:
                    display_name = f"{provider_info['display_name']} - {model}"
                    value = f"{provider}:{model}"
                    embedding_options[display_name] = value
            
            # Find current selection
            current_embedding = f"{current_config['embedding_provider']}:{current_config['embedding_model']}"
            current_embedding_index = list(embedding_options.values()).index(current_embedding) if current_embedding in embedding_options.values() else 0
            
            # Create dropdown
            selected_embedding = st.selectbox(
                "Embedding Model",
                options=list(embedding_options.keys()),
                index=current_embedding_index,
                key="embedding_combined_select"
            )
            
            # LLM model selection - combine provider and model
            llm_options = {}
            for provider, provider_info in LLM_PROVIDERS.items():
                for model in provider_info["models"]:
                    display_name = f"{provider_info['display_name']} - {model}"
                    value = f"{provider}:{model}"
                    llm_options[display_name] = value
            
            # Find current selection
            current_llm = f"{current_config['llm_provider']}:{current_config['llm_model']}"
            current_llm_index = list(llm_options.values()).index(current_llm) if current_llm in llm_options.values() else 0
            
            # Create dropdown
            selected_llm = st.selectbox(
                "LLM Model",
                options=list(llm_options.keys()),
                index=current_llm_index,
                key="llm_combined_select"
            )
            
            # Warning about database reset
            st.warning("⚠️ Applying changes will restart the app and reset the database.")
            
            # Apply button
            submit = st.form_submit_button("Apply and Restart")
            if submit:
                # Parse the selected values
                embedding_provider, embedding_model = embedding_options[selected_embedding].split(":", 1)
                llm_provider, llm_model = llm_options[selected_llm].split(":", 1)
                
                # Update config
                from app.utils.model_config import save_config_to_file
                
                # Create new config
                new_config = current_config.copy()
                new_config["embedding_provider"] = embedding_provider
                new_config["embedding_model"] = embedding_model
                new_config["llm_provider"] = llm_provider
                new_config["llm_model"] = llm_model
                
                # If both providers are the same, update the main provider too
                if embedding_provider == llm_provider:
                    new_config["provider"] = embedding_provider
                
                # Save config
                success = save_config_to_file(new_config)
                
                if success:
                    st.success("✅ Model settings updated. Restarting...")
                    
                    # Add a delay to ensure the success message is displayed
                    time.sleep(1.5)
                    
                    # Clear the database
                    try:
                        # Define the paths to clear
                        chroma_db_dir = os.path.join(app_dir, "chroma_db")
                        embeddings_log_dir = os.path.join(app_dir, "embeddings", "log")
                        
                        # Ensure permissions before deleting
                        def ensure_directory_permissions(directory):
                            if os.path.exists(directory):
                                try:
                                    print(f"Setting permissions on {directory}")
                                    os.chmod(directory, 0o755)
                                    if os.name != 'nt':
                                        try:
                                            uid = os.getuid()
                                            gid = os.getgid()
                                            os.chown(directory, uid, gid)
                                        except Exception as e:
                                            print(f"Could not set ownership: {e}")
                                except Exception as e:
                                    print(f"Could not set permissions: {e}")
                        
                        # Ensure permissions
                        ensure_directory_permissions(chroma_db_dir)
                        ensure_directory_permissions(embeddings_log_dir)
                        
                        # Clean tracking dir
                        tracking_dir = os.path.join(chroma_db_dir, "document_tracking")
                        if os.path.exists(tracking_dir):
                            print(f"Cleaning tracking directory: {tracking_dir}")
                            ensure_directory_permissions(tracking_dir)
                            for item in os.listdir(tracking_dir):
                                item_path = os.path.join(tracking_dir, item)
                                try:
                                    if os.path.isfile(item_path):
                                        os.unlink(item_path)
                                except Exception as e:
                                    print(f"Error removing file {item_path}: {e}")
                        
                        # Delete chroma_db
                        if os.path.exists(chroma_db_dir):
                            try:
                                print(f"Deleting database directory: {chroma_db_dir}")
                                shutil.rmtree(chroma_db_dir)
                            except Exception as e:
                                print(f"Error removing directory {chroma_db_dir}: {e}")
                                for item in os.listdir(chroma_db_dir):
                                    item_path = os.path.join(chroma_db_dir, item)
                                    try:
                                        if os.path.isfile(item_path):
                                            os.unlink(item_path)
                                        elif os.path.isdir(item_path):
                                            shutil.rmtree(item_path)
                                    except Exception as e:
                                        print(f"Error removing {item_path}: {e}")
                        
                        # Delete log directory
                        if os.path.exists(embeddings_log_dir):
                            print(f"Deleting log directory: {embeddings_log_dir}")
                            shutil.rmtree(embeddings_log_dir, ignore_errors=True)
                        
                        # Clear session state
                        if "vector_db" in st.session_state:
                            del st.session_state["vector_db"]
                        
                        # Close the model settings
                        st.session_state["show_model_settings"] = False
                        
                        # Restart the app
                        restart_app()
                    except Exception as e:
                        st.error(f"❌ Error clearing database: {str(e)}")
                        st.info("Please try again or restart the application manually")
                else:
                    st.error("❌ Failed to update model settings. Please try again.")

# Attempt to initialize an existing database
vector_db = db_manager.initialize_db()
st.session_state["vector_db"] = vector_db

# If no database exists, process documents and create one
if not vector_db:
    # Show loading message
    with st.spinner("🔍 Initializing database and processing documents..."):
        # Get the path to the data directory
        data_dir = os.path.join(project_root, "data")
        
        # Define the semantic domains
        domains = ["requirements", "catalogues", "standards"]
        
        # Initialize the document list
        all_documents = []
        files_processed = 0
        
        # Process documents from each domain
        for domain in domains:
            domain_dir = os.path.join(data_dir, domain)
            if not os.path.exists(domain_dir):
                st.warning(f"Domain directory not found: {domain}")
                continue
            
            # Process all files in domain directory with a single traversal
            domain_files_processed = process_directory(domain_dir, domain, all_documents)
            files_processed += domain_files_processed
            print(f"DEBUG: Processed {domain_files_processed} files in {domain} domain")
        
        # Create the database from documents
        if all_documents:
            vector_db, unique_doc_count = db_manager.create_db_from_documents(all_documents)
            # Update session state after creation
            st.session_state["vector_db"] = vector_db
            st.info(f"📄 Processed {len(all_documents)} text chunks from {files_processed} files across {len([d for d in domains if os.path.exists(os.path.join(data_dir, d))])} domains, storing {unique_doc_count} unique documents.")
        else:
            st.error("❌ No documents found to process. Please add files to the domain directories.")

# Add the Utils section after the main app but before the chat history
if st.session_state["show_utils"]:
    st.markdown("---")
    # Only show the Document Traceability tab now
    utils_tabs = st.tabs(["Document Traceability"])

    with utils_tabs[0]:
        document_tracing_ui()

# --- Display Chat History ---
for message in st.session_state["messages"]:
    role_class = "user-message" if message["role"] == "user" else "assistant-message"
    with st.chat_message(message["role"]):
        st.markdown(f"<div class='{role_class}'>{message['content']}</div>", unsafe_allow_html=True)

# --- User Input ---
user_question = st.chat_input("Ask me anything about automotive development...")

if user_question:
    st.session_state["messages"].append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(f"<div class='user-message'>{user_question}</div>", unsafe_allow_html=True)

    # --- Processing Animation ---
    with st.spinner("Thinking... 🤔"):
        if st.session_state.get("vector_db"):
            # Process query for better retrieval
            query = preprocess_query(user_question)
            
            # Perform hybrid search to improve retrieval accuracy
            retrieved_docs = hybrid_search(st.session_state["vector_db"], query, user_question, k=20)
            
            if retrieved_docs:
                # Format source information based on document type and trace info
                source_info_list = []
                for i, doc in enumerate(retrieved_docs[:5]):
                    # Use trace info if available
                    trace_info = doc.metadata.get("trace_info", None)
                    if trace_info:
                        source_info = format_trace_info(trace_info)
                        source_info_list.append(f"📖 **Source:** {source_info}")
                    else:
                        # Fall back to standard metadata
                        source_type = doc.metadata.get('source_type', 'Unknown')
                        source = doc.metadata.get('source', 'Unknown')
                        
                        if source_type == 'pdf':
                            page = doc.metadata.get('page', 'N/A')
                            source_info_list.append(f"📖 **Source:** {source}, Page: {page}")
                        else:
                            # For JSON, add relevant metadata details
                            service_id = doc.metadata.get('service_id', '')
                            service_name = doc.metadata.get('service_name', '')
                            instance_id = doc.metadata.get('instance_id', '')
                            if instance_id:
                                source_info_list.append(f"📖 **Source:** {source} (Service: {service_name}, Service ID: {service_id}, Instance ID: {instance_id})")
                            elif service_id or service_name:
                                source_info_list.append(f"📖 **Source:** {source} (Service: {service_name}, ID: {service_id})")
                            else:
                                source_info_list.append(f"📖 **Source:** {source}")
                
                source_info = "\n".join(source_info_list)
                
                # Use content from top 5 retrieved documents for more comprehensive context
                context_text = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs[:5]])
            else:
                source_info = "❌ **No relevant information found.**"
                context_text = "No context available."
        else:
            source_info = "❌ **No document database available.**"
            context_text = "No context available."

        # --- Construct AI Prompt ---
        prompt = f"""
        ## SYSTEM ROLE
        You are an AI assistant specializing in automotive development documentation. Provide concise, accurate answers based only on the given context. Your expertise covers interface communications, system architectures, protocols, and automotive standards.

        ## USER QUESTION
        "{user_question}"

        ## CONTEXT
        '''
        {context_text}
        '''

        ## INSTRUCTIONS
        - Focus on technical details present in the provided context
        - Pay special attention to exact IDs, especially Instance IDs, Service IDs, and other numerical identifiers
        - Do not try to infer values - only respond with information explicitly stated in the context
        - Be precise with numerical values - never substitute one ID for another
        - If asked about an ID or value and it's explicitly shown in the context, quote the exact value
        - If the information isn't present in the context, clearly state so
        - Explain automotive terms and concepts when relevant
        - For JSON interface definitions, precisely report attribute values as they appear in the data
        - When dealing with file transfer or management services, pay special attention to the service name, ID and methods
        - For technical terms like "FileTransferAgent", ensure you connect it to natural language terms like "file transfer service"
        - Make direct connections between technical identifiers and their functional descriptions
        - When asked about a specific service, verify you're using information from the correct service definition

        ## RESPONSE FORMAT
           
           **Answer:** [Concise response]

        📌 **Key Insights:**
        - Bullet point 1
        - Bullet point 2
        - Bullet point 3

        {source_info}
        """

        # --- Call LLM API based on provider selection ---
        try:
            llm_provider = st.session_state.get("llm_provider")
            llm_model = st.session_state.get("llm_model")
            
            # Prepare common message format for both providers
            messages = [{'role': 'user', 'content': prompt}]
            
            # Get API keys based on provider
            if llm_provider == "openai":
                # Get OpenAI API key from environment
                api_key = os.getenv("OPENAI_API_KEY")
                
                if not api_key:
                    # Try to get from secrets
                    try:
                        api_key = st.secrets["OPENAI_API_KEY"]
                    except:
                        answer = "❌ OpenAI API key not found. Please provide your API key."
                
                if api_key:
                    # Get model parameters from the configuration manager
                    model_params = {
                        'model': llm_model,
                    }
                    
                    # Add generation parameters from the new configuration manager
                    openai_params = get_generation_params("openai")
                    for key, value in openai_params.items():
                        if value is not None:  # Only add non-None values
                            model_params[key] = value
                    
                    # Call OpenAI API
                    logger.info(f"Calling OpenAI API with model: {llm_model}")
                    client = OpenAI(api_key=api_key)
                    completion = client.chat.completions.create(
                        messages=messages, 
                        **model_params, 
                        timeout=120
                    )
                    answer = completion.choices[0].message.content
                    logger.info(f"Successfully received response from OpenAI model: {llm_model}")
                    
            elif llm_provider == "huggingface":
                # Get HuggingFace API token from environment
                api_key = os.getenv("HUGGINGFACE_API_TOKEN")
                
                if not api_key:
                    # Try to get from secrets
                    try:
                        api_key = st.secrets["HUGGINGFACE_API_TOKEN"]
                    except:
                        answer = "❌ HuggingFace API token not found. Please provide your API token."
                
                if api_key:
                    # Model parameters for HuggingFace
                    model_params = {
                        'model': llm_model,
                    }
                    
                    # Call HuggingFace API
                    logger.info(f"Calling HuggingFace API with model: {llm_model}")
                    client = get_huggingface_client(api_key=api_key)
                    completion = client.chat.create(
                        messages=messages,
                        **model_params,
                        timeout=120
                    )
                    answer = completion.choices[0].message.content
                    logger.info(f"Successfully received response from HuggingFace model: {llm_model}")
            else:
                answer = f"❌ Unsupported LLM provider: {llm_provider}"
                
        except Exception as e:
            answer = f"❌ Error generating response: {str(e)}"

    # --- Display AI Response ---
    st.session_state["messages"].append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(f"<div class='assistant-message'>{answer}</div>", unsafe_allow_html=True)