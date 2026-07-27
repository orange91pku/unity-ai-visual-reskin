# Changelog

## 0.3.0-visual-rag

- Added a separate local-first Visual RAG Python package and CLI.
- Added SQLite storage for theme/project assets, vectors, Unity usage evidence,
  mapping proposals and review evidence.
- Added deterministic per-sprite atlas extraction from Unity `.meta` rects.
- Added visual feature, palette, geometry, alpha, edge and perceptual-hash
  extraction.
- Added semantic text, image and hybrid retrieval with explainable score parts.
- Added read-only Unity project ingestion and versioned Project Brain context.
- Added pending-only mapping proposals that cannot authorize mutation.
- Added JSON schemas and synthetic automated tests.

## 0.2.0-portability

- Added deterministic scene/prefab scanning and semantic rule matching.
- Added ambiguity and unresolved-destination gates.
- Added SHA-256 transactional backup, apply, verification and auto-rollback.
- Added guarded Theme Pack `.meta` hashes and idempotent no-op apply.
- Added last-transaction rollback.
- Connected scan/apply/rollback actions to the Editor Workbench.
- Added a clean-project portability fixture and automated gate runner.

## 0.1.0-foundation

- Introduced Core / Theme Pack / Project Adapter boundaries.
- Added stable semantic-role vocabulary and versioned JSON contracts.
- Added theme/project discovery and validation in a Unity Editor window.
- Added the first 300Mind theme pack.
- Added the PuzzleDrop adapter and production-scene scope.
- Documented migration, authoring, storage, versioning, and safety gates.
