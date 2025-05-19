import os
import shutil
import streamlit as st
import sys
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents.base import Document
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
import chromadb
from dotenv import load_dotenv
import traceback
import json
import datetime
from .document_tracking import DocumentTraceability
import hashlib
import re # Added for filename sanitization
import time

# Add new imports for HuggingFace support
from .huggingface_embeddings import HuggingFaceEmbeddings
from ..utils.model_config import get_model_config

# --- Define Log Directory --- 
# Define log directory globally for reuse
log_directory = os.path.join(os.path.dirname(__file__), "log")
# --- END Log Directory --- 


class DBManager:
    """Manager for vector database operations.
    
    Handles initialization, persistence, and querying of the vector database.
    """
    
    def __init__(self, persist_directory: str, embedding_model: str = None, embedding_provider: str = None):
        """Initialize the database manager.
        
        Args:
            persist_directory: Directory to persist the database
            embedding_model: Name of the embedding model to use (optional)
            embedding_provider: Provider for embeddings ('openai' or 'huggingface') (optional)
        """
        # Load environment variables if not already done
        load_dotenv()
        
        # Get model configuration
        model_config = get_model_config()
        
        # Use provided values or fall back to configuration
        self.embedding_provider = embedding_provider or model_config.get("embedding_provider", "openai")
        self.embedding_model = embedding_model or model_config.get("embedding_model", "text-embedding-3-large")
        
        # Set up API keys based on provider
        if self.embedding_provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                st.error("❌ OpenAI API key not found in environment variables.")
        elif self.embedding_provider == "huggingface":
            # Get HuggingFace cache folder
            self.hf_cache_folder = os.getenv("HUGGINGFACE_HUB_CACHE")
            # For HuggingFace Hub API access (if needed)
            self.hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
            
        self.persist_directory = persist_directory
        self.db = None
        
        # Add tracking directory
        self.tracking_directory = os.path.join(persist_directory, "document_tracking")
        os.makedirs(self.tracking_directory, exist_ok=True)
        
        # Document tracking index
        self.tracking_index_path = os.path.join(self.tracking_directory, "tracking_index.json")
        self.tracking_index = self._load_tracking_index()
    
    def _get_embeddings_function(self):
        """Get the appropriate embeddings function based on provider."""
        if self.embedding_provider == "openai":
            print(f"DEBUG: Using OpenAI embeddings with model: {self.embedding_model}")
            return OpenAIEmbeddings(model=self.embedding_model, openai_api_key=self.api_key)
        elif self.embedding_provider == "huggingface":
            print(f"DEBUG: Using HuggingFace embeddings with model: {self.embedding_model}")
            return HuggingFaceEmbeddings(
                model_name=self.embedding_model,
                cache_folder=self.hf_cache_folder
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {self.embedding_provider}")
    
    def _load_tracking_index(self) -> Dict[str, Any]:
        """Load document tracking index or create if not exists."""
        if os.path.exists(self.tracking_index_path):
            try:
                with open(self.tracking_index_path, 'r') as f:
                    loaded_index = json.load(f)
                return loaded_index
            except Exception as e:
                print(f"WARNING: Error loading tracking index: {str(e)}. Creating new index.")
                # If error loading, create new
        
        # Create new index structure
        index = {
            "documents": {},  # doc_id -> traceability info
            "sources": {},    # source_path -> [doc_ids]
            "domains": {},    # domain -> [doc_ids]
            "file_types": {}, # file_type -> [doc_ids]
            "total_documents": 0, # Initialize count
            "created": datetime.datetime.now().isoformat()
        }
        
        # Save the newly created index immediately
        try:
            with open(self.tracking_index_path, 'w') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            print(f"ERROR: Failed to save newly created tracking index: {str(e)}")
            # If saving the new index fails, things are bad, but return the in-memory version
        
        return index
    
    def _save_tracking_index(self):
        """Save tracking index to disk, ensuring the document count is accurate."""
        # Ensure the main keys exist
        for key in ["documents", "sources", "domains", "file_types"]:
            if key not in self.tracking_index:
                self.tracking_index[key] = {}
        
        # Explicitly calculate count JUST before saving
        current_doc_count = len(self.tracking_index.get("documents", {}))
        self.tracking_index["total_documents"] = current_doc_count
        print(f"DEBUG: Saving tracking index with total_documents = {current_doc_count}")
        
        try:
            with open(self.tracking_index_path, 'w') as f:
                json.dump(self.tracking_index, f, indent=2)
            print(f"DEBUG: Successfully wrote tracking index to {self.tracking_index_path}")
        except Exception as e:
            print(f"ERROR: Failed to write tracking index to {self.tracking_index_path}: {str(e)}")
            # Raise the exception to signal the failure upstream if needed
            raise e
    
    def _track_document(self, document: Document) -> str:
        """Track a document and return its ID."""
        # Create traceability info with provider information
        trace_info = DocumentTraceability.from_document(
            doc=document, 
            embedding_model=self.embedding_model,
            embedding_provider=self.embedding_provider,
            source_path=document.metadata.get("source", None)
        )
        
        # Store in tracking index
        doc_id = trace_info.doc_id
        self.tracking_index["documents"][doc_id] = trace_info.to_dict()
        
        # Update source index
        source_path = trace_info.source_path or "unknown_source" # Handle None source
        if source_path not in self.tracking_index["sources"]:
            self.tracking_index["sources"][source_path] = []
        if doc_id not in self.tracking_index["sources"][source_path]:
            self.tracking_index["sources"][source_path].append(doc_id)
        
        # Update domain index
        domain = trace_info.domain or "unknown_domain" # Handle None domain
        if domain not in self.tracking_index["domains"]:
            self.tracking_index["domains"][domain] = []
        if doc_id not in self.tracking_index["domains"][domain]:
            self.tracking_index["domains"][domain].append(doc_id)
        
        # Update file type index
        file_type = trace_info.file_type or "unknown_type" # Handle None type
        if file_type not in self.tracking_index["file_types"]:
            self.tracking_index["file_types"][file_type] = []
        if doc_id not in self.tracking_index["file_types"][file_type]:
            self.tracking_index["file_types"][file_type].append(doc_id)
        
        return doc_id
    
    def initialize_db(self) -> Optional[Chroma]:
        """Initialize the vector database.
        
        First tries to load an existing database, and if that fails,
        creates a new one.
        
        Returns:
            Initialized Chroma database or None if initialization fails
        """
        # Try to load existing database
        try:
            if os.path.exists(self.persist_directory):
                # Load tracking index first to get expected count
                self.tracking_index = self._load_tracking_index() # Reload in case it changed
                expected_count = len(self.tracking_index.get("documents", {}))
                print(f"DEBUG: Expected document count from tracking index: {expected_count}")
                # End load tracking
                
                try:
                    client = chromadb.PersistentClient(path=self.persist_directory)
                except ValueError as ve:
                    # Check specifically for the tenant error
                    if "Could not connect to tenant" in str(ve):
                        error_msg = "❌ ChromaDB tenant initialization error. This typically occurs after deleting the database directory."
                        print(f"DEBUG: {error_msg}")
                        print(f"DEBUG: Original error: {str(ve)}")
                        
                        # Suggest app restart
                        st.error(error_msg)
                        st.warning("The application needs to be restarted completely to fix this issue. Please close this window and restart the app, or click the 'Clear DB' button which will restart the app for you.")
                        
                        # Provide a button to trigger restart if main.py has restart_app function
                        if st.button("🔄 Restart Application"):
                            # Get the path to the current Python executable
                            python_executable = sys.executable
                            
                            # Get the full path to the main.py file
                            main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
                            
                            # Start a new process to run the Streamlit app
                            print(f"Restarting app using: {python_executable} -m streamlit run {main_path}")
                            
                            try:
                                # Start a new process directly with the current Python executable
                                # which already has the conda environment activated
                                subprocess.Popen([python_executable, "-m", "streamlit", "run", main_path])
                                
                                # Add a sleep to ensure the new process has time to start
                                print("Waiting for new process to start...")
                                time.sleep(2)
                                
                                # Exit the current process with success code
                                print("Exiting current process...")
                                os._exit(0)
                            except Exception as e:
                                print(f"Error in restart process: {str(e)}")
                                # If something goes wrong, we should still exit
                                os._exit(1)
                    
                    # Re-raise for broader exception handling
                    raise ve
                
                embeddings = self._get_embeddings_function()
                self.db = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=embeddings,
                    client=client
                )
                
                # Test with a simple query to verify the DB is working
                print("DEBUG: Testing loaded Chroma database...")
                self.db.similarity_search("test", k=1) # Check if query runs
                print("DEBUG: Chroma database test query successful.")
                
                # Check if the database count matches expected count
                actual_count = 0
                try:
                    actual_count = self.db._collection.count()
                    print(f"DEBUG: Actual document count from DB collection: {actual_count}")
                    
                    if actual_count == expected_count and actual_count > 0:
                        st.success(f"✅ Successfully loaded existing vector database with {actual_count} documents.")
                    elif actual_count > 0 and actual_count != expected_count:
                        st.warning(f"⚠️ Loaded existing database, but document count ({actual_count}) differs from expected ({expected_count}). Consider rebuilding.")
                    elif actual_count == 0 and expected_count == 0:
                        st.info("Empty database, proceeding with initialization...")
                    elif actual_count == 0 and expected_count > 0:
                        st.error(f"❌ Loaded database is empty, but {expected_count} documents were expected. Database may be corrupt. Please rebuild.")
                        # Treat as failure, force rebuild
                        raise ValueError(f"DB empty but expected {expected_count} docs")
                    else: # actual_count > 0 and expected_count == 0 (shouldn't happen if tracking is correct)
                        st.warning(f"⚠️ Loaded database has {actual_count} documents, but tracking index expected 0. Tracking might be out of sync.")
                except Exception as count_err:
                    # If counting fails after load, it's suspicious
                    print(f"ERROR: Error getting collection count: {str(count_err)}")
                    st.error(f"❌ Failed to verify document count in loaded database: {str(count_err)}. Database might be corrupt. Please rebuild.")
                    raise count_err # Treat as failure to force rebuild
                # End FIX
                
                return self.db
        except Exception as e:
            # Add detailed logging for the exception
            traceback_info = traceback.format_exc()
            print(f"DEBUG: Failed to load, query, or verify existing database. Error: {str(e)}")
            print(f"DEBUG: Traceback: {traceback_info}")
            st.error(f"❌ Could not load existing database. Attempting to rebuild index... Error: {str(e)}")
            
            # Only delete if there was an error accessing the existing DB
            if os.path.exists(self.persist_directory):
                print(f"DEBUG: Removing existing persist directory: {self.persist_directory}")
                try:
                    shutil.rmtree(self.persist_directory)
                    print(f"DEBUG: Successfully removed directory: {self.persist_directory}")
                except Exception as rm_err:
                    print(f"ERROR: Error removing directory {self.persist_directory}: {str(rm_err)}")
                    st.error(f"❌ Failed to remove corrupted database directory: {str(rm_err)}")
        
        # If we get here, loading failed or directory didn't exist.
        print("DEBUG: Setting self.db to None and returning None from initialize_db.")
        self.db = None
        return None
    
    def create_db_from_documents(self, documents: List[Document]) -> Tuple[Optional[Chroma], int]:
        """Create a new vector database from documents.
        
        Args:
            documents: List of documents to add to the database
            
        Returns:
            A tuple containing the created Chroma database (or None if creation fails)
            and the number of unique documents added.
        """
        if not documents:
            st.error("❌ No documents provided to create database.")
            return None, 0
        
        try:
            # Print diagnostic information
            print(f"DEBUG: Total documents to process: {len(documents)}")
            
            # Filter out non-Document objects
            valid_documents = [doc for doc in documents if isinstance(doc, Document)]
            
            if len(valid_documents) < len(documents):
                print(f"WARNING: Filtered out {len(documents) - len(valid_documents)} invalid documents")
                if not valid_documents:
                    st.error("❌ No valid Document objects found in the provided documents.")
                    return None, 0
            
            # Deduplicate documents based on content hash
            unique_documents_dict = {}
            processed_count = 0
            skipped_due_to_error = 0

            for i, doc in enumerate(valid_documents):
                try:
                    # Ensure page_content exists and is hashable
                    if not hasattr(doc, 'page_content') or not isinstance(doc.page_content, str):
                        print(f"WARNING: Document at index {i} lacks valid string page_content. Skipping deduplication, adding by object ID.")
                        unique_documents_dict[id(doc)] = doc
                        skipped_due_to_error += 1
                        continue # Move to next document

                    # Hash the content
                    doc_hash = hashlib.md5(doc.page_content.encode()).hexdigest()

                    # Add to dict if hash is new
                    if doc_hash not in unique_documents_dict:
                        unique_documents_dict[doc_hash] = doc
                    
                    processed_count += 1

                except Exception as e:
                    # Catch any unexpected error during processing this specific document
                    print(f"ERROR: Unexpected error deduplicating document at index {i}: {str(e)}. Skipping deduplication, adding by object ID.")
                    # Use object ID as fallback key
                    unique_documents_dict[id(doc)] = doc 
                    skipped_due_to_error += 1
                      
            original_count = len(valid_documents)
            processed_documents = list(unique_documents_dict.values())
            final_unique_count = len(processed_documents)
            print(f"INFO: Deduplication finished. Input: {original_count}, Final unique count: {final_unique_count}, Skipped due to error: {skipped_due_to_error}")

            # Track documents before creating embeddings (use the deduplicated list)
            print(f"DEBUG: Tracking {final_unique_count} unique documents for traceability")
            self.tracking_index["documents"] = {} # Clear just the documents part for this run
            
            for doc in processed_documents:
                self._track_document(doc)
            
            # --- START NEW LOGGING STRATEGY ---
            print(f"DEBUG: Starting new logging strategy for {final_unique_count} processed documents (Creation).")
            self._log_processed_chunks(processed_documents, "creation")
            print("DEBUG: Finished new logging strategy (Creation).")
            # --- END NEW LOGGING STRATEGY ---

            # Use dynamic embeddings function based on provider
            print(f"DEBUG: Creating embeddings with provider: {self.embedding_provider}, model: {self.embedding_model}")
            embeddings = self._get_embeddings_function()
            
            print(f"DEBUG: Creating ChromaDB client at: {self.persist_directory}")
            try:
                client = chromadb.PersistentClient(path=self.persist_directory)
            except ValueError as ve:
                # Check specifically for the tenant error
                if "Could not connect to tenant" in str(ve):
                    error_msg = "❌ ChromaDB tenant initialization error. This typically occurs after deleting the database directory."
                    print(f"DEBUG: {error_msg}")
                    print(f"DEBUG: Original error: {str(ve)}")
                    
                    # Suggest app restart
                    st.error(error_msg)
                    st.warning("The application needs to be restarted completely to fix this issue. Please close this window and restart the app, or click the 'Clear DB' button which will restart the app for you.")
                    
                    # Provide a button to trigger restart if main.py has restart_app function
                    if st.button("🔄 Restart Application"):
                        # Get the path to the current Python executable
                        python_executable = sys.executable
                        
                        # Get the full path to the main.py file
                        main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
                        
                        # Start a new process to run the Streamlit app
                        print(f"Restarting app using: {python_executable} -m streamlit run {main_path}")
                        
                        try:
                            # Start a new process directly with the current Python executable
                            # which already has the conda environment activated
                            subprocess.Popen([python_executable, "-m", "streamlit", "run", main_path])
                            
                            # Add a sleep to ensure the new process has time to start
                            print("Waiting for new process to start...")
                            time.sleep(2)
                            
                            # Exit the current process with success code
                            print("Exiting current process...")
                            os._exit(0)
                        except Exception as e:
                            print(f"Error in restart process: {str(e)}")
                            # If something goes wrong, we should still exit
                            os._exit(1)
                
                # Re-raise for broader exception handling
                raise ve
            
            print(f"DEBUG: Creating Chroma database with {final_unique_count} unique documents")
            try:
                # Filter complex metadata from all documents - use proper approach
                for i, doc in enumerate(processed_documents): # Use deduplicated list
                    if not isinstance(doc, Document):
                        print(f"DEBUG: Document at index {i} is not a Document object: {type(doc)}")
                        continue
                        
                    # Create clean metadata dictionary manually
                    filtered_metadata = {}
                    if hasattr(doc, 'metadata') and doc.metadata:
                        for key, value in doc.metadata.items():
                            # Only keep simple data types
                            if isinstance(value, (str, int, float, bool)) or value is None:
                                filtered_metadata[key] = value
                            elif isinstance(value, list) or isinstance(value, dict):
                                # Convert complex types to strings
                                try:
                                    filtered_metadata[key] = str(value)
                                except:
                                    pass  # Skip if can't convert
                    doc.metadata = filtered_metadata
                
                # Actually create the database (use the deduplicated list)
                self.db = Chroma.from_documents(
                    documents=processed_documents, # Use deduplicated list
                    embedding=embeddings,
                    persist_directory=self.persist_directory,
                    client=client
                )
                print("DEBUG: Successfully created Chroma database")
                
                # Save tracking index AFTER successful creation
                try:
                    print("DEBUG: Saving tracking index after successful DB creation.")
                    self._save_tracking_index() 
                except Exception as index_save_err:
                     print(f"ERROR: DB created successfully, but failed to save tracking index: {str(index_save_err)}")
                     # Proceed, but inconsistency might occur later
                # End move

                st.success("✅ Successfully created vector embeddings and built the database.")
                return self.db, final_unique_count
            except Exception as e:
                print(f"DEBUG: Exception in Chroma.from_documents: {str(e)}")
                traceback_info = traceback.format_exc()
                print(f"DEBUG: Traceback: {traceback_info}")
                st.error(f"❌ Failed to create embeddings: {str(e)}")
                return None, 0
        except Exception as e:
            traceback_info = traceback.format_exc()
            print(f"DEBUG: Exception in create_db_from_documents: {str(e)}")
            print(f"DEBUG: Traceback: {traceback_info}")
            st.error(f"❌ Failed to create embeddings: {str(e)}")
            return None, 0
    
    def get_db(self) -> Optional[Chroma]:
        """Get the current database instance.
        
        Returns:
            Current Chroma database or None if not initialized
        """
        return self.db
    
    def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to an existing database.
        
        Args:
            documents: List of documents to add
            
        Returns:
            True if documents were added successfully, False otherwise
        """
        if not self.db:
            st.error("❌ Database not initialized. Cannot add documents.")
            return False
        
        try:
            # Clean metadata using the same process as in create_db_from_documents
            cleaned_documents = []
            for doc in documents:
                # Check for valid Document object
                if not isinstance(doc, Document):
                    continue
                
                # Create clean metadata dictionary manually
                filtered_metadata = {}
                if hasattr(doc, 'metadata') and doc.metadata:
                    for key, value in doc.metadata.items():
                        # Only keep simple data types
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            filtered_metadata[key] = value
                        elif isinstance(value, list) or isinstance(value, dict):
                            # Convert complex types to strings
                            try:
                                filtered_metadata[key] = str(value)
                            except:
                                pass  # Skip if can't convert
                
                # Create new Document with filtered metadata
                cleaned_doc = Document(
                    page_content=doc.page_content,
                    metadata=filtered_metadata
                )
                cleaned_documents.append(cleaned_doc)
            
            # --- FIX: Deduplicate added documents relative to existing AND new ones ---
            # 1. Get existing tracked *content* hashes (doc_id is derived from content)
            existing_hashes = set()
            for info in self.tracking_index.get("documents", {}).values():
                if 'content_hash' in info:
                    try:
                        # Use embedding provider from tracking if available, otherwise default to current
                        provider = info.get('embedding_provider', self.embedding_provider)
                        doc_id = DocumentTraceability.from_document(
                            Document(page_content=info['content_hash'], metadata={}), 
                            embedding_model=self.embedding_model,
                            embedding_provider=provider
                        ).doc_id
                        existing_hashes.add(doc_id)
                    except Exception as e:
                        print(f"ERROR: Error computing doc_id from existing hash: {str(e)}")

            # 2. Deduplicate new batch internally and against existing
            unique_new_docs_dict = {}
            skipped_new_duplicates = 0
            skipped_new_error = 0
            
            for i, doc in enumerate(cleaned_documents):
                try:
                    if not hasattr(doc, 'page_content') or not isinstance(doc.page_content, str):
                        # Use object ID if no content - won't match existing but keeps it
                        doc_id = f"objid_{id(doc)}"
                        print(f"WARNING: Add doc {i}: invalid content, using object ID for uniqueness.")
                        skipped_new_error += 1
                    else:
                        # Generate doc_id (which is based on hash)
                        doc_id = DocumentTraceability.from_document(
                            doc=doc, 
                            embedding_model=self.embedding_model,
                            embedding_provider=self.embedding_provider
                        ).doc_id

                    # Check against existing AND current batch dict keys (which are doc_ids)
                    if doc_id not in existing_hashes and doc_id not in unique_new_docs_dict:
                        unique_new_docs_dict[doc_id] = doc # Store by doc_id
                    else:
                        skipped_new_duplicates += 1
                except Exception as e:
                     print(f"ERROR: Add doc {i}: error during deduplication hash/check: {str(e)}")
                     doc_id = f"objid_{id(doc)}" # Fallback ID
                     unique_new_docs_dict[doc_id] = doc # Add with fallback ID
                     skipped_new_error += 1

            final_docs_to_add = list(unique_new_docs_dict.values())
            final_add_count = len(final_docs_to_add)
            
            if final_add_count == 0:
                 st.info(f"ℹ️ No new unique documents to add (skipped {skipped_new_duplicates} duplicates, {skipped_new_error} errors).")
                 return True # Nothing to add, technically successful

            print(f"INFO: Adding {final_add_count} new unique documents (skipped {skipped_new_duplicates} duplicates, {skipped_new_error} errors).")
            # --- End FIX ---

            # Track documents before adding (use the unique list)
            for doc in final_docs_to_add:
                self._track_document(doc)

            # --- START NEW LOGGING STRATEGY ---
            print(f"DEBUG: Starting new logging strategy for {final_add_count} documents to add (Addition).")
            self._log_processed_chunks(final_docs_to_add, "addition")
            print("DEBUG: Finished new logging strategy (Addition).")
            # --- END NEW LOGGING STRATEGY ---

            # Add documents to database (use the unique list)
            print(f"DEBUG: Adding {len(final_docs_to_add)} cleaned documents to ChromaDB.")
            self.db.add_documents(final_docs_to_add)
            print(f"DEBUG: Successfully added documents to ChromaDB collection.")

            # Save tracking index AFTER successful addition
            try:
                print("DEBUG: Saving tracking index after successful document addition.")
                self._save_tracking_index()
            except Exception as index_save_err:
                 print(f"ERROR: Documents added successfully, but failed to save tracking index: {str(index_save_err)}")
                 # Proceed, but inconsistency might occur later
            # End move

            st.success(f"✅ Successfully added {final_add_count} new unique documents to the database.")
            return True
        except Exception as e:
            st.error(f"❌ Failed to add documents: {str(e)}")
            return False
    
    def similarity_search(self, query: str, k: int = 5, filter_dict: Optional[dict] = None):
        """Perform similarity search in the database.
        
        Args:
            query: Query string
            k: Number of results to return
            filter_dict: Dictionary of metadata filters
            
        Returns:
            List of documents similar to the query
        """
        if not self.db:
            st.error("❌ Database not initialized. Cannot perform search.")
            print("DEBUG: similarity_search called but self.db is None.")
            return []
        
        print(f"DEBUG: similarity_search called with query='{query}', k={k}, filter={filter_dict}")
        
        try:
            raw_results = []
            if filter_dict:
                print(f"DEBUG: Calling ChromaDB search with filter: {filter_dict}")
                raw_results = self.db.similarity_search(query, k=k, filter=filter_dict)
            else:
                print("DEBUG: Calling ChromaDB search without filter.")
                raw_results = self.db.similarity_search(query, k=k)
            
            print(f"DEBUG: ChromaDB search returned {len(raw_results)} results.")
            
            # Enhance results with traceability information
            enhanced_results = []
            for doc in raw_results:
                try:
                    # Generate a document ID from content hash
                    doc_id = DocumentTraceability.from_document(
                        doc=doc, 
                        embedding_model=self.embedding_model,
                        embedding_provider=self.embedding_provider
                    ).doc_id
                    
                    # Try to get trace info from tracking index
                    trace_info = self.get_document_trace(doc_id)
                    if trace_info:
                        # Add trace info to metadata for client use
                        # Make a copy to avoid modifying original results directly if needed elsewhere
                        enhanced_doc = Document(page_content=doc.page_content, metadata=doc.metadata.copy()) 
                        enhanced_doc.metadata["trace_info"] = trace_info
                        enhanced_results.append(enhanced_doc)
                    else:
                        enhanced_results.append(doc) # Append original doc if no trace info
                except Exception as enhance_err:
                    print(f"DEBUG: Error enhancing document metadata: {str(enhance_err)}. Skipping enhancement for this doc.")
                    enhanced_results.append(doc) # Append original doc on error

            print(f"DEBUG: Returning {len(enhanced_results)} results after enhancement.")
            return enhanced_results
        except Exception as e:
            traceback_info = traceback.format_exc()
            print(f"DEBUG: Exception during ChromaDB search: {str(e)}")
            print(f"DEBUG: Traceback: {traceback_info}")
            st.error(f"❌ Search error: {str(e)}")
            return []
    
    # Document traceability query methods
    
    def get_source_documents(self) -> List[str]:
        """Get list of all source documents."""
        return list(self.tracking_index["sources"].keys())
    
    def get_documents_by_source(self, source_path: str) -> List[Dict[str, Any]]:
        """Get all document traces for a specific source."""
        if source_path not in self.tracking_index["sources"]:
            return []
        
        doc_ids = self.tracking_index["sources"][source_path]
        # Ensure doc_id exists in documents index before trying to access
        return [self.tracking_index["documents"][doc_id] for doc_id in doc_ids if doc_id in self.tracking_index["documents"]]
    
    def get_documents_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all document traces for a specific domain."""
        if domain not in self.tracking_index["domains"]:
            return []
        
        doc_ids = self.tracking_index["domains"][domain]
        # Ensure doc_id exists in documents index before trying to access
        return [self.tracking_index["documents"][doc_id] for doc_id in doc_ids if doc_id in self.tracking_index["documents"]]
    
    def get_documents_by_type(self, file_type: str) -> List[Dict[str, Any]]:
        """Get all document traces for a specific file type."""
        if file_type not in self.tracking_index["file_types"]:
            return []
        
        doc_ids = self.tracking_index["file_types"][file_type]
        # Ensure doc_id exists in documents index before trying to access
        return [self.tracking_index["documents"][doc_id] for doc_id in doc_ids if doc_id in self.tracking_index["documents"]]
    
    def get_document_trace(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get trace info for a specific document ID."""
        return self.tracking_index["documents"].get(doc_id)

    # --- START NEW HELPER METHOD for Logging ---
    def _log_processed_chunks(self, documents_to_log: List[Document], process_type: str):
        """Logs processed document chunks to domain-specific files based on source.

        Args:
            documents_to_log: List of Document objects (chunks) to log.
            process_type: String indicating the process ("creation" or "addition").
        """
        print(f"DEBUG: Logging {len(documents_to_log)} chunks for process type: {process_type}")

        # Group documents by source file path
        source_groups: Dict[str, List[Tuple[int, Document]]] = {}
        for i, doc in enumerate(documents_to_log):
            source_path = doc.metadata.get("source", "unknown_source")
            if source_path not in source_groups:
                source_groups[source_path] = []
            source_groups[source_path].append((i, doc)) # Store original index too

        # Process each source group
        for source_path, doc_tuples in source_groups.items():
            if not doc_tuples:
                continue # Skip if empty group (shouldn't happen)

            # Use the first doc in the group to determine domain
            # Assume all chunks from the same source file belong to the same domain
            first_doc = doc_tuples[0][1]
            domain = first_doc.metadata.get("domain", "unknown_domain")

            # Sanitize domain name for directory creation
            safe_domain = re.sub(r'[\/*?:"<>|]', "_", domain) # Replace invalid chars
            domain_log_dir = os.path.join(log_directory, safe_domain)

            # Create domain-specific log directory
            try:
                os.makedirs(domain_log_dir, exist_ok=True)
            except OSError as e:
                print(f"ERROR: Could not create log directory '{domain_log_dir}': {e}. Skipping logs for source '{source_path}'.")
                continue

            # Sanitize source filename for log file name
            base_name = os.path.basename(source_path)
            safe_base_name = re.sub(r'[\/*?:"<>|]', "_", base_name) # Replace invalid chars
            log_filename = f"{safe_base_name}.log"
            log_filepath = os.path.join(domain_log_dir, log_filename)

            # Write log file for this source
            try:
                # Use 'w' to overwrite log file for each run (ensures fresh logs)
                with open(log_filepath, 'w', encoding='utf-8') as f:
                    # Write Header
                    f.write(f"--- Log Start ({process_type.capitalize()}) ---\n")
                    f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"Source File: {source_path}\n")
                    f.write(f"Domain: {domain}\n")
                    f.write(f"Total Chunks for this Source in this Batch: {len(doc_tuples)}\n")
                    f.write("----------------------------------------\n\n")

                    # Write each chunk's details
                    for i, doc in doc_tuples: # Use the stored index and doc
                        try:
                            doc_id = DocumentTraceability.from_document(
                                doc=doc, 
                                embedding_model=self.embedding_model,
                                embedding_provider=self.embedding_provider
                            ).doc_id
                        except Exception:
                            doc_id = "error_generating_id"

                        f.write(f"--- Chunk Start (Index in Batch: {i}, ID: {doc_id}) ---\n")

                        # Write Metadata
                        f.write("Metadata:\n")
                        if hasattr(doc, 'metadata') and doc.metadata:
                            for key, value in doc.metadata.items():
                                # Truncate long values for readability in log
                                value_str = str(value)
                                if len(value_str) > 200:
                                    value_str = value_str[:200] + "... (truncated)"
                                f.write(f"  {key}: {value_str}\n")
                        else:
                            f.write("  (No metadata found)\n")

                        # Write Page Content
                        f.write("Page Content:\n")
                        page_content = getattr(doc, 'page_content', '[NO PAGE CONTENT FOUND]')
                        if not isinstance(page_content, str):
                            page_content = str(page_content)
                        f.write(page_content)
                        f.write("\n") # Add newline after content

                        f.write(f"--- Chunk End ---\n\n")

                    f.write(f"--- Log End ({process_type.capitalize()}) ---\n")
                print(f"DEBUG: Successfully wrote log for source '{source_path}' to '{log_filepath}'")

            except IOError as e:
                print(f"ERROR: Failed to write log file '{log_filepath}': {e}")
            except Exception as e:
                # Catch any other unexpected errors during logging for this source file
                print(f"ERROR: Unexpected error writing log file '{log_filepath}': {e}")
                import traceback
                print(traceback.format_exc())
    # --- END NEW HELPER METHOD ---
