import streamlit as st
import traceback
from app.retrieval.query_preprocessing import extract_technical_terms


def hybrid_search(db, processed_query, original_query, k=20):
    """Perform hybrid search combining keyword filtering with vector similarity.
    
    This approach improves retrieval by:
    1. First attempting metadata filtering for exact matches
    2. Falling back to semantic search if metadata filtering returns too few results
    3. Combining results for a more comprehensive set of relevant documents
    4. Applying domain filtering if specified in the session state
    """
    print(f"DEBUG: hybrid_search started. Original query: '{original_query}', Processed query: '{processed_query}', k={k}")
    metadata_results = []
    
    # Check if domain filtering is enabled
    domain_filter = st.session_state.get("domain_filter")
    print(f"DEBUG: Domain filter: {domain_filter}")
    
    # Step 1: Try metadata filtering for exact matches with technical terms
    print("DEBUG: Starting metadata filtering step.")
    technical_terms = extract_technical_terms(original_query)
    print(f"DEBUG: Extracted technical terms: {technical_terms}")
    
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
                    metadata_results.extend(filtered_docs)
                except Exception as filter_err:
                    # If a particular filter fails, log and continue
                    print(f"DEBUG: Error during metadata filtered search for {current_filter}: {str(filter_err)}")
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                    continue
    else:
        print("DEBUG: No technical terms found for metadata filtering.")
    
    print(f"DEBUG: Metadata filtering step finished. Found {len(metadata_results)} potential results.")

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
        
    except Exception as e:
        # If domain filtering fails, log and fall back to unfiltered search
        print(f"DEBUG: Error during standard semantic search (possibly domain filter): {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        st.warning(f"Domain filtering error: {str(e)}. Falling back to unfiltered search.")
        try:
            print("DEBUG: Falling back to unfiltered semantic search.")
            standard_results = db.similarity_search(processed_query, k=k, filter=None)
            print(f"DEBUG: Unfiltered fallback search returned {len(standard_results)} results.")
        except Exception as fallback_e:
            print(f"DEBUG: Error during unfiltered fallback search: {str(fallback_e)}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            st.error(f"❌ Critical search error: {fallback_e}")
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
    return final_results
