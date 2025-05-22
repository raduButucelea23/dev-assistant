import streamlit as st
import traceback
import os
import json
import datetime
import time
from pathlib import Path
from app.retrieval.query_preprocessing import extract_technical_terms

def create_log_directory():
    """Create a timestamped log directory for the current retrieval session."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_dir = Path("app/embeddings/log/runtime") / timestamp
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def log_documents(log_dir, filename, documents, metadata=None):
    """Save document contents and metadata to a JSON file."""
    doc_data = []
    
    for i, doc in enumerate(documents):
        # Extract document data
        doc_info = {
            "index": i,
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        doc_data.append(doc_info)
    
    # Add any additional metadata
    log_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "count": len(documents),
        "metadata": metadata or {},
        "documents": doc_data
    }
    
    # Save to file
    log_path = log_dir / f"{filename}.json"
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
    
    print(f"DEBUG: Logged {len(documents)} documents to {log_path}")
    return log_path

def hybrid_search(db, processed_query, original_query, k=20):
    """Perform hybrid search combining keyword filtering with vector similarity.
    
    This approach improves retrieval by:
    1. First attempting metadata filtering for exact matches
    2. Falling back to semantic search if metadata filtering returns too few results
    3. Combining results for a more comprehensive set of relevant documents
    4. Applying domain filtering if specified in the session state
    """
    # Create log directory for this retrieval session
    log_dir = create_log_directory()
    
    # Log the initial query
    query_log = {
        "original_query": original_query,
        "processed_query": processed_query,
        "k": k,
        "start_time": time.time()
    }
    
    with open(log_dir / "query.json", "w") as f:
        json.dump(query_log, f, indent=2)
    
    print(f"DEBUG: hybrid_search started. Original query: '{original_query}', Processed query: '{processed_query}', k={k}")
    metadata_results = []
    
    # Check if domain filtering is enabled
    domain_filter = st.session_state.get("domain_filter")
    print(f"DEBUG: Domain filter: {domain_filter}")
    
    # Step 1: Try metadata filtering for exact matches with technical terms
    print("DEBUG: Starting metadata filtering step.")
    technical_terms = extract_technical_terms(original_query)
    print(f"DEBUG: Extracted technical terms: {technical_terms}")
    
    # Log technical terms
    with open(log_dir / "technical_terms.json", "w") as f:
        json.dump({
            "terms": technical_terms,
            "query": original_query
        }, f, indent=2)
    
    if technical_terms:
        for term in technical_terms:
            print(f"DEBUG: Processing technical term: '{term}'")
            metadata_filters = {
                "data_object_name": {"$in": [term]},
                "service_name": {"$in": [term]},
                "normalized_name": {"$in": [term.lower()]},
                "normalized_service_name": {"$in": [term.lower()]},
                "name_keywords": {"$in": [term.lower()]},
                "service_keywords": {"$in": [term.lower()]},
                "service_aliases": {"$in": [term.lower()]},
                "method_names": {"$in": [term]},
            }
            
            for field, filter_value in metadata_filters.items():
                current_filter = {field: filter_value}
                print(f"DEBUG: Attempting filter: {current_filter}")
                try:
                    # Combine with domain filter if enabled
                    if domain_filter:
                        final_filter_dict = {
                            **current_filter, 
                            "domain": domain_filter
                        }
                    else:
                        final_filter_dict = current_filter
                        
                    print(f"DEBUG: Calling similarity_search with filter: {final_filter_dict}")
                    filtered_docs = db.similarity_search(
                        processed_query,
                        k=5, 
                        filter=final_filter_dict
                    )
                    print(f"DEBUG: Filtered search returned {len(filtered_docs)} docs for filter {current_filter}")
                    
                    # Log the results from this specific filter
                    if filtered_docs:
                        filter_log_name = f"metadata_filter_{term}_{field}"
                        log_documents(log_dir, filter_log_name, filtered_docs, {
                            "filter": str(current_filter),
                            "term": term,
                            "field": field
                        })
                    
                    metadata_results.extend(filtered_docs)
                except Exception as filter_err:
                    # If a particular filter fails, log and continue
                    print(f"DEBUG: Error during metadata filtered search for {current_filter}: {str(filter_err)}")
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                    
                    # Log the error
                    with open(log_dir / f"error_metadata_filter_{term}_{field}.json", "w") as f:
                        json.dump({
                            "error": str(filter_err),
                            "traceback": traceback.format_exc(),
                            "filter": str(current_filter)
                        }, f, indent=2)
                    
                    continue
    else:
        print("DEBUG: No technical terms found for metadata filtering.")
    
    print(f"DEBUG: Metadata filtering step finished. Found {len(metadata_results)} potential results.")
    
    # Log all metadata results
    if metadata_results:
        log_documents(log_dir, "metadata_results_all", metadata_results, {
            "count": len(metadata_results),
            "technical_terms": technical_terms
        })

    # Step 2: Always perform a standard semantic search as well
    print("DEBUG: Starting standard semantic search step.")
    standard_results = []
    try:
        # Apply domain filter to standard search if specified
        semantic_filter = {"domain": domain_filter} if domain_filter else None
        print(f"DEBUG: Calling similarity_search for standard semantic search. Filter: {semantic_filter}")
        
        standard_results = db.similarity_search(
            processed_query, 
            k=k,
            filter=semantic_filter
        )
        print(f"DEBUG: Standard semantic search returned {len(standard_results)} results.")
        
        # Log standard semantic search results
        log_documents(log_dir, "standard_semantic_results", standard_results, {
            "filter": str(semantic_filter),
            "count": len(standard_results)
        })
        
    except Exception as e:
        # If domain filtering fails, log and fall back to unfiltered search
        print(f"DEBUG: Error during standard semantic search (possibly domain filter): {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        st.warning(f"Domain filtering error: {str(e)}. Falling back to unfiltered search.")
        
        # Log the error
        with open(log_dir / "error_standard_search.json", "w") as f:
            json.dump({
                "error": str(e),
                "traceback": traceback.format_exc(),
                "filter": str(semantic_filter)
            }, f, indent=2)
        
        try:
            print("DEBUG: Falling back to unfiltered semantic search.")
            standard_results = db.similarity_search(processed_query, k=k, filter=None)
            print(f"DEBUG: Unfiltered fallback search returned {len(standard_results)} results.")
            
            # Log fallback search results
            log_documents(log_dir, "fallback_semantic_results", standard_results, {
                "fallback_reason": str(e),
                "count": len(standard_results)
            })
            
        except Exception as fallback_e:
            print(f"DEBUG: Error during unfiltered fallback search: {str(fallback_e)}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            st.error(f"❌ Critical search error: {fallback_e}")
            
            # Log the fallback error
            with open(log_dir / "error_fallback_search.json", "w") as f:
                json.dump({
                    "error": str(fallback_e),
                    "traceback": traceback.format_exc()
                }, f, indent=2)
                
            standard_results = []
    
    print("DEBUG: Starting combination and deduplication.")
    # Combine results, removing duplicates
    seen_content = set()
    combined_results = []
    
    # First add the metadata-filtered results (higher priority)
    for doc in metadata_results:
        content_hash = hash(doc.page_content)
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            combined_results.append(doc)
    
    print(f"DEBUG: Added {len(combined_results)} unique results from metadata search.")
    
    # Then add the semantic search results
    initial_combined_count = len(combined_results)
    for doc in standard_results:
        content_hash = hash(doc.page_content)
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            combined_results.append(doc)
            
    print(f"DEBUG: Added {len(combined_results) - initial_combined_count} unique results from standard search.")
    print(f"DEBUG: Total combined results before limiting to k: {len(combined_results)}")
    
    # Return the combined results, limited to k
    final_results = combined_results[:k]
    print(f"DEBUG: Returning final {len(final_results)} results after limiting to k={k}.")
    
    # Log the final combined results
    log_documents(log_dir, "final_combined_results", final_results, {
        "metadata_results_count": len(metadata_results),
        "standard_results_count": len(standard_results),
        "combined_count": len(combined_results),
        "final_count": len(final_results),
        "k_limit": k
    })
    
    # Log timing information
    with open(log_dir / "timing.json", "w") as f:
        json.dump({
            "start_time": query_log["start_time"],
            "end_time": time.time(),
            "duration": time.time() - query_log["start_time"]
        }, f, indent=2)
    
    return final_results
