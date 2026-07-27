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

`v0.4.0` adds a local-first SQLite visual catalog, per-sprite atlas
feature extraction, semantic and image retrieval, Unity reference evidence,
stable identities, Project Brain context ingestion, review-only mapping
proposals, and approval-gated raster transactions. Raster apply preserves the
Unity `.meta`, GUID, dimensions, serialized-reference count and—by default—the
source alpha mask required by tight Sprite meshes.

Start with [Architecture](docs/ARCHITECTURE.md) and
[Visual RAG](docs/VISUAL_RAG.md), then
[Theme authoring](docs/THEME_PACK_AUTHORING.md). The
[automation findings](docs/HUNGRYANTS_AUTOMATION_FINDINGS.md) record the
production-project regression evidence and remaining runner work. See
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

## Safe raster pilot

Every mutation is split into two explicit stages. Materialization only creates
a preview outside `Assets`; apply requires the exact proposal ID as approval.

```powershell
python -m revisual_rag --db .revisual/visual-rag.sqlite3 materialize-raster `
  --proposal-file .revisual/mapping-proposals.json `
  --proposal-id vrmap_EXACT_ID `
  --project-root D:/UnityProject `
  --theme-root Packages/com.hydracore.visual-reskin.theme.300mind `
  --output-dir .revisual/candidates

python -m revisual_rag --db .revisual/visual-rag.sqlite3 apply-raster `
  --candidate-manifest .revisual/candidates/vrmap_EXACT_ID-candidate.json `
  --approve vrmap_EXACT_ID `
  --project-root D:/UnityProject `
  --backup-root .revisual/transactions
```

If a post-apply invariant fails, apply restores the original image and `.meta`
automatically. A successful transaction can still be reversed exactly:

```powershell
python -m revisual_rag rollback-raster `
  --transaction .revisual/transactions/TRANSACTION_ID/transaction.json
```
