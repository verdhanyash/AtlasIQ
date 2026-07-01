# AtlasIQ Agent Instructions

You are continuing development of **AtlasIQ**.

## Source of Truth

1. Read every file inside the `docs/` directory before starting any task.
2. Treat those documents as the project's constitution.
3. Never contradict or redesign the documented architecture.
4. If implementation and documentation disagree, stop and ask for clarification before changing either.

---

## Development Philosophy

1. Continue from the current repository state.
2. Prioritize maintainability, readability, and correctness over speed.
3. Do not over-engineer Version 1.
4. Prefer the simplest implementation that satisfies the documented architecture.
5. Extend existing modules before introducing new ones.

---

## Implementation Rules

1. Implement **one small, independently testable module at a time**.
2. Never implement multiple major modules in a single response.
3. Modify only the files required for the current task.
4. Never refactor unrelated code while implementing a feature.
5. If another module appears incorrect, explain the issue instead of changing it.

---

## Code Quality

Every implementation must:

* compile successfully
* integrate with the existing architecture
* include appropriate type hints
* include docstrings where appropriate
* include structured logging where appropriate
* include unit tests when applicable
* avoid hardcoded configuration values

Prefer production-quality code over quick prototypes.

---

## Architecture Rules

Do not:

* redesign the architecture
* introduce new top-level folders
* introduce new frameworks without clear justification
* create placeholder files, empty abstractions, or unused services
* implement future milestones

If a new abstraction or dependency is genuinely required:

1. Explain why the current architecture is insufficient.
2. Explain the trade-offs.
3. Wait for approval before introducing it.

---

## Completion Requirements

Before writing code:

* Briefly explain what will be implemented.
* List the files that will be created or modified.
* Explain how the module fits into the existing architecture.

After implementation:

* Summarize what was completed.
* Explain how it integrates with the project.
* Describe how it was tested.
* Identify the next logical module.
* Stop and wait for the next instruction.

---

## Goal

Build AtlasIQ incrementally as a production-inspired Enterprise Knowledge Platform.

Optimize for:

* clean architecture
* modularity
* testability
* explainability
* retrieval quality
* long-term maintainability

A complete, well-engineered Version 1 is more valuable than an incomplete Version 2.
