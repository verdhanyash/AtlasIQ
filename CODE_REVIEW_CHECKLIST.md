# CODE_REVIEW_CHECKLIST.md

# AtlasIQ Code Review Checklist

This document defines the minimum quality standards for every implementation in AtlasIQ.

Every completed module should be reviewed against this checklist **before committing**.

The purpose is to ensure consistency, maintainability, and adherence to the documented architecture, regardless of which AI assistant or developer produced the code.

---

# 1. Architectural Review

Verify that the module:

* [ ] Has a single, well-defined responsibility.
* [ ] Matches the documented architecture.
* [ ] Does not perform responsibilities belonging to another module.
* [ ] Does not introduce unnecessary coupling.
* [ ] Does not redesign existing architecture.
* [ ] Fits naturally into the current project structure.

---

# 2. Separation of Concerns

Confirm the module only performs its intended responsibility.

Examples:

Validator:

* [ ] Validates files only.
* [ ] Does not parse documents.
* [ ] Does not compute hashes.
* [ ] Does not generate embeddings.
* [ ] Does not communicate with databases.
* [ ] Does not call an LLM.

Parser:

* [ ] Parses documents only.
* [ ] Does not validate files.
* [ ] Does not chunk text.
* [ ] Does not generate embeddings.
* [ ] Does not persist data.

Chunker:

* [ ] Splits text only.
* [ ] Does not generate embeddings.
* [ ] Does not communicate with databases.
* [ ] Does not call the LLM.

Every module should have one clear responsibility.

---

# 3. Configuration Review

Verify that:

* [ ] No configurable value is hardcoded.
* [ ] Model names come from configuration.
* [ ] Database URLs come from configuration.
* [ ] API keys come from environment variables.
* [ ] Chunk size comes from configuration.
* [ ] Chunk overlap comes from configuration.
* [ ] File size limits come from configuration.
* [ ] Watch folder paths come from configuration.

Hardcoded values should only exist if they are true constants that are unlikely to change.

---

# 4. Code Quality

Verify:

* [ ] Code is readable.
* [ ] Functions are reasonably small.
* [ ] Variable names are meaningful.
* [ ] No duplicated logic.
* [ ] No dead code.
* [ ] No unused imports.
* [ ] No unnecessary abstractions.
* [ ] No premature optimization.

Prefer clarity over cleverness.

---

# 5. Python Best Practices

Verify:

* [ ] Type hints are present.
* [ ] Public functions include docstrings.
* [ ] Exceptions are meaningful.
* [ ] Logging is used where appropriate.
* [ ] Constants are named.
* [ ] Magic numbers are avoided unless justified.

---

# 6. Testing

Confirm:

* [ ] Unit tests exist.
* [ ] Existing tests still pass.
* [ ] Edge cases are covered.
* [ ] Failure cases are tested.
* [ ] Happy path is tested.

The module should be independently testable.

---

# 7. Performance Review

Verify:

* [ ] No obvious performance bottlenecks.
* [ ] Appropriate data structures are used.
* [ ] Expensive work is not repeated unnecessarily.
* [ ] Resource usage is reasonable for Version 1.

Do not optimize prematurely.

---

# 8. Maintainability

Verify:

* [ ] The implementation is easy to understand.
* [ ] Another developer could extend it.
* [ ] Dependencies are minimized.
* [ ] Interfaces are clean.
* [ ] The implementation is modular.

---

# 9. Version 1 Scope

Confirm that the implementation does not introduce:

* [ ] Authentication
* [ ] OCR
* [ ] Microservices
* [ ] Kafka
* [ ] Kubernetes
* [ ] Knowledge Graph
* [ ] Fine-tuning
* [ ] Multi-agent systems
* [ ] SharePoint integration
* [ ] Notion integration
* [ ] Google Drive integration

Unless explicitly requested later.

---

# 10. Final Review Questions

Before committing, answer these questions:

1. Does this module have exactly one responsibility?

2. Does it follow the documented architecture?

3. Is every configurable value externalized?

4. Can it be tested independently?

5. Does it introduce unnecessary complexity?

6. Would another engineer understand this implementation after reading it once?

7. Is this implementation appropriate for Version 1?

If any answer is **No**, revise the implementation before committing.

---

# Definition of Done

A module is considered complete only if:

* The implementation matches the documented architecture.
* The code passes all tests.
* The module is independently testable.
* The implementation satisfies this checklist.
* The module integrates cleanly with the existing system.
* The code is ready to commit without further architectural changes.
