# Visual RAG

## Purpose

Visual RAG gives AI a searchable visual memory for reusable Unity art. It
answers:

- which Theme Pack assets look and behave like this project asset;
- which semantic role an asset is approved to fill;
- where a project asset is used and how important it is;
- what technical constraints must survive replacement;
- which suggestions were accepted or rejected previously.

It is deliberately separate from the Unity mutation engine.

## Stored data

SQLite stores metadata, not art binaries:

- stable `vrag_*` identity;
- Theme Pack/project identity and version;
- Unity GUID, sprite name and relative path;
- content SHA-256;
- per-sprite dimensions, aspect, alpha and opaque bounds;
- brightness, saturation, edge density, palette and perceptual hash;
- visual feature vector and semantic hashed vector with provider versions;
- semantic role, style tags, license and provenance;
- scene/prefab usage evidence and reference count;
- pending mapping and later review/A-B evidence.

Stable identity includes source, GUID/path, sprite and semantic role. Content
hash is separate, so a stable Unity identity survives an approved art revision.

## Retrieval

The default provider is deterministic and offline:

- `hydracore.visual-features.v1` indexes geometry, color, alpha and texture;
- `hydracore.semantic-hash.v1` indexes role, tags, path and sprite name.

Search may be text-only, image-only or hybrid. Every result exposes its visual,
semantic and exact-role score. These vectors are intentionally not called CLIP
embeddings. A future ONNX/CLIP provider can be added behind the same provider
and vector fields.

## Commands

```powershell
python -m revisual_rag --db .revisual/visual-rag.sqlite3 init

python -m revisual_rag --db .revisual/visual-rag.sqlite3 ingest-theme `
  --manifest Packages/com.example.theme/Theme/hydra-theme.json

python -m revisual_rag --db .revisual/visual-rag.sqlite3 ingest-project `
  --project-root D:\game\UnityProject --project-id studio.game

python -m revisual_rag --db .revisual/visual-rag.sqlite3 search `
  --text "fantasy primary purchase button" --source-kind theme --limit 20

python -m revisual_rag --db .revisual/visual-rag.sqlite3 propose `
  --project-id studio.game --theme-id studio.theme.fantasy `
  --output .revisual/proposals.json
```

`propose` always emits `mutationAuthorized: false` and every proposal starts at
`approval.status: pending`.

## Safety boundary

Visual RAG never writes under a Unity project's `Assets/`. After human approval,
the selected mappings are converted into the existing Core plan. Core performs:

1. pre-scan and baseline hashes;
2. ambiguity and destination checks;
3. dry-run;
4. transactional backup;
5. apply while preserving Theme Pack `.meta`;
6. Unity compile, Missing Script, GUID/reference, 9-slice and layout gates;
7. visual review;
8. accept or exact rollback.

## Scaling

SQLite is sufficient for one workstation and many Theme Packs. The schema
records vector provider/version and exposes JSON contracts, allowing a later
move to PostgreSQL plus a vector index. Binary art remains in Git/LFS or
content-addressed object storage.

## PuzzleDrop read-only trial

The v0.3.0 trial indexed:

- 737 project visual assets, including individual Unity sub-sprites;
- 20 Theme Pack semantic bindings;
- 1,041 serialized Unity files;
- 16,176 GUID/fileID references grouped into 649 indexed usage records;
- zero Unity asset, `.meta`, scene or prefab writes.

After the cache was warm, a full repeat scan reused 737/737 visual records and
completed in 4.04 seconds on the development workstation. A migration scan
that computed 118 new sub-sprites and reused 619 records completed in 13.61
seconds. Proposal generation is sub-second and remains review-only.
