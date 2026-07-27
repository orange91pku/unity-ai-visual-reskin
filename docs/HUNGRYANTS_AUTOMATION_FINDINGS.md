# HungryAnts automation findings

Validation date: 2026-07-28

This document records defects found while running Project Brain and
ReVisualReskin against a production-sized Unity 6000 project. Machine-specific
paths, proprietary assets and generated databases are intentionally excluded.

## Verified regression: unsafe proposal scope

### Symptom

The first proposal run emitted 17 mappings:

- one referenced game UI image;
- sixteen unreferenced images from package or `Editor` folders.

The raw proposal false-positive rate was 94.1%. The catalog was allowed to
remain broad for discovery, but proposal generation did not establish a safe
default mutation scope.

### Root cause

`propose_mappings` ranked every project image whose filename tokens matched a
Theme Pack role. It did not require serialized Unity usage and did not exclude
Editor-only paths.

### Fix

Safe-default proposal generation now:

- rejects `reference_count <= 0`;
- rejects paths below an `Editor` folder;
- exposes `--include-unreferenced` and `--include-editor-assets` only as
  explicit discovery overrides;
- keeps `mutationAuthorized=false` and approval pending.

### Evidence

- Before: 17 proposals, 16 Editor/vendor false positives.
- After: 1 referenced game-art proposal, 0 Editor/vendor false positives.
- ReVisual unit suite: 11/11 passing.
- The approved one-image transaction preserved `.meta`, GUID, dimensions,
  alpha and serialized reference count.
- Unity compile, Missing Script, Level V2 and gameplay regression gates passed.
- The candidate failed human visual review and exact rollback restored the
  original bytes. This is the expected safety behavior.

### Regression contract

The default `propose` command must never return:

- an asset with zero serialized project references;
- an asset whose normalized path contains `/Editor/`.

The two discovery flags may override these filters, but their output must still
remain review-only.

## Open runner findings

These findings belong to the future cross-platform orchestration layer. They
are documented here so the same failures are not rediscovered.

### Windows environment-key collision

PowerShell `Start-Process` can fail when the inherited environment contains
both `Path` and `PATH`. A production runner must construct a
case-insensitive, de-duplicated environment block or avoid this wrapper for
Python child processes.

Acceptance criteria:

- child startup works with mixed-case duplicate environment keys;
- the runner returns a structured startup error instead of entering a polling
  loop with a null process handle.

### ScheduledJobs warning flood

`Start-Job` may load the ScheduledJobs adapter and repeatedly warn when its
profile directory is inaccessible. It completed the scan but polluted logs and
made failure diagnosis harder.

Acceptance criteria:

- performance sampling does not depend on PowerShell ScheduledJobs;
- stderr contains only messages from the measured process or the runner.

### Unity path quoting

Passing `Start-Process -ArgumentList` as a PowerShell array split a Unity
project path containing spaces. Unity rejected the malformed path before
opening the project.

Acceptance criteria:

- project and log paths containing spaces and non-ASCII characters survive
  round-trip argument parsing;
- the runner verifies Unity's logged project path before accepting a gate.

### Unity process completion

Directly invoking the Windows Unity GUI executable may return control before
the Unity process exits, leaving no reliable exit code.

Acceptance criteria:

- track the launched Unity PID;
- enforce a per-gate timeout;
- require both process termination and a terminal success/failure log marker;
- record elapsed time, exit code and peak working set.

### Art inventory classification

The independent inventory can rank normal maps, noise textures, package icons
and editor-only images above actual game UI.

Acceptance criteria:

- classify game art, technical textures, package/vendor art and editor art into
  separate lanes;
- safe-default proposals consume only referenced runtime game-art lanes;
- discovery can still query every lane explicitly.

### Theme coverage and runtime visual coverage

A technically compatible Theme Pack can still be too small or aesthetically
weaker than the current project. A gameplay boot capture also does not prove
that a changed popup or settings surface rendered correctly.

Acceptance criteria:

- report semantic-role coverage before applying a batch;
- reject project-wide claims when required roles have no approved candidate;
- maintain per-surface navigation and capture recipes;
- require visual acceptance separately from technical integration.

## Performance reference

The validation run observed:

| Stage | Result | Time |
|---|---:|---:|
| Art inventory | 180 image files | 25.99 s |
| Project Brain graph | 2,451 assets | 32.65 s |
| ReVisual cold project ingest | 543 records | 8.83 s |
| ReVisual warm project ingest | 543/543 reused | 3.15 s |
| Safe proposal generation | 1 proposal | 0.50 s |
| Full Unity post-apply gates | all passed | 162.67 s |

Unity startup dominates the end-to-end gate time. A future runner should
support a single-session gate bundle while preserving per-gate evidence and
rollback boundaries.
