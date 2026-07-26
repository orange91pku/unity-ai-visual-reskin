# PuzzleDrop migration

The existing PuzzleDrop 300Mind pipeline is the reference implementation for
transaction and Unity gates.

## Migration waves

### Wave 1 — contracts

- Core, Theme Pack and Adapter packages exist.
- 300Mind bindings and PuzzleDrop rules are represented in manifests.
- Catalog validation is read-only.

### Wave 2 — engine extraction

- Move generic scanner, backup, hash, apply, verification and rollback code
  from `Chroma300MindProductionPipeline` into Core.
- Keep PuzzleDrop-specific runtime actions in the adapter.
- Compare the old and new dry-run plans byte-for-byte.

### Wave 3 — package install

- Install the three packages into a clean PuzzleDrop clone.
- Avoid duplicate atlas GUIDs: remove/migrate the old in-project 300Mind copy
  before enabling the packaged copy.
- Run baseline, apply, runtime review, rollback and no-op gates.

### Wave 4 — retire legacy tool

- Keep the old pipeline for one release as a fallback.
- Remove it only after two equivalent verified builds.

## Acceptance evidence

- compile pass;
- zero Missing Script;
- unchanged MonoScript and scene GUIDs;
- valid 9-slice borders;
- exact rollback hashes;
- clean second apply;
- Home, Shop, Gameplay and popup captures;
- independent technical and visual verdicts.

