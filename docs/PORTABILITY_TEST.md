# Portability test

## Verified result

ReVisualReskin `0.2.0` passed a clean-project fixture on Unity
`6000.3.10f1` on 2026-07-27.

The fixture installs Core, the 300Mind Theme Pack, and a tiny Project Adapter
as independent local Unity packages. It creates one legacy UGUI purchase
button and executes this sequence:

1. create and save the baseline scene;
2. dry-run and require exactly one deterministic mapping;
3. apply the mapping transactionally;
4. require zero Missing Script and unchanged Theme Pack `.meta` hashes;
5. scan again and require the mapping to be recognized as applied;
6. apply again and require an idempotent `no_op_verified` transaction;
7. rollback and require the original scene SHA-256 hash;
8. scan the restored scene and require the original mapping again.

Recorded result:

```json
{
  "unityVersion": "6000.3.10f1",
  "corePackageVersion": "0.2.0",
  "themeId": "hydracore.theme.300mind",
  "projectId": "hydracore.fixture",
  "dryRunPassed": true,
  "applyPassed": true,
  "noOpPassed": true,
  "rollbackPassed": true,
  "sceneHashRestored": true,
  "missingScripts": 0,
  "guardedThemeMetaFiles": 2,
  "passed": true
}
```

## Reproduce

Create a clean Unity 6000.3 project and install these local packages:

- `Packages/com.hydracore.visual-reskin`
- `Packages/com.hydracore.visual-reskin.theme.300mind`
- a Project Adapter, or the fixture manifest in `tests/portability`

Copy `tests/portability/ReVisualReskinFixtureRunner.cs` into
`Assets/Editor`, copy `tests/portability/hydra-project.json` into an
`Assets` subfolder, then run:

```powershell
unity --format json run "D:\path\to\fixture" `
  --editor-version 6000.3.10f1 --timeout 300 -- `
  -nographics `
  -executeMethod ReVisualReskinFixtureRunner.Run `
  -logFile "D:\path\to\fixture\Logs\portability.log"
```

The successful log contains `REVRS_PORTABILITY_PASS`; the machine-readable
report is written to
`art-audit/portability-fixture-report.json`.

## Defects found by the fixture

The clean import resized both source atlases to Unity's 2048-pixel import
limit. Unity consequently scales `Sprite.border`, while the Theme Pack stores
9-slice borders in original source pixels. The first validator compared the
two values directly and blocked the transaction for the wrong reason. Version
0.2 converts source border values using the actual import ratio.

The fixture also caught malformed generated `.meta` files without a final LF.
Repository validation now rejects that condition before Unity import.

## Scope of this verdict

This proves the generic package lifecycle and Unity serialization safety on a
minimal clean project. It does not yet prove full PuzzleDrop visual coverage.
PuzzleDrop integration, old/new plan comparison, runtime navigation, and
human visual review are Wave 3 gates.
