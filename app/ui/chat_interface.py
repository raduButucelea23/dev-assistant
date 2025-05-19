import streamlit as st
from typing import List, Dict, Any, Optional
from openai import OpenAI

from retrieval.query_preprocessing import preprocess_query
from retrieval.hybrid_search import hybrid_search
from ui.styling import format_user_message, format_assistant_message


def initialize_chat_state():
    """Initialize the chat state in session state if it doesn't exist.
    
    This sets up the conversation history and other necessary state variables.
    """
    if "messages" not in st.session_state:
        st.session_state["messages"] = []


def display_chat_history():
    """Display the chat history with custom styling.
    
    This renders all previous messages in the conversation.
    """
    for message in st.session_state["messages"]:
        role_class = "user-message" if message["role"] == "user" else "assistant-message"
        with st.chat_message(message["role"]):
            st.markdown(f"<div class='{role_class}'>{message['content']}</div>", unsafe_allow_html=True)


def process_query(query: str, vector_db: Any) -> Optional[str]:
    """Process a user query and generate a response.
    
    This function:
    1. Preprocesses the query
    2. Retrieves relevant documents
    3. Formats the context
    4. Generates a response using OpenAI

    Args:
        query: User query text
        vector_db: Vector database for document retrieval
        
    Returns:
        Generated response text or None if processing fails
    """
    if not vector_db:
        return "❌ No document database available. Please rebuild the index."

    # Preprocess the query
    processed_query = preprocess_query(query)
    
    # Retrieve relevant documents
    retrieved_docs = hybrid_search(vector_db, processed_query, query, k=20)
    
    if not retrieved_docs:
        return "❌ No relevant information found in the knowledge base."
    
    # Format source information
    source_info_list = []
    for i, doc in enumerate(retrieved_docs[:5]):
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
    
    # Combine context from top documents
    context_text = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs[:5]])
    
    # Create a prompt for the model
    # System message to set context and expectations
    system_message = """You are Auto-Dev-Assistant, an AI designed to help with automotive software development questions.
    You have access to a knowledge base of technical documentation. Answer the user's question based only on the provided context.
    Be detailed and technical but easy to understand. If the answer is not in the context, say you don't know.
    Format your response in markdown with headings, bullet points, and code blocks as appropriate.
    Always mention your sources at the end of your response."""
    
    # Format the prompt with context
    prompt = f"""
    {system_message}
    
    Here is information from the knowledge base that might be relevant:
    
    {context_text}
    
    User Question: {query}
    
    Please provide a detailed answer based on the provided information, formatting your response with markdown where appropriate.
    Include a "Sources" section at the end with citations to the reference materials.
    """
    
    # Call OpenAI API to generate response
    try:
        # Get API key from session state
        api_key = st.session_state.get("openai_api_key")
        if not api_key:
            # Try to get from environment
            from dotenv import load_dotenv
            import os
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Try to get from Streamlit secrets
                try:
                    api_key = st.secrets["OPENAI_API_KEY"]
                except:
                    return "❌ OpenAI API key not found. Please provide your API key in the sidebar."
        
        client = OpenAI(api_key=api_key)
        
        # Model parameters
        model_params = {
            'model': 'gpt-4o-mini',  # Use the specified model
            'temperature': 0.3,  # Lower temperature for more deterministic responses
            'max_tokens': 4000,
            'top_p': 0.85,
            'frequency_penalty': 0.5,
            'presence_penalty': 0.1
        }
        
        # Create the message list
        messages = [{'role': 'user', 'content': prompt}]
        
        # Call the API
        completion = client.chat.completions.create(
            messages=messages,
            **model_params,
            timeout=120
        )
        
        # Extract the response
        answer = completion.choices[0].message.content
        
        # Add source info to the response
        if not answer.lower().endswith("sources:") and "sources:" not in answer.lower():
            answer += f"\n\n**Sources:**\n{source_info}"
        
        return answer
    
    except Exception as e:
        return f"❌ Error generating response: {str(e)}"


def handle_user_input():
    """Handle user input from the chat interface.
    
    Gets the user query, displays it, processes it, and displays the response.
    """
    user_question = st.chat_input("Ask me anything about automotive development...")
    
    if user_question:
        # Add user message to chat history
        st.session_state["messages"].append({"role": "user", "content": user_question})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(format_user_message(user_question), unsafe_allow_html=True)
        
        # Process the query
        with st.spinner("Thinking... 🤔"):
            # Get vector database from session state
            vector_db = st.session_state.get("vector_db")
            
            # Generate response
            answer = process_query(user_question, vector_db)
        
        # Add assistant message to chat history
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        
        # Display assistant message
        with st.chat_message("assistant"):
            st.markdown(format_assistant_message(answer), unsafe_allow_html=True)
