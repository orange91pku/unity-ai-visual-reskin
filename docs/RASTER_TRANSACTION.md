# Approval-gated raster transactions

The raster workflow replaces image bytes without changing Unity identity.

## Pipeline

1. `propose` emits semantic/visual candidates with `mutationAuthorized=false`.
2. A reviewer selects a proposal ID.
3. `materialize-raster` extracts the selected Sprite from its atlas, converts
   Unity's bottom-left Sprite rectangle to image coordinates, resizes it to the
   source dimensions, and preserves the source alpha mask by default.
4. The generated preview and candidate manifest remain outside `Assets`.
5. `apply-raster --approve <proposalId>` verifies that proposal, source image,
   source `.meta`, GUID, and candidate have not changed.
6. The engine backs up the image and `.meta`, atomically replaces only the image
   bytes, and verifies all invariants.
7. Unity CLI gates compare compile errors and Missing Script evidence before and
   after the transaction.

## Hard invariants

- `.meta` SHA-256 is unchanged.
- Unity GUID is unchanged.
- pixel dimensions are unchanged.
- serialized GUID reference count is unchanged.
- alpha SHA-256 is unchanged unless an operator explicitly uses
  `--allow-alpha-change`.
- any failed invariant causes immediate restoration.

The alpha gate is important for recovered Unity projects that contain
serialized tight Sprite meshes. Preserving alpha prevents the new raster from
escaping or being clipped unexpectedly by the old mesh.

## Baseline-red projects

Recovered projects may already fail compilation because vendor packages are
missing. In that case, the gate compares normalized unique compiler errors and
Missing Script GUID sets:

- no new compiler error may appear;
- no new missing-script GUID may appear;
- identity and raster invariants must still pass.

This is a delta gate, not a claim that the project itself is healthy.
