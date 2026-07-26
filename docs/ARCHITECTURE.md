# Architecture

## Decision

ReVisualReskin uses three independently versioned layers.

### Core

Core owns deterministic behavior:

- catalog discovery;
- semantic-role contracts;
- scanning and reference evidence;
- dry-run plans;
- apply transactions and SHA-256 backups;
- GUID, Missing Script, compile, 9-slice, layout and runtime gates;
- before/after capture orchestration;
- rollback and commit hand-off;
- editor workbench.

Core must not contain a game name, game scene path, vendor sprite name, or
theme-specific GUID.

### Theme Pack

A Theme Pack owns reusable visual content:

- sprites, atlases, fonts, materials, masks and optional code-generated art;
- `hydra-theme.json`;
- 9-slice borders and image modes;
- semantic tags and visual-search metadata;
- preview thumbnails and quality evidence in future versions.

Theme Pack assets keep stable `.meta` files. Updating a theme version must not
silently regenerate GUIDs.

### Project Adapter

A Project Adapter owns game knowledge:

- production scenes and prefab roots;
- exclusions;
- exact and contextual semantic detection rules;
- runtime navigation actions and capture surfaces;
- project-specific layout corrections;
- permitted mutation scope.

Adapters may depend on game assemblies. Theme Packs never may.

## Rule precedence

Semantic classification is deterministic:

1. explicit approved object/path mapping;
2. component and hierarchy context;
3. exact source sprite mapping;
4. constrained name heuristic;
5. AI suggestion requiring human approval.

AI output is a proposed mapping, never an unreviewed mutation instruction.

## Safety state machine

```text
discovered
  -> scanned
  -> mapped
  -> human-approved
  -> dry-run-passed
  -> backed-up
  -> applied
  -> technical-verified
  -> visual-reviewed
  -> accepted/committed

Any failure after backed-up -> auto-rolled-back
```

Technical and visual verdicts are stored separately.

## Compatibility

The first supported baseline is Unity `6000.3` and UGUI `2.0.0`. JSON manifests
are versioned independently of package versions. Existing fields will not be
renamed without a schema migration.

