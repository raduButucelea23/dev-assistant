import os
import sys
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
import pandas as pd
from pathlib import Path
from collections import Counter

# Load environment variables
load_dotenv()

def main():
    # Get the app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_db_dir = os.path.join(app_dir, "chroma_db")
    
    # Check if the chroma_db directory exists
    if not os.path.exists(chroma_db_dir):
        print("❌ The chroma_db directory does not exist.")
        return
    
    print(f"📁 ChromaDB directory: {chroma_db_dir}")
    
    try:
        # Initialize the ChromaDB client
        client = chromadb.PersistentClient(path=chroma_db_dir)
        
        # Get all collections (in v0.6.0 this returns just the names)
        collection_names = client.list_collections()
        print(f"📊 Found {len(collection_names)} collections in the database")
        
        if not collection_names:
            print("❌ No collections found in the database.")
            return
        
        # For each collection, get and display metadata
        for collection_info in collection_names:
            # In v0.6.0, collection_info is just the name string
            collection_name = collection_info
            print(f"\n📋 Collection: {collection_name}")
            
            # Get the collection object
            collection_data = client.get_collection(name=collection_name)
            all_items = collection_data.get()
            
            if not all_items or not all_items.get('metadatas'):
                print("  ❌ No documents found in this collection.")
                continue
                
            # Extract source files from metadata
            source_files = []
            domains = []
            
            for metadata in all_items.get('metadatas', []):
                if metadata and 'source' in metadata:
                    source = metadata['source']
                    source_files.append(source)
                
                if metadata and 'domain' in metadata:
                    domain = metadata['domain']
                    domains.append(domain)
            
            # Count and display unique source files
            unique_files = set(source_files)
            file_counter = Counter(source_files)
            
            print(f"  📄 Total documents: {len(all_items.get('ids', []))}")
            print(f"  🗂️ Unique source files: {len(unique_files)}")
            
            # Display domain distribution if available
            if domains:
                domain_counter = Counter(domains)
                print(f"  🔍 Domain distribution:")
                for domain, count in domain_counter.items():
                    print(f"    - {domain}: {count} documents")
            
            # Display the top files by document count
            print(f"  📈 Top files by document count:")
            for file, count in file_counter.most_common(10):  # Show top 10
                print(f"    - {file}: {count} documents")
            
            # Option to export detailed information to CSV
            export_to_csv = input("\nExport complete file list to CSV? (y/n): ").lower() == 'y'
            if export_to_csv:
                # Create a DataFrame with file info
                df = pd.DataFrame({
                    'source_file': source_files,
                    'domain': domains if domains else [''] * len(source_files)
                })
                
                # Add file count
                file_counts = df['source_file'].value_counts().reset_index()
                file_counts.columns = ['source_file', 'document_count']
                
                # Merge to get unique files with counts
                unique_df = df.drop_duplicates(subset=['source_file'])
                result_df = pd.merge(unique_df, file_counts, on='source_file')
                
                # Save to CSV
                csv_path = os.path.join(app_dir, "chroma_db_files.csv")
                result_df.to_csv(csv_path, index=False)
                print(f"✅ Exported file list to: {csv_path}")
    
    except Exception as e:
        print(f"❌ Error accessing ChromaDB: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 