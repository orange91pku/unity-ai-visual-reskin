from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


SERIALIZED_EXTENSIONS = {
    ".anim",
    ".asset",
    ".controller",
    ".mat",
    ".prefab",
    ".spriteatlas",
    ".unity",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _inside(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = (root / Path(relative_path)).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"Path escapes root: {relative_path}")
    return candidate


def _find_proposal(envelope: dict, proposal_id: str) -> dict:
    for proposal in envelope.get("proposals", []):
        if proposal.get("proposalId") == proposal_id:
            return proposal
    raise ValueError(f"Proposal not found: {proposal_id}")


def _unity_guid(meta_path: Path) -> str:
    match = re.search(
        r"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$",
        meta_path.read_text(encoding="utf-8-sig"),
    )
    if not match:
        raise ValueError(f"Unity GUID not found in {meta_path}")
    return match.group(1).lower()


def _serialized_reference_count(project_root: Path, guid: str) -> int:
    encoded_guid = guid.lower().encode("ascii")
    count = 0
    for path in (project_root / "Assets").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SERIALIZED_EXTENSIONS:
            continue
        count += path.read_bytes().lower().count(encoded_guid)
    return count


def _image_facts(path: Path) -> tuple[int, int, str]:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        alpha_hash = hashlib.sha256(rgba.getchannel("A").tobytes()).hexdigest()
        return rgba.width, rgba.height, alpha_hash


def materialize_candidate(
    proposal_file: Path,
    proposal_id: str,
    project_root: Path,
    theme_root: Path,
    output_dir: Path,
    *,
    preserve_alpha: bool = True,
) -> dict:
    proposal_file = proposal_file.resolve()
    project_root = project_root.resolve()
    theme_root = theme_root.resolve()
    output_dir = output_dir.resolve()
    envelope = _load_json(proposal_file)
    proposal = _find_proposal(envelope, proposal_id)

    source_relative = proposal["source"]["relativePath"]
    source_path = _inside(project_root, source_relative)
    source_meta = Path(str(source_path) + ".meta")
    atlas_path = _inside(theme_root, proposal["destination"]["relativePath"])
    if not source_path.is_file() or not source_meta.is_file():
        raise FileNotFoundError(f"Source image or meta is missing: {source_path}")
    if not atlas_path.is_file():
        raise FileNotFoundError(f"Theme atlas is missing: {atlas_path}")

    source_hash = _sha256(source_path)
    expected_source_hash = proposal["source"].get("contentHash")
    if expected_source_hash and source_hash != expected_source_hash:
        raise ValueError("Source image changed after proposal generation")
    source_guid = _unity_guid(source_meta)
    expected_guid = (proposal["source"].get("unityGuid") or "").lower()
    if expected_guid and source_guid != expected_guid:
        raise ValueError("Source GUID does not match mapping proposal")

    sprite_rect = proposal.get("technicalConstraints", {}).get("spriteRect")
    if not sprite_rect:
        raise ValueError("Destination has no spriteRect; atlas extraction is unsafe")
    x = int(sprite_rect["x"])
    y = int(sprite_rect["y"])
    width = int(sprite_rect["width"])
    height = int(sprite_rect["height"])

    with Image.open(source_path) as source_image, Image.open(atlas_path) as atlas_image:
        source = source_image.convert("RGBA")
        atlas = atlas_image.convert("RGBA")
        top = atlas.height - y - height
        if x < 0 or top < 0 or x + width > atlas.width or top + height > atlas.height:
            raise ValueError("spriteRect is outside the destination atlas")
        replacement = atlas.crop((x, top, x + width, top + height))
        replacement = replacement.resize(source.size, Image.Resampling.LANCZOS)
        if preserve_alpha:
            replacement.putalpha(source.getchannel("A"))

        output_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = output_dir / f"{proposal_id}-{source_path.name}"
        replacement.save(candidate_path, format="PNG", optimize=True)

    source_width, source_height, source_alpha = _image_facts(source_path)
    candidate_width, candidate_height, candidate_alpha = _image_facts(candidate_path)
    if (source_width, source_height) != (candidate_width, candidate_height):
        raise AssertionError("Candidate dimensions do not match source dimensions")
    if preserve_alpha and source_alpha != candidate_alpha:
        raise AssertionError("Candidate alpha mask does not match source alpha mask")

    manifest = {
        "schema": "hydracore.visual-rag.raster-candidate/v1",
        "createdUtc": _utc_now(),
        "proposalId": proposal_id,
        "projectId": envelope.get("projectId"),
        "themeId": envelope.get("themeId"),
        "approval": {"status": "pending", "required": True},
        "source": {
            "relativePath": source_relative,
            "sha256": source_hash,
            "metaSha256": _sha256(source_meta),
            "unityGuid": source_guid,
            "dimensions": [source_width, source_height],
            "alphaSha256": source_alpha,
        },
        "destination": {
            "relativePath": proposal["destination"]["relativePath"],
            "spriteName": proposal["destination"].get("spriteName"),
            "semanticRole": proposal["destination"].get("semanticRole"),
            "atlasSha256": _sha256(atlas_path),
            "spriteRect": sprite_rect,
        },
        "candidate": {
            "path": str(candidate_path),
            "sha256": _sha256(candidate_path),
            "dimensions": [candidate_width, candidate_height],
            "alphaSha256": candidate_alpha,
            "preserveAlpha": preserve_alpha,
        },
    }
    manifest_path = output_dir / f"{proposal_id}-candidate.json"
    _write_json(manifest_path, manifest)
    return {"ok": True, "manifest": str(manifest_path), **manifest}


def apply_candidate(
    candidate_manifest: Path,
    approval_id: str,
    project_root: Path,
    backup_root: Path,
) -> dict:
    candidate_manifest = candidate_manifest.resolve()
    project_root = project_root.resolve()
    backup_root = backup_root.resolve()
    manifest = _load_json(candidate_manifest)
    proposal_id = manifest["proposalId"]
    if approval_id != proposal_id:
        raise ValueError("Approval id must exactly match proposalId")

    source_path = _inside(project_root, manifest["source"]["relativePath"])
    source_meta = Path(str(source_path) + ".meta")
    candidate_path = Path(manifest["candidate"]["path"]).resolve()
    if _sha256(source_path) != manifest["source"]["sha256"]:
        raise ValueError("Source image changed after candidate materialization")
    if _sha256(source_meta) != manifest["source"]["metaSha256"]:
        raise ValueError("Source .meta changed after candidate materialization")
    if _sha256(candidate_path) != manifest["candidate"]["sha256"]:
        raise ValueError("Candidate image changed after materialization")

    reference_count = _serialized_reference_count(
        project_root, manifest["source"]["unityGuid"]
    )
    transaction_dir = backup_root / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + proposal_id
    )
    transaction_dir.mkdir(parents=True, exist_ok=False)
    image_backup = transaction_dir / source_path.name
    meta_backup = transaction_dir / (source_path.name + ".meta")
    shutil.copy2(source_path, image_backup)
    shutil.copy2(source_meta, meta_backup)

    transaction = {
        "schema": "hydracore.visual-rag.raster-transaction/v1",
        "transactionId": transaction_dir.name,
        "createdUtc": _utc_now(),
        "state": "applying",
        "proposalId": proposal_id,
        "approvalId": approval_id,
        "projectRoot": str(project_root),
        "sourceRelativePath": manifest["source"]["relativePath"],
        "backupImage": str(image_backup),
        "backupMeta": str(meta_backup),
        "pre": {
            "imageSha256": manifest["source"]["sha256"],
            "metaSha256": manifest["source"]["metaSha256"],
            "unityGuid": manifest["source"]["unityGuid"],
            "dimensions": manifest["source"]["dimensions"],
            "alphaSha256": manifest["source"]["alphaSha256"],
            "serializedReferenceCount": reference_count,
        },
    }
    transaction_path = transaction_dir / "transaction.json"
    _write_json(transaction_path, transaction)

    temporary = source_path.with_name(source_path.name + ".revisual.tmp")
    try:
        shutil.copyfile(candidate_path, temporary)
        os.replace(temporary, source_path)
        post_width, post_height, post_alpha = _image_facts(source_path)
        post = {
            "imageSha256": _sha256(source_path),
            "metaSha256": _sha256(source_meta),
            "unityGuid": _unity_guid(source_meta),
            "dimensions": [post_width, post_height],
            "alphaSha256": post_alpha,
            "serializedReferenceCount": _serialized_reference_count(
                project_root, manifest["source"]["unityGuid"]
            ),
        }
        invariants = {
            "imageChanged": post["imageSha256"] != transaction["pre"]["imageSha256"],
            "metaUnchanged": post["metaSha256"] == transaction["pre"]["metaSha256"],
            "guidUnchanged": post["unityGuid"] == transaction["pre"]["unityGuid"],
            "dimensionsUnchanged": post["dimensions"] == transaction["pre"]["dimensions"],
            "alphaUnchanged": (
                not manifest["candidate"]["preserveAlpha"]
                or post["alphaSha256"] == transaction["pre"]["alphaSha256"]
            ),
            "referencesUnchanged": (
                post["serializedReferenceCount"]
                == transaction["pre"]["serializedReferenceCount"]
            ),
        }
        if not all(invariants.values()):
            raise AssertionError(f"Post-apply invariant failed: {invariants}")
        transaction.update(
            {
                "state": "applied",
                "appliedUtc": _utc_now(),
                "post": post,
                "invariants": invariants,
            }
        )
        _write_json(transaction_path, transaction)
        return {"ok": True, "transaction": str(transaction_path), **transaction}
    except Exception as error:
        if temporary.exists():
            temporary.unlink()
        shutil.copy2(image_backup, source_path)
        shutil.copy2(meta_backup, source_meta)
        transaction.update(
            {
                "state": "rolled_back",
                "rolledBackUtc": _utc_now(),
                "error": str(error),
            }
        )
        _write_json(transaction_path, transaction)
        raise


