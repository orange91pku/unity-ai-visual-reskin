# Unity AI Visual Reskin

[![CI](https://github.com/orange91pku/unity-ai-visual-reskin/actions/workflows/ci.yml/badge.svg)](https://github.com/orange91pku/unity-ai-visual-reskin/actions/workflows/ci.yml)
[![Apache-2.0](https://img.shields.io/badge/code%20license-Apache--2.0-blue.svg)](LICENSE)
[![Unity 6](https://img.shields.io/badge/Unity-6000.3-black.svg)](docs/PORTABILITY_TEST.md)
[![Visual RAG](https://img.shields.io/badge/Visual%20RAG-local--first-7c3aed.svg)](docs/VISUAL_RAG.md)

Unity AI Visual Reskin is an open, AI-first visual intelligence and semantic
reskin pipeline for Unity projects. It helps developers and coding agents:

- discover which sprites, textures, prefabs, scenes and GameObjects are
  visually important;
- connect those assets to exact Unity GUID/fileID and hierarchy evidence;
- search reusable Theme Packs through a local Visual RAG;
- propose explainable old-art to new-art mappings;
- preview and apply approved raster replacements without losing Unity
  identity;
- compile, scan Missing Scripts, run project-specific Unity gates and roll
  back exactly when either technical or visual quality fails.

The system is designed to work with
[Unity AI Project Brain](https://github.com/orange91pku/unity-ai-project-brain).
Project Brain provides structural truth; Unity AI Visual Reskin provides visual
retrieval, theme knowledge and guarded mutation.

> Status: public research and developer tooling. The safe workflow is
> production-project tested, but final visual approval remains a human or
> vision-model decision.

## Why this repository exists

Normal search can find files named `button` or `background`, but it cannot tell
an AI:

- whether that image is runtime game art or an Editor-only icon;
- which scene, prefab, component and property use it;
- whether a proposed replacement preserves alpha, slicing and aspect ratio;
- whether changing it created a Missing Script or compile regression;
- whether a technically valid replacement is actually better-looking.

This repository makes those decisions explicit, versioned and testable.

## Architecture

```text
Unity repository
   |
   +-- Unity AI Project Brain
   |      GUID/fileID + scene/prefab/GameObject/component evidence
   |                       |
   |                       v
   +---------------- visual-context.json
                           |
                           v
                  Local Visual RAG
                  theme + project index
                           |
                    pending proposals
                           |
                    visual approval
                           |
                           v
                 Unity Reskin Core
             preview -> apply -> gates
                    -> accept/rollback
```

The repository separates four independently replaceable layers:

1. **Core Unity package** — deterministic scanning, matching, transactions,
   safety gates and Editor UX.
2. **Theme Packs** — reusable art, semantic roles, 9-slice metadata and stable
   Unity `.meta` files.
3. **Project Adapters** — project-specific scenes, prefab roots, exclusions,
   legacy names and runtime capture recipes.
4. **Visual RAG service** — local SQLite metadata/vector catalog, Project Brain
   bridge, retrieval and review-only proposals.

No AI-generated proposal directly authorizes mutation.

## Repository layout

```text
Packages/
  com.hydracore.visual-reskin/
  com.hydracore.visual-reskin.theme.300mind/
  com.hydracore.visual-reskin.adapter.puzzledrop/
revisual_rag/          Python Visual RAG and safe raster transactions
schemas/               Versioned bridge, proposal and manifest contracts
tests/                 Unit and Unity portability fixtures
tools/                 Repository and Unity metadata validators
docs/                  Architecture, authoring and operational guides
AGENTS.md              Fast context for AI coding agents
llms.txt               Machine-oriented documentation index
```

## Requirements

- Unity `6000.3` for the verified Unity package baseline;
- Python `3.10+`;
- PowerShell 7 for the repository validator;
- Git;
- a Unity project using text serialization for full YAML evidence;
- optionally, Unity AI Project Brain for exact hierarchy/component usage.

## Quick start

Clone and install the Python service:

```bash
git clone https://github.com/orange91pku/unity-ai-visual-reskin.git
cd unity-ai-visual-reskin
python -m pip install -e .
python -m revisual_rag --db .revisual/visual-rag.sqlite3 init
```

Index the bundled example Theme Pack:

```bash
python -m revisual_rag --db .revisual/visual-rag.sqlite3 ingest-theme \
  --manifest Packages/com.hydracore.visual-reskin.theme.300mind/Theme/hydra-theme.json
```

Index a Unity project without Project Brain:

```bash
python -m revisual_rag --db .revisual/visual-rag.sqlite3 ingest-project \
  --project-root /absolute/path/to/UnityProject \
  --project-id studio.game
```

This fallback reads Unity YAML references. For hierarchy, component and
property-level evidence, use the
[Project Brain integration guide](docs/PROJECT_BRAIN_BRIDGE.md).

Generate safe-default review proposals:

```bash
python -m revisual_rag --db .revisual/visual-rag.sqlite3 propose \
  --project-id studio.game \
  --theme-id hydracore.theme.300mind \
  --output .revisual/mapping-proposals.json
```

Safe defaults exclude Editor-only images and images with zero serialized Unity
references. Discovery workflows can explicitly opt into those lanes, but their
results remain review-only.

## Approval-gated raster pilot

Materialization creates a preview outside Unity `Assets/`:

```bash
python -m revisual_rag --db .revisual/visual-rag.sqlite3 materialize-raster \
  --proposal-file .revisual/mapping-proposals.json \
  --proposal-id vrmap_EXACT_ID \
  --project-root /absolute/path/to/UnityProject \
  --theme-root Packages/com.hydracore.visual-reskin.theme.300mind \
  --output-dir .revisual/candidates
```

Apply requires the same exact proposal ID:

```bash
python -m revisual_rag --db .revisual/visual-rag.sqlite3 apply-raster \
  --candidate-manifest .revisual/candidates/vrmap_EXACT_ID-candidate.json \
  --approve vrmap_EXACT_ID \
  --project-root /absolute/path/to/UnityProject \
  --backup-root .revisual/transactions
```

The transaction verifies image and `.meta` hashes, GUID, dimensions, alpha and
serialized-reference count. Any failed invariant restores the original files.
An accepted technical transaction can still be reversed:

```bash
python -m revisual_rag rollback-raster \
  --transaction .revisual/transactions/TRANSACTION_ID/transaction.json
```

## Validation

```bash
python -m unittest discover -s tests -v
pwsh -File tools/validate-repository.ps1
```

The current Python suite covers Visual RAG identity, Project Brain usage,
schema migration, proposal safety and exact raster rollback. The Unity fixture
is documented in [Portability test](docs/PORTABILITY_TEST.md).

## Safety model

- Project Brain and Visual RAG exchange versioned JSON; they never share
  databases.
- Project Brain and Visual RAG are read-only toward Unity source.
- Every mapping starts with `mutationAuthorized=false`.
- Preview output and indexes stay outside Unity `Assets/`.
- Apply is explicit, approval-gated and transaction-backed.
- Unity `.meta` and GUID identity must not change.
- Technical integration and visual quality are separate verdicts.
- A failed verdict rolls back rather than claiming partial success.

## Documentation

- [Connect Unity AI Project Brain](docs/PROJECT_BRAIN_BRIDGE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Visual RAG](docs/VISUAL_RAG.md)
- [Theme Pack authoring](docs/THEME_PACK_AUTHORING.md)
- [Project Adapter authoring](docs/PROJECT_ADAPTER_AUTHORING.md)
- [Raster transactions](docs/RASTER_TRANSACTION.md)
- [Storage and scale](docs/STORAGE_AND_SCALE.md)
- [Production automation findings](docs/HUNGRYANTS_AUTOMATION_FINDINGS.md)
- [Contributing](CONTRIBUTING.md)

## For AI agents

Start with [AGENTS.md](AGENTS.md), then read `llms.txt` for the shortest map of
authoritative files. Stable machine contracts live under `schemas/`. Do not
infer mutation authority from search scores or proposal JSON.

## License and third-party content

Repository code is licensed under Apache-2.0. Bundled sample Theme Pack art is
third-party content and is not relicensed by the code license; see
[Third-party notices](THIRD_PARTY_NOTICES.md).

This project is not affiliated with or endorsed by Unity Technologies.
