# Project Adapter authoring

A Project Adapter translates one game's structure into stable semantic roles.
It never chooses the final art.

## Process

1. List production scenes and owned prefab roots.
2. Exclude packages, demos, debug UI, recovery output and source theme folders.
3. Scan visible `Image`, `SpriteRenderer`, material and font references.
4. Add exact rules for high-confidence legacy names.
5. Add hierarchy/component rules only when scoped enough to avoid collisions.
6. Define normal runtime navigation for Home, Shop, Gameplay and popups.
7. Record layout corrections separately from sprite mappings.
8. Run baseline Missing Script, GUID and scene-hash gates.

## Detection rules

Higher `priority` wins. A selector may contain:

- exact source sprite name;
- host-name substring;
- hierarchy substring;
- component type.

The engine must record which rule produced every mapping. Ambiguous matches are
blocked until reviewed.

## Portability test

An adapter passes when:

- Core and a Theme Pack install without copying game code into either package;
- scan and dry-run work on a clean clone;
- apply changes only approved assets;
- rollback restores exact file hashes;
- a second apply is a verified no-op;
- runtime capture returns to the original scene and dirty state.