def rollback_transaction(transaction_manifest: Path) -> dict:
    transaction_manifest = transaction_manifest.resolve()
    transaction = _load_json(transaction_manifest)
    project_root = Path(transaction["projectRoot"]).resolve()
    source_path = _inside(project_root, transaction["sourceRelativePath"])
    source_meta = Path(str(source_path) + ".meta")
    backup_image = Path(transaction["backupImage"]).resolve()
    backup_meta = Path(transaction["backupMeta"]).resolve()
    shutil.copy2(backup_image, source_path)
    shutil.copy2(backup_meta, source_meta)
    restored = {
        "imageSha256": _sha256(source_path),
        "metaSha256": _sha256(source_meta),
        "unityGuid": _unity_guid(source_meta),
    }
    if restored["imageSha256"] != transaction["pre"]["imageSha256"]:
        raise AssertionError("Rollback image hash does not match pre-apply hash")
    if restored["metaSha256"] != transaction["pre"]["metaSha256"]:
        raise AssertionError("Rollback meta hash does not match pre-apply hash")
    transaction.update(
        {
            "state": "rolled_back",
            "rolledBackUtc": _utc_now(),
            "restored": restored,
        }
    )
    _write_json(transaction_manifest, transaction)
    return {"ok": True, "transaction": str(transaction_manifest), **transaction}
