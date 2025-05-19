# Automotive Dev Assistant

## Summary

Dev Assistant is an AI-powered chatbot that provides specialized knowledge assistance for automotive documentation. It uses Retrieval-Augmented Generation (RAG) to intelligently search through and answer questions about various automotive documents in multiple formats (.json, .arxml, .odx, .pdf, .md, .csv, .xlsx).

This project is based on the [MWC25-AI-Chatbot](https://github.com/isi-mube/MWC25-AI-Chatbot) repository. Special thanks to the original developers for providing the foundation for this RAG application.

## Setup & Running Instructions

### Option 1: Using Docker (Recommended)

1. **Prerequisites:**
   - Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) on your system
   - Clone the repository: `git clone <repository-url>`

2. **API Configuration:**
   - Create a `.env` file in the project root with your API keys:
   ```
   # Required for OpenAI models
   OPENAI_API_KEY=your_openai_key_here
   
   # Required for HuggingFace Hub models
   HUGGINGFACE_API_TOKEN=your_huggingface_token_here
   ```

3. **Running with Docker Compose:**
   ```bash
   # Build and start the application
   docker-compose build
   docker-compose up
   ```

4. **Access the Application:**
   - Open your browser and navigate to: `http://localhost:8502`

For more detailed Docker instructions, see [DOCKER.md](DOCKER.md).

### Option 2: Using Conda

