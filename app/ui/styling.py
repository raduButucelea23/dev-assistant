import streamlit as st


def apply_styling():
    """Apply custom styling to the Streamlit application.
    
    This function applies a uniform white background to all components
    including the sidebar and chat input area.
    """
    
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
            background-color: white !important;
        }
        
        .stChatMessage {
            border-radius: 15px;
        }
        
        /* Custom color scheme with uniform white background */
        .main {
            background-color: white;
        }
        
        .stApp {
            background-color: white;
        }
        
        .css-1v3fvcr {
            background-color: white;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: white !important;
        }
        
        .css-6qob1r {
            background-color: white !important;
        }
        
        /* Chat input container styling */
        .css-1x8cf1d {
            background-color: white !important;
        }
        
        /* Eliminate any dark backgrounds */
        .css-1adrfps {
            background-color: white !important;
        }
        
        .css-1v3fvcr {
            background-color: white !important;
        }
        
        .css-wjbhl0, .css-12oz5g7 {
            background-color: white !important;
        }
        
        /* Chat input field */
        .stChatFloatingInputContainer, 
        [data-testid="stChatInput"], 
        .stChatInput, 
        div[data-baseweb="textarea"] {
            background-color: white !important;
            border: 1px solid #ccc !important;
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


def format_user_message(message):
    """Format a user message with custom styling.
    
    Args:
        message: User message text
        
    Returns:
        Formatted HTML for the user message
    """
    return f'<div class="user-message">{message}</div>'


def format_assistant_message(message):
    """Format an assistant message with custom styling.
    
    Args:
        message: Assistant message text
        
    Returns:
        Formatted HTML for the assistant message
    """
    return f'<div class="assistant-message">{message}</div>'
