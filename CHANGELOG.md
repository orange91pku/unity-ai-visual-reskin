# Changelog

## 0.4.1

- Added no-clone Unity Package Manager installation through tagged Git URLs.
- Published stable UPM identities under `com.heycici.visual-reskin`.
- Synchronized Core, Theme Pack, Project Adapter, Python package and manifest
  versions.
- Added direct UPM URLs, project `manifest.json` examples, update/uninstall
  guidance and an automated remote-install verification workflow.

## 0.4.0

- Added approval-gated raster materialization, transactional apply and exact
  rollback.
- Added Unity identity gates for `.meta`, GUID, dimensions, alpha masks and
  serialized reference counts.
- Added `setting -> settings` semantic normalization for conservative icon
  matching.
- Excluded unreferenced and Editor-only images from safe-default mapping
  proposals, with explicit discovery overrides and regression coverage.
- Documented Windows/Unity automation findings from the HungryAnts validation.
- Added public Project Brain integration, AI-agent discovery, CI, contribution,
  licensing and security documentation.

## 0.3.1 - Visual RAG bridge

- Fixed Project Brain context ingestion when the same visual asset/fileID is
  used by multiple hierarchy or component locations.
- Upgraded the local database to schema v2 with a lossless v1 migration.
- Preserved property name, hierarchy, component, evidence kind and aggregated
  reference counts in the Visual RAG usage graph.
- Made Project Brain context authoritative when supplied instead of
  double-counting the fallback Unity YAML scan.
- Rejected a context whose `projectId` differs from the requested project.

## 0.3.0 - Visual RAG

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

## 0.2.0 - Portability

- Added deterministic scene/prefab scanning and semantic rule matching.
- Added ambiguity and unresolved-destination gates.
- Added SHA-256 transactional backup, apply, verification and auto-rollback.
- Added guarded Theme Pack `.meta` hashes and idempotent no-op apply.
- Added last-transaction rollback.
- Connected scan/apply/rollback actions to the Editor Workbench.
- Added a clean-project portability fixture and automated gate runner.

## 0.1.0 - Foundation

- Introduced Core / Theme Pack / Project Adapter boundaries.
- Added stable semantic-role vocabulary and versioned JSON contracts.
- Added theme/project discovery and validation in a Unity Editor window.
- Added the first 300Mind theme pack.
- Added the PuzzleDrop adapter and production-scene scope.
- Documented migration, authoring, storage, versioning and safety gates.