1. **Prerequisites:**
   - Install [Conda](https://docs.conda.io/en/latest/miniconda.html) on your system
   - Clone the repository: `git clone <repository-url>`

2. **Environment Setup:**
   ```bash
   # Create and activate the conda environment from environment.yml
   conda env create -f environment.yml
   
   # Activate the environment
   conda activate auto-dev
   ```

3. **API Configuration:**
   - Create a `.env` file as described in Option 1

4. **Running the Application:**
   ```bash
   # Make sure you have activated the conda environment
   conda activate auto-dev
   
   # Launch the application
   streamlit run app/main.py
   ```

5. **Rebuilding the Database (if needed):**
   - Use the "Rebuild Database" button in the UI when adding new documents

## Technical Summary

- **Application Framework:** Streamlit web application
- **Python Backend:** Coordinates the entire RAG process using Langchain and custom code
- **Project Type:** Retrieval-Augmented Generation (RAG) chatbot for automotive documentation in various formats
- **Two-stage AI Process:** Uses separate models for embedding/retrieval and response generation
- **Embedding Models:** 
  - OpenAI's text-embedding-3-large
  - HuggingFace's BAAI/bge-large-en-v1.5 (default) and Alibaba-NLP/gte-large-en-v1.5
- **Large Language Models:** 
  - OpenAI's gpt-4o-mini
  - HuggingFace's meta-llama/Llama-3.3-70B-Instruct (default), mistralai/Mistral-7B-Instruct-v0.3, and tiiuae/falcon-40b-instruct
- **Vector Database:** ChromaDB with persistent storage
- **Data Organization:** 
  - Semantically organized by domains (requirements, catalogues, standards)
  - Each domain contains files of various formats (pdf, json, arxml, odx, csv, etc.)
  - Enhanced metadata with domain-specific context
- **Document Processing:** 
  - PyPDFLoader for extracting text from PDFs
  - Custom JSON processing with metadata extraction
  - XML-based processing for ARXML (AUTOSAR) and ODX (diagnostic) files
  - Signal Database JSON processing with specialized metadata extraction
  - FMEA (Failure Mode and Effects Analysis) document processing
  - TARA (Threat Assessment and Risk Analysis) document processing
  - Support for markdown, CSV, and Excel documents
  - Recursive directory scanning to process files in subdirectories
- **Text Chunking:** CharacterTextSplitter with a chunk size of 2000 and 200 character overlap
- **Retrieval Strategy:** Hybrid search combining technical term extraction, metadata filtering and semantic vector similarity
- **Context Utilization:** Uses the top 5 retrieved documents as context for the LLM
- **Caching Strategy:** Uses Streamlit's `cache_resource` for document loading and embedding
- **Cached Document Processing:** The document loading and embedding happens only once at startup
- **Error Handling:** Database rebuilding mechanism if the existing ChromaDB appears corrupted
- **Stateless Processing:** Each query is processed independently without memory of previous interactions
- **No Chat History in Context:** Previous Q&A pairs are not included in the prompt to the LLM
- **Source Attribution:** Displays up to 5 source references with detailed metadata
- **Environmental Setup:** 
  - `dotenv` for local API key management
  - Support for Streamlit Secrets in production
- **Response Format:** Structured output including the answer, key insights, and source information
- **User Interface:** 
  - Chat interface with message history persistence
  - Custom styling with Comic Sans font and pastel colors
  - Logo and title display

## Directory Structure

```
.
├── app/                     # Main application code
│   ├── chroma_db/           # Vector database (created at runtime)
│   ├── components/          # UI components 
│   └── main.py              # Main application entry point
├── data/                    # Data organized by semantic domains
│   ├── requirements/        # Functional and non-functional requirements, specifications, and acceptance criteria
│   ├── catalogues/          # Signal definitions and diagnostic services including AUTOSAR (.arxml), ODX (.odx), and CAN database (.dbc) files
│   ├── standards/           # Industry and OEM-specific standards and regulatory documentation
│   └── README.md            # Documentation of data organization
├── images/                  # Application images and assets
├── environment.yml          # Conda environment configuration
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker configuration
└── README.md                # This file
```

## Semantic Data Organization

The data is organized by semantic domains rather than file types to improve retrieval relevance:

```
data/
├── requirements/           # Functional and non-functional requirements, specifications, and acceptance criteria
│   ├── *.md                # Markdown documentation
│   ├── fmea-*.json         # FMEA (Failure Mode and Effects Analysis) JSON files
│   ├── tara-*.json         # TARA (Threat Assessment and Risk Analysis) JSON files
│   └── source-xls/         # Source Excel files for requirements
├── catalogues/             # Signal definitions and diagnostic services including AUTOSAR, ODX, and CAN database files
│   ├── *.arxml             # AUTOSAR XML files
│   ├── *.odx-c             # ODX diagnostic files
│   ├── signal*.json        # Signal database JSON files
│   └── dbc/                # DBC CAN database files
├── standards/              # Industry and OEM-specific standards and regulatory documentation
│   └── *.pdf               # PDF format documentation
```

This approach provides better context for RAG retrieval by grouping related documents together regardless of format.

## Document Preparation

To add new documents to the system:
1. Identify the appropriate semantic domain for your document (requirements, catalogues, or standards)
2. Place the document directly in the corresponding domain directory or in an appropriate subdirectory
3. Supported file formats:
   - PDF (*.pdf) - Standards and documentation
   - JSON (*.json) - Interface definitions
   - Signal Database JSON (signal*.json) - Signal definitions and interface specifications
   - FMEA JSON (fmea-*.json) - Failure Mode and Effects Analysis documents
   - TARA JSON (tara-*.json) - Threat Assessment and Risk Analysis documents
   - ARXML (*.arxml) - AUTOSAR interface definitions
   - ODX (*.odx, *.odx-c) - Diagnostic interface definitions
   - Markdown (*.md) - Documentation
   - Excel (*.xlsx, *.xls) - Structured data
   - CSV (*.csv) - Tabular data
4. Rebuild the database using the "Rebuild Database" button in the UI

## Model Configuration

The application supports two types of models:

### Embedding Models

- **OpenAI**: Uses OpenAI's API for generating embeddings
  - Models: text-embedding-3-large

- **HuggingFace (Local)**: Runs models locally on your machine
  - Models: 
    - BAAI/bge-large-en-v1.5 (default, dimension: 1024)
    - Alibaba-NLP/gte-large-en-v1.5 (dimension: 1024)

### LLM Models

- **OpenAI**: Uses OpenAI's API for generating responses
  - Models: gpt-4o-mini

- **HuggingFace (API)**: Uses the HuggingFace Hub Inference API
  - Models:
    - meta-llama/Llama-3.3-70B-Instruct (default)
    - mistralai/Mistral-7B-Instruct-v0.3
    - tiiuae/falcon-40b-instruct

### Switching Models

The application uses the default configuration as follows:
- Embedding Provider: openai
- Embedding Model: text-embedding-3-large
- LLM Provider: openai
- LLM Model: gpt-4o-mini

To change models, modify the appropriate session state variables in the main.py file or through the Streamlit session state.