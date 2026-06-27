# Engineering Guidelines

## General Principles

This repository should resemble production software.

Every module should have one responsibility.

Always optimize for maintainability over cleverness.

Never sacrifice readability for shorter code.

Prefer explicit code over magic.

---

## Architecture

Use Clean Architecture.

Business logic must never depend on UI.

Business logic must never depend on LLM providers.

Business logic must never depend on database implementations.

Dependencies should always point inward.

---

## Folder Rules

Every folder owns one concern.

backend/

API only.

ingestion/

Parsing, metadata, validation, chunking.

retrieval/

Hybrid retrieval and reranking only.

evaluation/

Metrics and benchmarking.

analytics/

Query analytics.

database/

Database clients.

Never violate folder boundaries.

---

## Coding Standards

Use

- Python 3.12+

- Type hints

- Dataclasses where appropriate

- Pydantic

- Logging

- Dependency Injection

Avoid

- Global variables

- Circular imports

- Long functions

- Files over ~400 lines

- Hardcoded paths

---

## Error Handling

Never silently ignore errors.

Raise meaningful exceptions.

Log all unexpected failures.

Return meaningful API responses.

---

## Documentation

Every public function requires:

- docstring

- parameters

- return type

Every module should contain a short explanation.

---

## Testing

Every module should include tests.

Parser

Chunker

Retriever

API

Evaluation

Coverage should focus on business logic.

---

## Git

Use Conventional Commits.

feat:

fix:

docs:

refactor:

test:

Never commit broken code.

---

## AI Agent Rules

Do not introduce unnecessary frameworks.

Do not change architecture without permission.

Do not replace chosen technologies.

Do not invent abstractions unless justified.

Always explain major engineering decisions.