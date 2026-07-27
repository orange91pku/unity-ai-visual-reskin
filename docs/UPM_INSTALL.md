# Install with Unity Package Manager

Unity AI Visual Reskin is distributed as versioned Git packages. A developer
does not need to clone this repository or copy package files into a Unity
project.

## Requirements

- Unity `6000.3` for the currently verified baseline.
- Git `2.14+` available on `PATH`.
- Internet access to GitHub while Unity resolves the package.

## Install in the Package Manager UI

1. Open **Window > Package Management > Package Manager**.
2. Select **+ > Install package from Git URL**.
3. Paste the Core URL and select **Install**:

   ```text
   https://github.com/orange91pku/unity-ai-visual-reskin.git?path=/Packages/com.heycici.visual-reskin#v0.4.1
   ```

4. To use the bundled example art, install the Theme Pack after Core:

   ```text
   https://github.com/orange91pku/unity-ai-visual-reskin.git?path=/Packages/com.heycici.visual-reskin.theme.300mind#v0.4.1
   ```

The `#v0.4.1` revision pins a reproducible release. The `?path=` query selects
one UPM package from this multi-package repository.

## Install in Packages/manifest.json

Teams can commit both direct dependencies to their Unity project:

```json
{
  "dependencies": {
    "com.heycici.visual-reskin": "https://github.com/orange91pku/unity-ai-visual-reskin.git?path=/Packages/com.heycici.visual-reskin#v0.4.1",
    "com.heycici.visual-reskin.theme.300mind": "https://github.com/orange91pku/unity-ai-visual-reskin.git?path=/Packages/com.heycici.visual-reskin.theme.300mind#v0.4.1"
  }
}
```

Unity generates or updates `Packages/packages-lock.json`. Commit both files so
the team and CI resolve the same package revision.

## Open the tool

After Unity finishes compiling, open:

**Tools > HeyCici > Visual Reskin Workbench**

Core discovery and validation are available immediately. A Theme Pack supplies
reusable semantic art. A Project Adapter supplies project-specific scene,
prefab and naming rules.

## Project Adapters

The repository includes a PuzzleDrop adapter as a reference implementation. It
contains project-specific paths and should not be installed into unrelated
games. Create a separate adapter for each project by following
[Project Adapter authoring](PROJECT_ADAPTER_AUTHORING.md).

If you are working on PuzzleDrop, its pinned Git URL is:

```text
https://github.com/orange91pku/unity-ai-visual-reskin.git?path=/Packages/com.heycici.visual-reskin.adapter.puzzledrop#v0.4.1
```

## Update

Change every installed Visual Reskin URL to the same newer release tag. Update
Core first, then Theme Packs and Project Adapters. Do not mix package versions.

For example, replace `#v0.4.1` with the next published tag in
`Packages/manifest.json`, save the file and let Unity resolve dependencies.

## Uninstall

Remove Project Adapters and Theme Packs first, then remove Core. This order
avoids leaving packages whose manifests depend on Core.

Package removal does not modify Unity assets that were previously changed by
an approved reskin transaction. Use the transaction rollback command before
uninstalling when those changes must be reverted.

## Troubleshooting

### No Git executable was found

Install Git `2.14+`, ensure it is available on `PATH`, then restart Unity Hub
and the Editor.

### Package name is invalid or cannot be found

Use the complete URL, including `.git`, `?path=/Packages/...` and the release
tag. Install Core before an optional Theme Pack or Adapter.

### Authentication prompt

This repository is public and does not require GitHub credentials. Check
whether a corporate proxy or a global Git URL rewrite is intercepting GitHub.

### Dependency resolution fails after an update

Confirm that Core, all Theme Packs and all Project Adapters use the same
release tag and package version. Delete only the affected entries from
`Packages/packages-lock.json` if Unity has retained a stale revision, then let
Package Manager resolve them again.

## Optional Visual RAG CLI

The local Python service is also installable without cloning:

```bash
python -m pip install \
  "revisual-rag @ git+https://github.com/orange91pku/unity-ai-visual-reskin.git@v0.4.1"
```

Unity Package Manager does not install Python. The Unity package and Visual RAG
service remain separate by design.
