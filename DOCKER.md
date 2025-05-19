# Docker Setup for Auto-Dev Assistant

This document outlines how to run the Auto-Dev Assistant application using Docker Compose.

## Prerequisites

- Docker installed on your system
- Docker Compose installed on your system

## First-Time Setup

After cloning the repository:

1. Build the Docker image:
   ```bash
   docker-compose build
   ```

2. Start the application:
   ```bash
   docker-compose up
   ```

3. Access the application at:
   ```
   http://localhost:8502
   ```

## Subsequent Runs

1. Start the application:
   ```bash
   docker-compose up
   ```

2. To run in background mode:
   ```bash
   docker-compose up -d
   ```

3. To stop the application:
   ```bash
   docker-compose down
   ```

## Note

The application automatically mounts the following volumes to ensure your data is saved:
- `./data:/app/data`: For application data
- `./input-data:/app/input-data`: For input files