from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_asset_id(
    source_kind: str,
    source_id: str,
    unity_guid: str | None,
    relative_path: str,
    sprite_name: str | None = None,
    semantic_role: str | None = None,
) -> str:
    identity = "|".join(
        [
            source_kind.casefold(),
            source_id.casefold(),
            (unity_guid or "").casefold(),
            relative_path.replace("\\", "/").casefold(),
            (sprite_name or "").casefold(),
            (semantic_role or "").casefold(),
        ]
    )
    return "vrag_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]


def fingerprint(values: list[str]) -> str:
    body = "\n".join(sorted(values))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
