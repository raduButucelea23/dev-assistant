import streamlit as st
import pandas as pd
from typing import Dict, Any


def document_tracing_ui():
    """Display document tracing information in the UI."""
    # Remove redundant header
    # st.header("📚 Document Traceability")
    
    # Get DB manager
    db_manager = st.session_state.get("db_manager")
    if not db_manager:
        st.warning("Database not initialized.")
        return
    
    # Display statistics
    sources = db_manager.get_source_documents()
    domains = list(db_manager.tracking_index["domains"].keys())
    file_types = list(db_manager.tracking_index["file_types"].keys())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Source Documents", len(sources))
    with col2:
        st.metric("Domains", len(domains))
    with col3:
        st.metric("File Types", len(file_types))
    
    # Allow filtering by different dimensions
    tab1, tab2, tab3 = st.tabs(["By Source", "By Domain", "By File Type"])
    
    with tab1:
        if not sources:
            st.info("No source documents found in the tracking database.")
        else:
            selected_source = st.selectbox("Select Source Document", sources)
            if selected_source:
                documents = db_manager.get_documents_by_source(selected_source)
                st.write(f"Found {len(documents)} chunks from this source")
                
                # Display document details as dataframe
                if documents:
                    # Clean data for dataframe
                    df_data = []
                    for doc in documents:
                        df_data.append({
                            "Chunk ID": doc.get("chunk_id", "N/A"),
                            "File Type": doc.get("file_type", "Unknown"),
                            "Domain": doc.get("domain", "Unknown"),
                            "Embedding Date": doc.get("embedding_date", "Unknown"),
                            "Doc ID": doc.get("doc_id", "Unknown")[:8] + "..."  # Truncate ID for display
                        })
                    
                    if df_data:
                        st.dataframe(pd.DataFrame(df_data))
                        
                        # Allow viewing full details of a document
                        with st.expander("View Full Document Details"):
                            doc_to_view = st.selectbox(
                                "Select document to view details", 
                                range(len(documents)), 
                                format_func=lambda i: f"Chunk {documents[i].get('chunk_id', 'N/A')}"
                            )
                            st.json(documents[doc_to_view])
    
    with tab2:
        if not domains:
            st.info("No domains found in the tracking database.")
        else:
            selected_domain = st.selectbox("Select Domain", domains)
            if selected_domain:
                documents = db_manager.get_documents_by_domain(selected_domain)
                st.write(f"Found {len(documents)} chunks in this domain")
                
                # Display document info grouped by source
                sources_in_domain = {}
                for doc in documents:
                    source = doc.get("source_path", "Unknown")
                    if source not in sources_in_domain:
                        sources_in_domain[source] = []
                    sources_in_domain[source].append(doc)
                
                for source, docs in sources_in_domain.items():
                    with st.expander(f"{source} ({len(docs)} chunks)"):
                        # Clean data for dataframe
                        df_data = []
                        for doc in docs:
                            df_data.append({
                                "Chunk ID": doc.get("chunk_id", "N/A"),
                                "File Type": doc.get("file_type", "Unknown"),
                                "Embedding Date": doc.get("embedding_date", "Unknown"),
                                "Doc ID": doc.get("doc_id", "Unknown")[:8] + "..."  # Truncate ID for display
                            })
                        
                        if df_data:
                            st.dataframe(pd.DataFrame(df_data))
    
    with tab3:
        if not file_types:
            st.info("No file types found in the tracking database.")
        else:
            selected_type = st.selectbox("Select File Type", file_types)
            if selected_type:
                documents = db_manager.get_documents_by_type(selected_type)
                st.write(f"Found {len(documents)} chunks of this file type")
                
                # Simple table view of documents
                if documents:
                    # Group by domain for better organization
                    domains_in_type = {}
                    for doc in documents:
                        domain = doc.get("domain", "Unknown")
                        if domain not in domains_in_type:
                            domains_in_type[domain] = []
                        domains_in_type[domain].append(doc)
                    
                    for domain, docs in domains_in_type.items():
                        with st.expander(f"{domain} ({len(docs)} chunks)"):
                            # Clean data for dataframe
                            df_data = []
                            for doc in docs:
                                df_data.append({
                                    "Filename": doc.get("filename", "Unknown"),
                                    "Chunk ID": doc.get("chunk_id", "N/A"),
                                    "Source Path": doc.get("source_path", "Unknown"),
                                    "Embedding Date": doc.get("embedding_date", "Unknown")
                                })
                            
                            if df_data:
                                st.dataframe(pd.DataFrame(df_data))


def format_trace_info(trace_info: Dict[str, Any]) -> str:
    """Format trace info for display in results."""
    if not trace_info:
        return "Unknown source"
    
    source = trace_info.get("filename", "Unknown")
    domain = trace_info.get("domain", "Unknown")
    file_type = trace_info.get("file_type", "Unknown")
    
    return f"{source} ({domain}, {file_type})" 