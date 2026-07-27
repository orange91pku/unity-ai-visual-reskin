# ReVisualReskin

Reusable, AI-first Unity art reskin infrastructure.

The repository deliberately separates three independently versioned layers:

1. `com.hydracore.visual-reskin` - deterministic scanning, semantic matching,
   safety gates, transactions, and editor UX.
2. `com.hydracore.visual-reskin.theme.*` - reusable art and semantic bindings.
3. `com.hydracore.visual-reskin.adapter.*` - project-specific scene, prefab,
   exclusion, and legacy-name knowledge.

This prevents a growing theme library from leaking project-specific names and
GUIDs into the engine. A fourth, separately deployable component,
`revisual_rag`, indexes visual features and semantic evidence without owning or
mutating Unity assets.

## Repository layout

```text
Packages/
  com.hydracore.visual-reskin/
  com.hydracore.visual-reskin.theme.300mind/
  com.hydracore.visual-reskin.adapter.puzzledrop/
docs/
schemas/
tools/
revisual_rag/
  local Visual RAG catalog, scanner, retrieval and Project Brain adapter
```

## Current milestone

`v0.3.0-visual-rag` adds a local-first SQLite visual catalog, per-sprite atlas
feature extraction, semantic and image retrieval, Unity reference evidence,
stable identities, Project Brain context ingestion, and review-only mapping
proposals. It does not grant mutation authority. Approved mappings still pass
through the Core dry-run, backup, apply, Unity gate and rollback workflow.

Start with [Architecture](docs/ARCHITECTURE.md) and
[Visual RAG](docs/VISUAL_RAG.md), then
[Theme authoring](docs/THEME_PACK_AUTHORING.md). See
[Portability test](docs/PORTABILITY_TEST.md) for the verified gate sequence.

## Visual RAG quick start

```powershell
python -m revisual_rag --db .revisual/visual-rag.sqlite3 init
python -m revisual_rag --db .revisual/visual-rag.sqlite3 ingest-theme `
  --manifest Packages/com.hydracore.visual-reskin.theme.300mind/Theme/hydra-theme.json
python -m revisual_rag --db .revisual/visual-rag.sqlite3 search `
  --text "rounded popup background" --source-kind theme --limit 10
```

The database contains metadata and vectors only. Art binaries remain in
versioned Theme Packs or immutable object storage.
