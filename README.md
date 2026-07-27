# ReVisualReskin

Reusable, AI-first Unity art reskin infrastructure.

The repository deliberately separates three independently versioned layers:

1. `com.hydracore.visual-reskin` - deterministic scanning, semantic matching,
   safety gates, transactions, and editor UX.
2. `com.hydracore.visual-reskin.theme.*` - reusable art and semantic bindings.
3. `com.hydracore.visual-reskin.adapter.*` - project-specific scene, prefab,
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

`v0.2.0-portability` adds the generic scanner, deterministic matcher,
transactional apply, automatic technical verification and exact rollback.
The packages passed a clean Unity `6000.3.10f1` fixture covering dry-run,
apply, idempotent no-op, unchanged Theme Pack metadata, zero Missing Script,
and SHA-256 scene restoration.

Start with [Architecture](docs/ARCHITECTURE.md) and
[Theme authoring](docs/THEME_PACK_AUTHORING.md). See
[Portability test](docs/PORTABILITY_TEST.md) for the verified gate sequence.
