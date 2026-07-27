# Project Brain bridge

Project Brain and Visual RAG exchange versioned JSON. They never read each
other's database.

## Ownership

Project Brain owns structural truth:

- Unity GUID/fileID identity;
- scene, prefab, hierarchy and component graph;
- dependency and blast-radius evidence;
- Git history and runtime evidence;
- index fingerprint.

Visual RAG owns visual truth:

- Theme Pack catalog and semantic roles;
- visual features/embeddings and palettes;
- candidate ranking;
- visual review and A/B evidence.

## Input

`hydracore.project-brain.visual-context/v1` supplies project identity, index
fingerprint, assets and exact usage evidence. Its schema is
`schemas/visual-rag-project-context.schema.json`.

```powershell
python -m revisual_rag --db .revisual/visual-rag.sqlite3 ingest-project `
  --project-root D:\game\UnityProject `
  --project-id studio.game `
  --context D:\context\project-brain-visual-context.json
```

Without a context envelope the scanner falls back to read-only Unity YAML GUID
references. That fallback has less hierarchy/component detail.

When a context envelope is present it is authoritative for usage counts.
Visual RAG stores distinct owner, fileID, hierarchy, component, property and
evidence identities. Local database schema v2 migrates v1 usage rows without
discarding existing records.

## Output

`hydracore.visual-rag.mapping-proposals/v1` returns stable source/destination
IDs, score breakdown, technical constraints and evidence. The contract cannot
authorize mutation. A separate approved Core plan is required after review.

This boundary allows either system to be public, replaced or hosted
independently.
