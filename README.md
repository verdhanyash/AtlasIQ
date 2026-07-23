# AtlasIQ 🧠⚡

> **Enterprise-Grade Continuous Knowledge Platform with Hybrid Retrieval, Hardware Acceleration, and Evidence-Backed Search.**

---

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16--alpine-336791.svg)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-v1.11.0-red.svg)](https://qdrant.tech/)
[![CUDA Accelerated](https://img.shields.io/badge/CUDA-Hardware%20Accelerated-green.svg)](https://developer.nvidia.com/cuda-zone)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Overview

**AtlasIQ** is a production-inspired, enterprise RAG (Retrieval-Augmented Generation) knowledge engine designed to eliminate organizational document silos. Rather than acting as a simple file-upload chatbot, AtlasIQ builds a continuous, deterministic knowledge layer across enterprise files (PDF, DOCX, Markdown, TXT).

It combines **Hybrid Vector + Lexical Search (Qdrant + BM25)**, **Reciprocal Rank Fusion (RRF)**, **BGE Cross-Encoder Reranking**, **NVIDIA Build API / Local Ollama LLM Providers**, and **NVIDIA CUDA GPU Hardware Acceleration** to deliver answers with deterministic, page-exact citations in milliseconds.

---

## ✨ Key Features

* 📄 **Multi-Format Ingestion:** Layout-aware document parsing via IBM Docling (PDF, DOCX, Markdown, TXT) with automatic page-number tracking.
* ⚡ **GPU CUDA Acceleration:** Hardware-accelerated embedding generation (`nomic-embed-text-v1.5`) and reranking on NVIDIA GPUs (RTX 3050+).
* 🔍 **Hybrid Retrieval Engine:** Combines Dense Vector Search (Qdrant) and Sparse Keyword Search (BM25) fused via Reciprocal Rank Fusion (RRF).
* 🎯 **Precision Reranking:** Two-stage retrieval powered by `BAAI/bge-reranker-v2-m3` cross-encoders to ensure context relevance.
* 🤖 **Multi-LLM Integration:** Direct integration with NVIDIA Build API (`Llama 3.3 70B`, `DeepSeek R1`, `Nemotron 70B`) with seamless offline fallback to local Ollama (`gemma3:4b`).
* 📌 **Page-Exact Citations:** Deterministic context extraction with source document filenames, chunk relevance scores, and page numbers.
* 🛡️ **Grounding & Guardrails:** Automated confidence scoring; returns strict refusal when evidence falls below precision thresholds to prevent LLM hallucinations.
* 👁️ **Liquid Glass UI:** Modern web dashboard built with glassmorphic design principles, custom dark theme, and Geist Mono typography for model selectors.
* 🔄 **Continuous Ingestion Watcher:** File-system folder watcher (`watched_documents/`) with automated SHA-256 change detection and incremental re-indexing.

---

## 🏛️ System Architecture

```mermaid
flowchart TB
    User([User / Web UI])

    subgraph EntryPoints["Ingestion Layer"]
        UploadAPI["POST /ingest/upload"]
        FolderWatcher["Folder Watcher<br/>(watched_documents/)"]
    end

    subgraph QueryEntry["Query Interface"]
        FrontendUI["Glassmorphic Frontend<br/>(localhost:8502)"]
        QueryAPI["POST /query"]
    end

    User -->|Upload Documents| EntryPoints
    User -->|Ask Questions| FrontendUI --> QueryAPI

    subgraph IngestionPipeline["Ingestion Pipeline"]
        direction TB
        Validator["1. Validator"] --> Metadata["2. Metadata Extraction"]
        Metadata --> ChangeDetect["3. Change Detector<br/>(SHA-256 Hash)"]
        ChangeDetect -->|NEW / MODIFIED| Parser["4. Docling Layout Parser"]
        ChangeDetect -->|UNCHANGED| Skip([Skip Processing])
        Parser --> Chunker["5. Recursive Chunker<br/>(800 chars / 100 overlap)"]
        Chunker --> Embedder["6. GPU Embedder<br/>(nomic-embed-text-v1.5)"]
    end

    UploadAPI --> Validator
    FolderWatcher -->|Auto-Detect| Validator

    subgraph StorageLayer["Storage Layer"]
        direction LR
        PostgreSQL[("PostgreSQL 16<br/>Metadata & Text Chunks")]
        Qdrant[("Qdrant Vector DB<br/>768-dim Embeddings")]
    end

    Embedder -->|Text & Metadata| PostgreSQL
    Embedder -->|Vector Embeddings| Qdrant

    subgraph RetrievalPipeline["Retrieval & Generation Stack"]
        direction TB
        QEmbed["Query Embedder"] --> Dense["Dense Vector Search<br/>(Qdrant)"] & BM25["Sparse BM25 Search<br/>(PostgreSQL)"]
        Dense --> RRF["Reciprocal Rank Fusion (RRF)"]
        BM25 --> RRF
        RRF --> Reranker["BGE Cross-Encoder Reranker<br/>(BAAI/bge-reranker-v2-m3)"]
        Reranker --> Hydrate["Hydrate Text Chunks"]
        Hydrate --> Prompt["Prompt Builder"]
        Prompt --> LLMProvider["LLM Engine<br/>(NVIDIA Build API / Ollama)"]
        LLMProvider --> Citation["Citation & Guardrail Processor"]
    end

    QueryAPI --> QEmbed
    Citation -->|Answer + Page Citations + Confidence| FrontendUI
```

---

## 🛠️ Technology Stack

| Layer | Technology | Function |
| :--- | :--- | :--- |
| **Backend API** | FastAPI + Uvicorn | Async Python backend with OpenAPI documentation & dependency injection. |
| **Frontend UI** | HTML5 / Vanilla CSS / JS | Custom glassmorphic interface with Geist Mono typography & dynamic rendering. |
| **Relational DB** | PostgreSQL 16 (SQLAlchemy) | Stores structured document records, text chunks, and metadata. |
| **Vector DB** | Qdrant v1.11 | High-performance vector engine for 768-dimensional dense retrieval. |
| **Embedder** | nomic-embed-text-v1.5 | 768-dim embedding model accelerated via PyTorch CUDA. |
| **Reranker** | BAAI/bge-reranker-v2-m3 | Cross-encoder model re-scoring candidate chunks for maximum precision. |
| **LLM Engine** | NVIDIA Build API & Ollama | `meta/llama-3.3-70b-instruct`, `deepseek-r1`, `nemotron-70b`, `gemma3:4b`. |
| **Doc Parser** | IBM Docling | Layout-aware document parser preserving headings, tables, and page boundaries. |
| **Compute** | NVIDIA PyTorch CUDA | Hardware GPU acceleration on local GPU compute (`cuda:0`). |
| **Containers** | Docker & Docker Compose | Multi-container orchestration for PostgreSQL, Qdrant, and Web services. |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python:** `3.11` or higher
- **Docker Desktop:** Installed and running
- **GPU (Optional):** NVIDIA GPU with CUDA support for hardware acceleration
- **API Key (Optional):** NVIDIA Build API key (configured in `.env`)

---

### 1. Clone the Repository & Configure Environment

```bash
git clone https://github.com/verdhanyash/AtlasIQ.git
cd AtlasIQ

# Create Python Virtual Environment
python -m venv .venv
.venv\Scripts\activate   # On Windows (or 'source .venv/bin/activate' on Linux/macOS)

# Install Dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```env
NVIDIA_API_KEY=nvapi-your-key-here
LLM_PROVIDER=nvidia
LLM_MODEL=meta/llama-3.3-70b-instruct
POSTGRES_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/atlasiq
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

---

### 2. Start Service Infrastructure (PostgreSQL & Qdrant)

Launch database containers using Docker Compose:

```bash
docker compose up -d
```

Verify service health:
```bash
docker compose ps
```

---

### 3. Launch AtlasIQ Platform

You can start the unified backend and frontend service using the included launcher:

```bash
# Automated Launcher
python start_atlasiq.py
```

Alternatively, run services individually:

```bash
# Terminal 1: Backend API (Port 8000)
python -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend Web Server (Port 8502)
python -m http.server 8502 --directory atlasiq/frontend/static
```

---

### 4. Access the Web Application

- **Web Dashboard:** `http://localhost:8502`
- **FastAPI OpenAPI Docs:** `http://localhost:8000/docs`
- **API Health Check:** `http://localhost:8000/health`

---

## 📡 REST API Documentation

### 1. Question Answering (RAG Search)
`POST /query`

**Request Body:**
```json
{
  "query": "What are the financial metrics for Q4?",
  "top_k": 5,
  "min_confidence_score": 0.015
}
```

**Response:**
```json
{
  "query": "What are the financial metrics for Q4?",
  "answer": "Based on the provided documents:\n- Q4 Revenue reached $45.2M (+14% YoY).\n- Operating Margin expanded to 28.5%.",
  "confidence_score": 0.892,
  "has_sufficient_evidence": true,
  "citations": [
    {
      "citation_id": 1,
      "document_id": "c59c130b-719b-5003-9f46-9f8a1fab6675",
      "filename": "Q4_Financial_Report.pdf",
      "page_number": 12,
      "snippet": "Q4 Revenue reached $45.2M...",
      "relevance_score": 0.941
    }
  ],
  "latency_ms": 1420
}
```

---

### 2. Ingest Document
`POST /ingest/upload` (Multipart Form Upload)

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/ingest/upload" \
  -F "file=@/path/to/document.pdf"
```

---

### 3. List Ingested Collections
`GET /ingest/documents?limit=50`

---

### 4. System Health & GPU Status
`GET /health`

**Response JSON:**
```json
{
  "status": "healthy",
  "checks": {
    "fastapi": true,
    "postgresql": true,
    "qdrant": true,
    "llm_provider": "nvidia",
    "llm_model": "meta/llama-3.3-70b-instruct",
    "config_valid": true
  },
  "timestamp": "2026-07-23T12:00:00.000000+00:00"
}
```

---

## 📂 Project Structure

```text
AtlasIQ/
├── atlasiq/
│   ├── backend/                 # FastAPI Application & API Routes
│   │   ├── api/                 # /query, /ingest, /health routes
│   │   ├── core/                # Config, Security, Exception Handlers
│   │   └── main.py              # Application Entrypoint & Lifecycle
│   ├── ingestion/               # Document Processing Pipeline
│   │   ├── parser.py            # IBM Docling Layout-Aware PDF/DOCX Parser
│   │   ├── chunker.py           # Recursive Text Chunker
│   │   ├── embedder.py          # GPU-Accelerated Nomic Embedder (CUDA)
│   │   ├── pipeline.py          # Orchestrator with Incremental Updates
│   │   └── watcher.py           # Directory Watcher (watched_documents/)
│   ├── retrieval/               # Hybrid Retrieval & QA Stack
│   │   ├── dense.py             # Qdrant Vector Retriever
│   │   ├── bm25.py              # Sparse Lexical BM25 Search
│   │   ├── hybrid.py            # Reciprocal Rank Fusion (RRF)
│   │   ├── reranker.py          # BAAI/bge-reranker-v2-m3 Cross-Encoder
│   │   ├── llm/                 # NVIDIA Build API & Ollama Providers
│   │   └── qa_pipeline.py       # End-to-End RAG Execution Engine
│   ├── database/                # Persistence Clients
│   │   ├── postgres_client.py   # Async PostgreSQL Client & Schema
│   │   └── qdrant_client.py     # Qdrant Vector Collection Client
│   └── frontend/
│       └── static/              # Glassmorphic Web App (index.html)
├── configs/
│   └── default.yaml             # Core Application Configuration
├── prompts/
│   ├── qa_prompt.txt            # Grounded QA System Instructions
│   └── citation_prompt.txt      # Deterministic Citation Generator
├── tests/                       # Unit & End-to-End Test Suite (240+ Tests)
├── watched_documents/           # Drop Folder for Auto-Ingestion
├── docker-compose.yml           # PostgreSQL + Qdrant Services
├── start_atlasiq.py             # One-Click Unified Launcher
├── pyproject.toml               # Python Dependencies & Tool Configs
└── README.md
```

---

## 🧪 Testing & Verification

Run the automated Pytest suite to verify system integrity:

```bash
# Run all unit and integration tests
pytest

# Verify GPU Hardware Acceleration
python -c "import torch; print('CUDA Available:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

---

## 👤 Author & Credits

- **Author:** Yash Verdhan Parihar
- **GitHub:** [@verdhanyash](https://github.com/verdhanyash)
- **Project:** AtlasIQ Enterprise Knowledge Platform

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
