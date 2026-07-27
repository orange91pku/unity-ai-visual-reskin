# Connect Unity AI Project Brain

Unity AI Project Brain and Unity AI Visual Reskin are independent applications
that exchange a versioned, read-only JSON envelope.

- Project Brain owns Unity structural truth.
- Visual Reskin owns visual retrieval, Theme Packs, review and transactions.
- Neither application reads the other application's database.
- Neither search nor context output authorizes a Unity mutation.

Repositories:

- Project Brain:
  <https://github.com/orange91pku/unity-ai-project-brain>
- Visual Reskin:
  <https://github.com/orange91pku/unity-ai-visual-reskin>

Stable public UPM identities:

- Project Brain Unity bridge: `com.heycici.project-brain`
- Visual Reskin Core: `com.heycici.visual-reskin`

The package IDs do not merge system ownership. Project Brain and Visual RAG
still keep separate databases and exchange only versioned contracts.

## What the bridge adds

Visual Reskin can index a Unity project by scanning YAML references alone. The
Project Brain bridge adds exact:

- Unity GUID and fileID identity;
- scene and prefab owner paths;
- GameObject hierarchy paths;
- component types and serialized property names;
- aggregated reference counts;
- a deterministic graph fingerprint.

This evidence lets proposal generation exclude unreferenced and Editor-only
images by default and lets reviewers understand the blast radius of replacing
an asset.

## 1. Clone both repositories

```bash
git clone https://github.com/orange91pku/unity-ai-project-brain.git
git clone https://github.com/orange91pku/unity-ai-visual-reskin.git
```

The repositories may live anywhere. Do not copy either tool into the target
Unity project's `Assets/` folder.

Example layout:

```text
workspace/
  unity-ai-project-brain/
  unity-ai-visual-reskin/
  my-unity-game/
    Assets/
    Packages/
    ProjectSettings/
```

## 2. Install Project Brain

From `unity-ai-project-brain`:

```bash
pnpm install --frozen-lockfile
python -m pip install -e .
```

Project Brain currently requires Node.js `22.15+`, pnpm, Python `3.11+` and
Git.

## 3. Build and validate the Unity graph

Use the repository root for `--repository`. Use the folder containing
`Assets`, `Packages` and `ProjectSettings` for `--unity-project`.

```bash
python -m project_brain.unity_graph build \
  --repository /absolute/path/to/my-unity-game \
  --unity-project /absolute/path/to/my-unity-game \
  --policy config/index-policy.example.json \
  --database /absolute/path/to/output/unity-graph.sqlite3

python -m project_brain.unity_graph validate \
  --database /absolute/path/to/output/unity-graph.sqlite3
```

Do not continue if validation reports a fingerprint mismatch, dangling
identity edge or ambiguous script asset.

## 4. Export the Visual Context envelope

Choose a stable project ID. Use the same ID in both applications.

```bash
python -m project_brain.visual_context export \
  --graph /absolute/path/to/output/unity-graph.sqlite3 \
  --repository /absolute/path/to/my-unity-game \
  --unity-project /absolute/path/to/my-unity-game \
  --project-id studio.game \
  --output /absolute/path/to/output/visual-context.json
```

The output schema is:

```text
hydracore.project-brain.visual-context/v1
```

The envelope contains project-relative paths and content hashes. Generated
indexes and output envelopes should stay outside the Unity repository or in an
ignored tooling directory.

## 5. Install and initialize Visual Reskin

From `unity-ai-visual-reskin`:

```bash
python -m pip install -e .
python -m revisual_rag \
  --db /absolute/path/to/output/visual-rag.sqlite3 \
  init
```

The database stores metadata and feature vectors, not authoritative Unity art.

## 6. Ingest a Theme Pack

The repository includes one sample Theme Pack:

```bash
python -m revisual_rag \
  --db /absolute/path/to/output/visual-rag.sqlite3 \
  ingest-theme \
  --manifest Packages/com.heycici.visual-reskin.theme.300mind/Theme/hydra-theme.json
```

For a real production reskin, build a Theme Pack whose semantic-role coverage
matches the target game's UI and art surfaces.

## 7. Ingest the project with Project Brain evidence

```bash
python -m revisual_rag \
  --db /absolute/path/to/output/visual-rag.sqlite3 \
  ingest-project \
  --project-root /absolute/path/to/my-unity-game \
  --project-id studio.game \
  --context /absolute/path/to/output/visual-context.json
```

Visual Reskin rejects the envelope when its `projectId` differs from the CLI
project ID. When context is present, Project Brain usage is authoritative and
the YAML fallback is not double-counted.

