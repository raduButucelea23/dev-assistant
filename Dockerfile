FROM continuumio/miniconda3:latest

WORKDIR /app

# Install build dependencies and clean up in single layer
RUN apt-get update && apt-get install -y build-essential gcc curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy environment file
COPY environment.yml /app/

# Create conda environment and clean up in single layer to reduce image size
RUN conda env create -f environment.yml && \
    conda clean -afy && \
    find /opt/conda/ -follow -type f -name '*.a' -delete && \
    find /opt/conda/ -follow -type f -name '*.pyc' -delete

# Set up shell to use conda environment by default
SHELL ["/bin/bash", "--login", "-c"]
RUN echo "conda activate auto-dev" >> ~/.bashrc

# Copy application code (excluding large files)
COPY app/ /app/app/
COPY *.py /app/

# Create data directories for CI test documents
RUN mkdir -p /app/data/catalogues /app/data/requirements

# Copy specific test documents for CI validation (from real data)
COPY data/catalogues/IVI_Diagnostic_Catalogue.odx-c /app/data/catalogues/
COPY data/catalogues/ivi_signal_database.json /app/data/catalogues/
COPY data/requirements/fmea-battery-management-display.json /app/data/requirements/
COPY data/requirements/IVI-system-spec-sysml3.md /app/data/requirements/
COPY data/requirements/tara-impact-analysis-battery-management.json /app/data/requirements/
COPY data/requirements/tara-risk-assessment-battery-management.json /app/data/requirements/
COPY data/requirements/tara-threat-scenarios-battery-management.json /app/data/requirements/

# Create entrypoint script to ensure conda environment is activated
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'source ~/.bashrc' >> /app/entrypoint.sh && \
    echo 'conda activate auto-dev' >> /app/entrypoint.sh && \
    echo 'exec "$@"' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Copy the startup script
COPY startup.py /app/

# Set the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command - use our startup script instead of direct Streamlit
CMD ["python", "startup.py"] 