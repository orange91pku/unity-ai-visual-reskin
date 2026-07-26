# Theme storage and scale

The long-term system should treat theme content as an immutable artifact store
plus a searchable metadata catalog.

## Recommended split

### Git repository

Store:

- package manifests;
- JSON schemas;
- semantic mappings;
- small thumbnails;
- source attribution;
- tests and documentation.

Use Git LFS for large source files only when the team needs source-level
versioning.

### Object storage

Store:

- packaged `.tgz` releases;
- source PSD/AI files;
- large atlases;
- generated candidates;
- before/after captures;
- contact sheets.

Artifacts are addressed by content hash. Published versions are immutable.

### Visual RAG database

Store:

- asset and theme identifiers;
- semantic roles;
- visual embeddings;
- palette and geometry features;
- Unity importer/slicing metadata;
- licenses and provenance;
- project usage and A/B-test results;
- human and AI review scores.

The database points to object-storage hashes and package versions. It does not
become the authoritative home of binary art.

### re-api

Do not make `re-api` a binary art store. Add it only when multiple users,
machines or projects need a shared service. Its responsibilities should remain:

- authentication and access policy;
- theme registry/search endpoints;
- signed artifact URLs;
- Visual RAG query orchestration;
- ingestion jobs and A/B-result collection.

For the first releases, the local catalog can read Git manifests and package
folders directly. This keeps the system simple while preserving a clean route
to the shared service.

## Growth model

```text
Theme source
 -> ingestion/normalization
 -> semantic classification
 -> visual embedding
 -> human review
 -> immutable Theme Pack release
 -> project retrieval/mapping
 -> A/B evidence
 -> quality feedback
```

This supports hundreds of themes without copying all art into every game repo.
Projects pin only the package versions used by a build.