Expected result fields include:

```json
{
  "source": "studio.game",
  "assets": 0,
  "reused": 0,
  "computed": 0,
  "serializedFiles": 0,
  "references": 0,
  "indexFingerprint": "64-character-sha256",
  "warnings": []
}
```

Counts depend on the project. The fingerprint must match the validated Project
Brain graph.

## 8. Generate review-only mappings

```bash
python -m revisual_rag \
  --db /absolute/path/to/output/visual-rag.sqlite3 \
  propose \
  --project-id studio.game \
  --theme-id hydracore.theme.300mind \
  --output /absolute/path/to/output/mapping-proposals.json
```

The output schema is:

```text
hydracore.visual-rag.mapping-proposals/v1
```

Hard rules:

- `mutationAuthorized` is always `false`;
- every proposal starts at `approval.status=pending`;
- default proposal scope excludes zero-reference images;
- default proposal scope excludes paths below an `Editor` folder;
- `--include-unreferenced` and `--include-editor-assets` are discovery
  overrides, not automatic-apply modes.

## 9. Review, materialize and apply a canary

Start with one low-blast-radius asset. Materialization writes outside
`Assets/`:

```bash
python -m revisual_rag \
  --db /absolute/path/to/output/visual-rag.sqlite3 \
  materialize-raster \
  --proposal-file /absolute/path/to/output/mapping-proposals.json \
  --proposal-id vrmap_EXACT_ID \
  --project-root /absolute/path/to/my-unity-game \
  --theme-root Packages/com.heycici.visual-reskin.theme.300mind \
  --output-dir /absolute/path/to/output/candidates
```

After visual review, apply using the same exact proposal ID:

```bash
python -m revisual_rag \
  --db /absolute/path/to/output/visual-rag.sqlite3 \
  apply-raster \
  --candidate-manifest /absolute/path/to/output/candidates/vrmap_EXACT_ID-candidate.json \
  --approve vrmap_EXACT_ID \
  --project-root /absolute/path/to/my-unity-game \
  --backup-root /absolute/path/to/output/transactions
```

Apply verifies:

- source image hash;
- source `.meta` hash;
- Unity GUID;
- pixel dimensions;
- alpha-mask hash by default;
- serialized GUID reference count.

Any failed invariant restores the original image and `.meta`.

## 10. Run Unity gates

Use Unity CLI or your CI runner to verify at least:

1. import and C# compile;
2. Missing Script count before/after;
3. GUID and serialized-reference delta;
4. project-specific data/level validation;
5. runtime boot of affected scenes;
6. before/after captures of every changed visual surface.

Technical integration and visual quality are separate verdicts. A compile pass
does not prove that a replacement is aesthetically correct.

If either verdict fails:

```bash
python -m revisual_rag rollback-raster \
  --transaction /absolute/path/to/output/transactions/TRANSACTION_ID/transaction.json
```

## Contract ownership

| Data | Authority |
|---|---|
| Unity GUID/fileID and hierarchy usage | Project Brain |
| Visual features and semantic roles | Visual Reskin |
| Original Unity source | Target repository |
| Theme art binaries | Theme Pack or object storage |
| Review decision | Human or approved vision workflow |
| Apply/rollback record | Visual Reskin transaction |
| Compile/runtime evidence | Unity gate runner |

## Troubleshooting

### No proposals

This can be a correct safety result. Check:

- Theme Pack semantic-role coverage;
- whether target images have serialized references;
- whether assets are Editor-only;
- aspect-ratio and image-mode compatibility;
- technical-texture/material-only exclusions.

Do not lower every gate merely to force a mapping.

### Project asset count differs from image-file count

One image atlas may produce many indexed Unity sub-sprites. Visual record count
therefore can exceed physical image-file count.

### Project Brain reports unresolved script-symbol links

The visual GUID/fileID graph can still be valid without an optional Roslyn
catalog. Treat unresolved symbol links separately from unresolved visual
fileIDs.

### Windows path contains spaces

Quote the complete value passed to `--repository`, `--unity-project`,
`--project-root`, `--context` and `--logFile`. When wrapping Unity with
PowerShell `Start-Process`, construct and test the final argument string rather
than assuming an array preserves quoting.

## Security and privacy

- Do not commit `.project-brain`, `.revisual`, SQLite databases or local paths.
- Do not expose credentials through context or proposal documents.
- Keep Project Brain MCP and Context API read-only and loopback-bound unless an
  explicit deployment security model exists.
- Treat every generated proposal as untrusted review input.
