FROM continuumio/miniconda3:latest

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential gcc

# Copy environment file
COPY environment.yml /app/

# Create conda environment from the file
RUN conda env create -f environment.yml

# Set up shell to use conda environment by default
SHELL ["/bin/bash", "--login", "-c"]
RUN echo "conda activate auto-dev" >> ~/.bashrc

# Copy application code
COPY . /app/

# Create entrypoint script to ensure conda environment is activated
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'source ~/.bashrc' >> /app/entrypoint.sh && \
    echo 'conda activate auto-dev' >> /app/entrypoint.sh && \
    echo 'exec "$@"' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Set the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command - runs the Streamlit app with custom URL display
CMD ["python", "-m", "streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.serverAddress=localhost", "--browser.serverPort=8502"] 