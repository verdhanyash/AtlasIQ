# AtlasIQ - AI Agent Project Context

## Role

You are the lead software engineer for AtlasIQ.

Your responsibility is **NOT** to invent architecture.

Your responsibility is to implement the architecture described below.

If any requirement is ambiguous, preserve modularity and ask for clarification instead of making assumptions.

---

# Project Overview

AtlasIQ is an Enterprise Knowledge Platform.

It is **NOT** a chatbot.

It continuously ingests organizational knowledge, indexes documents, retrieves relevant information using modern information retrieval techniques, and generates evidence-backed answers using an LLM.

The project should demonstrate software engineering, machine learning, information retrieval, DevOps, and clean architecture.

---

# Core Philosophy

The LLM is replaceable.

The retrieval system is the core product.

Prioritize:

* Clean architecture
* Modularity
* Explainability
* Retrieval quality
* Extensibility

Never tightly couple components.

---

# Primary Objectives

Build a platform capable of:

* Continuous document ingestion
* Incremental indexing
* Hybrid Retrieval
* Reranking
* Evidence-backed answers
* Evaluation
* Analytics
* Future extensibility

---

# Architecture Principles

The project follows a layered architecture.

User

↓

Frontend

↓

FastAPI Backend

↓

Two independent pipelines

1. Document Ingestion

2. Question Answering

Both communicate through shared storage.

---

# Ingestion Pipeline

Pipeline:

Document

↓

Validation

↓

Parsing

↓

Metadata Extraction

↓

Chunking

↓

Embedding Generation

↓

Vector Storage

Responsibilities:

* Parse PDF, DOCX, Markdown, TXT
* Extract metadata
* Create semantic chunks
* Generate embeddings
* Store vectors
* Support incremental indexing

---

# Retrieval Pipeline

Question

↓

Hybrid Retrieval

↓

Reranker

↓

Prompt Construction

↓

LLM

↓

Answer

Responsibilities:

* Dense Retrieval
* BM25 Retrieval
* Reciprocal Rank Fusion
* Reranking
* Prompt Construction
* Citation Generation

---

# Folder Structure

atlasiq/

backend/

frontend/

ingestion/

retrieval/

evaluation/

analytics/

database/

configs/

prompts/

tests/

docs/

Only place logic inside its appropriate module.

---

# Technology Stack

Backend:

FastAPI

Frontend:

Streamlit

Database:

PostgreSQL

Vector Database:

Qdrant

Embeddings:

Nomic Embed

Retrieval:

Hybrid Retrieval

(Dense + BM25)

Reranker:

BGE Reranker

Generation:

Provider abstraction supporting:

* Ollama
* NVIDIA Build
* OpenAI

Containerization:

Docker

CI/CD:

GitHub Actions

Deployment:

Render

---

# AI Architecture

Never directly call an LLM.

Always go through

LLM Service

The application should never know which provider is being used.

Providers include:

* Ollama

* NVIDIA Build

* OpenAI

Future providers should require minimal code changes.

---

# Configuration

Never hardcode:

* model names

* chunk sizes

* overlap

* temperature

* top_k

* API URLs

Everything must be configurable.

---

# Coding Principles

Use:

* type hints

* docstrings

* logging

* dependency injection where appropriate

* service layer

Avoid:

* monolithic files

* duplicated logic

* hardcoded constants

* tightly coupled modules

---

# Design Principles

Every module must have one responsibility.

Parser should never generate embeddings.

Embedding module should never query the LLM.

LLM module should never communicate directly with Qdrant.

Maintain strict separation of concerns.

---

# Version 1 Scope

Implement:

* PDF ingestion

* Metadata extraction

* Chunking

* Embeddings

* Qdrant

* Hybrid Retrieval

* Reranking

* Prompt Builder

* LLM Service

* Citations

* Confidence

* Query Analytics

* Docker

---

# Future Scope

Architecture should allow future support for:

* Google Drive

* GitHub

* SharePoint

* Notion

* Websites

* Knowledge Graph

* Authentication

* RBAC

These should NOT be implemented in Version 1.

---

# Engineering Goals

The project should feel like production software.

It should be:

* Modular

* Extensible

* Testable

* Well documented

* Dockerized

* CI/CD ready

---

# Project Differentiators

AtlasIQ should be engineered around these ideas.

1. Continuous Knowledge Ingestion

2. Incremental Indexing

3. Explainable Retrieval

4. Knowledge Trust Engine

5. Retrieval Inspector

6. Retrieval Evaluation Dashboard

7. Knowledge Drift Detection

8. Semantic Versioning

9. Query Analytics

10. AtlasIQ Lab

11. Model Benchmark Dashboard

Not every feature belongs in Version 1, but architecture should allow future implementation.

---

# Expectations

Whenever implementing a module:

* Keep responsibilities small.

* Add meaningful comments.

* Write clean code.

* Follow SOLID principles where appropriate.

* Add unit tests.

* Do not introduce unnecessary frameworks.

* Explain engineering decisions when generating code.

Always optimize for maintainability over cleverness.



                                    User
                                      │
                                      ▼
                         ┌────────────────────────┐
                         │ Streamlit Frontend     │
                         │ Upload • Search • Lab  │
                         └────────────┬───────────┘
                                      │
                                      ▼
                         ┌────────────────────────┐
                         │    FastAPI Backend     │
                         └────────────┬───────────┘
                                      │
              ┌───────────────────────┴────────────────────────┐
              │                                                │
              ▼                                                ▼
     Document Ingestion                              Question Processing
              │                                                │
      Document Validator                             Query Analytics
              │                                                │
              ▼                                                ▼
      Document Parser                                Hybrid Retrieval
              │                                   (Dense + BM25 + RRF)
              ▼                                                │
      Metadata Service                                         ▼
              │                                           BGE Reranker
              ▼                                                │
      Change Detector                                          ▼
     (Incremental Indexing)                          Retrieval Inspector
              │                                                │
              ▼                                                ▼
      Semantic Chunker                                Prompt Service
              │                                                │
              ▼                                                ▼
      Embedding Model                                   LLM Service
              │                              (Ollama / NVIDIA / OpenAI)
              ▼                                                │
       Qdrant Vector DB                                       ▼
              │                                      Knowledge Trust Engine
              │                                                │
              └──────────────────────┬─────────────────────────┘
                                     ▼
                               PostgreSQL
                       Metadata • Analytics • Logs
                       Evaluations • Query History
                                     │
                                     ▼
                       Answer + Citations + Confidence


                     AtlasIQ Lab
                           │
      ┌────────────────────┼─────────────────────┐
      ▼                    ▼                     ▼
 Chunk Size Test    Embedding Comparison   Model Benchmark