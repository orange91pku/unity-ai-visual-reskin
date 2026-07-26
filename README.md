# ReVisualReskin

Reusable, AI-first Unity art reskin infrastructure.

The repository deliberately separates three independently versioned layers:

1. `com.hydracore.visual-reskin` — deterministic scanning, semantic matching,
   safety gates, transactions, and editor UX.
2. `com.hydracore.visual-reskin.theme.*` — reusable art and semantic bindings.
3. `com.hydracore.visual-reskin.adapter.*` — project-specific scene, prefab,
   exclusion, and legacy-name knowledge.

This prevents a growing theme library from leaking project-specific names and
GUIDs into the engine.

## Repository layout

```text
Packages/
  com.hydracore.visual-reskin/
  com.hydracore.visual-reskin.theme.300mind/
  com.hydracore.visual-reskin.adapter.puzzledrop/
docs/
schemas/
tools/
```

## Current milestone

`v0.1.0-foundation` establishes the portable package contracts, catalog
discovery, validation window, a 300Mind theme pack, and the PuzzleDrop adapter.
The proven PuzzleDrop transactional apply engine will be migrated behind these
contracts in the next milestone without changing theme manifests.

Start with [Architecture](docs/ARCHITECTURE.md) and
[Theme authoring](docs/THEME_PACK_AUTHORING.md).

