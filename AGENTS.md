# AI agent guide

This repository is **Unity AI Visual Reskin**. It is a specialist application
for Unity visual intelligence, Visual RAG, reusable Theme Packs and guarded art
replacement.

## Read first

1. `README.md`
2. `docs/UPM_INSTALL.md`
3. `docs/ARCHITECTURE.md`
4. `docs/PROJECT_BRAIN_BRIDGE.md`
5. `docs/VISUAL_RAG.md`
6. `docs/RASTER_TRANSACTION.md`

Machine contracts are under `schemas/`. Treat them as authoritative.

## System boundaries

- `revisual_rag/` is read-only during ingest, search and proposal generation.
- Project Brain owns Unity GUID/fileID, scene, prefab, GameObject, component
  and hierarchy evidence.
- Visual Reskin owns visual features, semantic roles, Theme Packs and mapping
  review.
- Only an explicitly approved raster/Core transaction may mutate a Unity
  project.
- Search score is never mutation authority.
- Technical integration and visual quality are separate verdicts.

## Safe change rules

- Never regenerate or delete Unity `.meta` files during art replacement.
- Preserve GUID, dimensions, alpha and serialized-reference count unless a
  reviewed migration explicitly changes the contract.
- Keep candidates, indexes, databases, reports and backups outside Unity
  `Assets/`.
- Do not broaden default proposal scope to Editor or zero-reference assets.
- Do not add project-specific names or GUIDs to Core.
- Put project-specific rules in an adapter.
- Put theme-specific GUIDs and sprite metadata in a Theme Pack.
- Any post-backup failure must produce exact rollback.

## Validation

Run before proposing a commit:

```bash
python -m unittest discover -s tests -v
pwsh -File tools/validate-repository.ps1
```

For Unity package changes, also run the fixture described in
`docs/PORTABILITY_TEST.md`.

For production-project changes, require:

- Unity compile;
- Missing Script before/after comparison;
- GUID/reference invariants;
- affected scene runtime boot;
- per-surface visual capture;
- rollback proof.

## Extension points

- New visual feature provider: preserve provider name/version in stored rows.
- New Theme Pack: follow `docs/THEME_PACK_AUTHORING.md`.
- New project: create an adapter using `docs/PROJECT_ADAPTER_AUTHORING.md`.
- New Project Brain contract: add a versioned schema and migration; do not
  silently reinterpret an existing envelope.
- New mutation type: add dry-run, approval, backup, invariants and rollback
  before exposing it in UI or CLI.

## Repository hygiene

- Do not commit `.revisual`, `.project-brain`, SQLite files, local absolute
  paths, credentials, Unity `Library`, generated builds or Python artifacts.
- Do not commit unrelated private tooling here.
- Third-party art is not covered by the Apache-2.0 code license; update
  `THIRD_PARTY_NOTICES.md` when adding a Theme Pack.

## Useful queries for an AI

- Architecture ownership: `docs/ARCHITECTURE.md`
- UPM distribution: `docs/UPM_INSTALL.md`
- Project Brain integration: `docs/PROJECT_BRAIN_BRIDGE.md`
- Proposal safety: `revisual_rag/retrieval.py`
- Unity identity transaction: `revisual_rag/raster_transaction.py`
- Database schema: `revisual_rag/store.py`
- Project ingest: `revisual_rag/ingest.py`
- CLI surface: `revisual_rag/cli.py`
- Regression evidence: `tests/test_visual_rag.py`
