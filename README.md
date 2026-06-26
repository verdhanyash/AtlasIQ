
# AtlasIQ

> **A continuous knowledge platform for intelligent document discovery, retrieval, and evidence-backed search.**

AtlasIQ is an enterprise-inspired knowledge platform designed to solve a common problem: **organizational knowledge is constantly growing, changing, and becoming difficult to search.**

Instead of acting as another document chatbot, AtlasIQ continuously builds and maintains a searchable knowledge layer from documents, allowing users to ask natural language questions and receive answers backed by relevant evidence.

---

## Why AtlasIQ?

Most document search systems require users to manually upload files and rely solely on vector search.

AtlasIQ focuses on the **entire knowledge lifecycle**:

* Continuous document ingestion
* Incremental indexing
* Intelligent retrieval
* Evidence-backed responses
* Knowledge analytics
* Evaluation and monitoring

The goal is to build a platform that can evolve into an enterprise knowledge system rather than a single-purpose chatbot.

---

# Core Capabilities

### Knowledge Ingestion

* Multi-format document support (PDF, DOCX, Markdown, TXT)
* Automatic document parsing
* Metadata extraction
* Continuous folder monitoring
* Incremental indexing

---

### Knowledge Retrieval

* Hybrid Retrieval (Semantic + Keyword)
* Context-aware search
* Intelligent reranking
* Metadata filtering
* Multi-document reasoning

---

### Knowledge Exploration

* Natural language search
* Source citations
* Confidence scoring
* Document comparison
* Explainable retrieval

---

### Platform Observability

* Query analytics
* Retrieval evaluation
* Structured logging
* Health monitoring

---

# System Architecture

```text
                                  ┌────────────────────────────┐
                                  │           User             │
                                  └─────────────┬──────────────┘
                                                │
                                     Natural Language Query
                                                │
                                                ▼
                          ┌─────────────────────────────────────┐
                          │      Streamlit User Interface       │
                          │ Upload • Search • Analytics • Eval  │
                          └─────────────────┬───────────────────┘
                                            │
                                            ▼
                           ┌──────────────────────────────────┐
                           │         FastAPI Backend          │
                           └───────┬───────────┬──────────────┘
                                   │           │
                    ┌──────────────┘           └──────────────┐
                    ▼                                         ▼
          Ingestion Pipeline                        Query Processing
                    │                                         │
      ┌─────────────┴──────────────┐               ┌──────────┴──────────┐
      │                            │               │                     │
      ▼                            ▼               ▼                     ▼
Document Parser             Metadata Engine   Hybrid Retrieval      Query Logger
      │                            │        (Dense + BM25)              │
      ▼                            │               │                    ▼
Chunking Engine                    │               ▼              PostgreSQL
      │                            │          Reranker
      ▼                            │               │
Embedding Model                    │               ▼
      │                            └────────► Prompt Builder
      ▼                                            │
   Qdrant Vector DB                                ▼
                                         LLM Provider Interface
                                                   │
                                                   ▼
                                   Answer + Citations + Confidence
```

---

# Project Structure

```text
atlasiq/

├── backend/
├── frontend/
├── ingestion/
├── retrieval/
├── evaluation/
├── analytics/
├── database/
├── tests/
├── docs/
│   ├── architecture.md
│   ├── srs.md
│   ├── api-design.md
│   ├── roadmap.md
│   └── decisions.md
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# Technology Stack

| Layer            | Technology                      |
| ---------------- | ------------------------------- |
| Backend          | FastAPI                         |
| Frontend         | Streamlit                       |
| Database         | PostgreSQL                      |
| Vector Database  | Qdrant                          |
| Retrieval        | Hybrid Retrieval (Dense + BM25) |
| Reranking        | BGE Reranker                    |
| Embeddings       | Nomic Embed                     |
| Document Parsing | Docling                         |
| Containerization | Docker                          |
| CI/CD            | GitHub Actions                  |
| Deployment       | Render                          |

---

# Development Roadmap

## Version 1 — Internship Release

* Multi-format document ingestion
* Continuous folder monitoring
* Incremental indexing
* Hybrid retrieval
* Natural language search
* Source citations
* Confidence scoring
* Document comparison
* Analytics dashboard
* Evaluation dashboard
* Docker deployment

---

## Future Roadmap

* Google Drive connector
* GitHub repository indexing
* Website ingestion
* Authentication
* Knowledge graph
* Enterprise connectors
* Cloud-native deployment
* Advanced retrieval optimization

---

# Design Principles

AtlasIQ is built around four engineering principles:

* **Knowledge should stay up to date.**
* **Answers should be backed by evidence.**
* **Search should understand both keywords and meaning.**
* **The system should be modular and easy to extend.**

---

# Current Status

🚧 Active Development

AtlasIQ is currently being developed as part of a software engineering and machine learning internship, with a focus on building a production-inspired knowledge platform using modern information retrieval techniques.

---

# License

MIT License
