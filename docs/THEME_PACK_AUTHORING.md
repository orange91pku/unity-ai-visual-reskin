# Theme Pack authoring

## Minimum package

```text
com.hydracore.visual-reskin.theme.<id>/
  package.json
  Theme/hydra-theme.json
  Art/
    ...
```

Every imported art file must include its `.meta`.

## Authoring flow

1. Import source art into an isolated Unity authoring project.
2. Remove demos, scripts and unrelated vendor content.
3. Normalize TextureImporter settings.
4. Slice atlases and define borders.
5. Assign one stable semantic role to each reusable visual.
6. Generate preview thumbnails and metadata.
7. Run theme validation in the Visual Reskin Workbench.
8. Test the pack against a fixture adapter.
9. Version and publish the immutable package.

## Required binding fields

- `semanticRole`: stable function, not a filename.
- `assetGuid`: GUID of the texture or sprite asset.
- `spriteName`: exact imported Sprite name.
- `imageMode`: `simple`, `sliced`, `filled`, or `auto`.
- `preserveAspect`: whether replacement keeps aspect ratio.
- `scale`: default layout scale.
- `border`: optional left, bottom, right, top values.

## Versioning

- Patch: metadata, tags, or compatible visual correction.
- Minor: new semantic roles/assets.
- Major: breaking geometry, slicing, or role behavior.

Never modify a published version in place. Publish a new version so A/B tests
and historical builds remain reproducible.

## Future Visual RAG fields

Each binding will eventually include:

- thumbnail and CLIP-style embedding;
- dominant palette;
- aspect ratio and alpha coverage;
- rendering, shape, edge and lighting tags;
- target UI scale;
- quality score and reviewer evidence;
- compatible and incompatible semantic roles;
- license/source provenance.

