# Contributing

Contributions that improve Unity visual understanding, Theme Pack portability,
safe automation and reproducible visual verification are welcome.

## Development setup

```bash
git clone https://github.com/orange91pku/unity-ai-visual-reskin.git
cd unity-ai-visual-reskin
python -m pip install -e .
python -m unittest discover -s tests -v
```

Run the repository contract validator:

```bash
pwsh -File tools/validate-repository.ps1
```

## Choose the correct layer

- General deterministic behavior belongs in Core.
- Reusable visual content and semantic bindings belong in a Theme Pack.
- Game-specific paths, names, exclusions and navigation belong in a Project
  Adapter.
- Visual features, catalog storage and retrieval belong in `revisual_rag`.
- Unity structural truth belongs in Project Brain, not duplicated here.

See `docs/ARCHITECTURE.md`.

## Pull request requirements

Every pull request should state:

- the problem and root cause;
- which layer owns the change;
- whether a public JSON or Unity package contract changes;
- technical and visual risks;
- tests and Unity gates run;
- rollback behavior.

Add regression coverage for defects. Do not accept “the scan completed” as
proof that output quality is correct.

## Compatibility

- Keep existing JSON fields stable within a schema version.
- Add explicit migrations for SQLite schema changes.
- Do not silently regenerate Unity GUIDs.
- Keep Theme Pack `.meta` files stable across art revisions.
- Record vector/feature provider name and version.

## Art and licensing

Only contribute art that may legally be redistributed. Add provenance and
license information to `THIRD_PARTY_NOTICES.md`. The repository's Apache-2.0
license applies to code, not automatically to third-party Theme Pack assets.

## Security

Do not commit:

- API keys, credentials or cookies;
- local absolute paths;
- `.project-brain` or `.revisual` databases;
- Unity `Library`, build output or package caches;
- unrelated private tooling;
- proprietary project assets without redistribution permission.
