# AI CV Processing Platform

This project is currently under active development and **is considered a work in progress**.

## Overview
A recruitment intelligence platform designed for automated CV processing. The system handles PDF uploads, extracts candidate data using AI, and performs semantic indexing for context-aware talent searching.

## Tech Stack
* Framework: FastAPI
* Database: PostgreSQL with pgvector extension
* ORM: SQLAlchemy
* Background Tasks: Taskiq with Redis broker
* AI/LLM: Ollama (Embeddings and Data Extraction)
* Storage: AWS S3 / MinIO
* Migrations: Alembic

## Development Setup
Currently, the services must be started manually. Docker integration is planned for future updates.

### Running Core API
Navigate to the core service directory and run:
```bash
uv run uvicorn src.main:app --env-file ../../.env --reload
```

### Running Background Worker
Navigate to the worker service directory and run:
```bash
uv run --env-file ../../.env taskiq worker src.main:broker
```

## Core Functionality
* Automated Parsing: Extracts structured data from PDF resumes using LLMs.
* Vector Search: Enables semantic search of candidates based on skills and experience.
* Asynchronous Pipeline: Offloads heavy processing to background workers to ensure API responsiveness.
* Deduplication: Uses content-aware hashing to prevent redundant processing of identical documents.