from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import UnidentifiedImageError

from .features import extract_image_features, semantic_vector
from .identity import fingerprint, sha256_file, stable_asset_id
from .store import VisualRagStore
from .unity_meta import (
    find_serialized_references,
    parse_sprite_file_ids,
    parse_sprite_rects,
    read_guid,
)


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp"}
SERIALIZED_EXTENSIONS = {".unity", ".prefab", ".asset", ".mat", ".controller", ".spriteatlas"}
DEFAULT_EXCLUDED_PARTS = {
    "library", "temp", "obj", "logs", "build", "builds", "userSettings", ".git",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(
    *,
    source_kind: str,
    source_id: str,
    source_version: str | None,
    role: str | None,
    tags: list[str],
    guid: str | None,
    sprite_name: str | None,
    relative_path: str,
    content_hash: str,
    features,
    license_id: str | None,
    provenance: str | None,
    reference_count: int,
    extra: dict,
) -> dict:
    return {
        "asset_id": stable_asset_id(
            source_kind, source_id, guid, relative_path, sprite_name, role
        ),
        "source_kind": source_kind,
        "source_id": source_id,
        "source_version": source_version,
        "semantic_role": role,
        "tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
        "unity_guid": guid,
        "sprite_name": sprite_name,
        "relative_path": relative_path.replace("\\", "/"),
        "content_hash": content_hash,
        "width": features.width,
        "height": features.height,
        "aspect_ratio": features.aspect_ratio,
        "alpha_coverage": features.alpha_coverage,
        "opaque_bounds_ratio": features.opaque_bounds_ratio,
        "brightness": features.brightness,
        "saturation": features.saturation,
        "edge_density": features.edge_density,
        "palette_json": json.dumps(features.dominant_palette),
        "perceptual_hash": features.perceptual_hash,
        "visual_provider": "hydracore.visual-features.v1",
        "visual_vector_json": json.dumps(features.visual_vector),
        "semantic_provider": "hydracore.semantic-hash.v1",
        "semantic_vector_json": json.dumps(
            semantic_vector(role, " ".join(tags), relative_path, sprite_name)
        ),
        "license_id": license_id,
        "provenance": provenance,
        "reference_count": reference_count,
        "extra_json": json.dumps(extra, ensure_ascii=False, sort_keys=True),
        "updated_utc": utc_now(),
    }


def ingest_theme(store: VisualRagStore, manifest_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    theme_id = manifest["themeId"]
    theme_root = manifest_path.parent.parent
    guid_to_asset: dict[str, Path] = {}
    sprite_rects: dict[str, dict] = {}
    for meta in theme_root.rglob("*.meta"):
        guid = read_guid(meta)
        asset = Path(str(meta)[:-5])
        if guid and asset.exists() and asset.suffix.casefold() in IMAGE_EXTENSIONS:
            guid_to_asset[guid] = asset
            sprite_rects[guid] = parse_sprite_rects(meta)

    existing = {
        row["asset_id"]: row
        for row in store.rows("source_kind='theme' AND source_id=?", (theme_id,))
    }
    records = []
    reused = 0
    warnings = []
    style_tags = [str(value) for value in manifest.get("styleTags", [])]
    for binding in manifest.get("assets", []):
        guid = str(binding.get("assetGuid", "")).lower()
        image_path = guid_to_asset.get(guid)
        if image_path is None:
            warnings.append(f"Unresolved GUID {guid} for {binding.get('semanticRole')}")
            continue
        sprite_name = binding.get("spriteName")
        rect = sprite_rects.get(guid, {}).get(sprite_name) if sprite_name else None
        relative = image_path.relative_to(theme_root).as_posix()
        tags = style_tags + [str(value) for value in binding.get("tags", [])]
        content_hash = sha256_file(image_path)
        asset_id = stable_asset_id(
            "theme", theme_id, guid, relative, sprite_name, binding.get("semanticRole")
        )
        cached = existing.get(asset_id)
        if cached and cached["content_hash"] == content_hash:
            cached["source_version"] = manifest.get("version")
            cached["tags_json"] = json.dumps(tags, ensure_ascii=False, sort_keys=True)
            cached["semantic_vector_json"] = json.dumps(
                semantic_vector(
                    binding.get("semanticRole"), " ".join(tags), relative, sprite_name
                )
            )
            cached["license_id"] = manifest.get("license", {}).get("id")
            cached["provenance"] = manifest.get("provenance")
            cached["extra_json"] = json.dumps(
                {
                    "imageMode": binding.get("imageMode", "simple"),
                    "preserveAspect": binding.get("preserveAspect", True),
                    "scale": binding.get("scale", 1.0),
                    "border": binding.get("border"),
                    "spriteRect": rect.__dict__ if rect else None,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            cached["updated_utc"] = utc_now()
            records.append(cached)
            reused += 1
            continue
        try:
            features = extract_image_features(image_path, rect)
        except (OSError, UnidentifiedImageError) as error:
            warnings.append(f"Unreadable image {image_path}: {error}")
            continue
        records.append(
            _record(
                source_kind="theme",
                source_id=theme_id,
                source_version=manifest.get("version"),
                role=binding.get("semanticRole"),
                tags=tags,
                guid=guid,
                sprite_name=sprite_name,
                relative_path=relative,
                content_hash=content_hash,
                features=features,
                license_id=manifest.get("license", {}).get("id"),
                provenance=manifest.get("provenance"),
                reference_count=0,
                extra={
                    "imageMode": binding.get("imageMode", "simple"),
                    "preserveAspect": binding.get("preserveAspect", True),
                    "scale": binding.get("scale", 1.0),
                    "border": binding.get("border"),
                    "spriteRect": rect.__dict__ if rect else None,
                },
            )
        )
    store.replace_source("theme", theme_id, records)
    return {
        "source": theme_id,
        "assets": len(records),
        "reused": reused,
        "computed": len(records) - reused,
        "warnings": warnings,
    }


def _is_excluded(path: Path, root: Path) -> bool:
    relative_parts = {part.casefold() for part in path.relative_to(root).parts}
    return bool(relative_parts & {part.casefold() for part in DEFAULT_EXCLUDED_PARTS})


def ingest_project(
    store: VisualRagStore,
    project_root: Path,
    project_id: str,
    context_path: Path | None = None,
) -> dict:
    project_root = project_root.resolve()
    assets_root = project_root / "Assets"
    if not assets_root.is_dir():
        raise ValueError(f"Unity Assets directory not found: {assets_root}")

    reference_counts: Counter[tuple[str, str]] = Counter()
    usage_rows: list[dict] = []
    serialized_files = [
        path for path in assets_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in SERIALIZED_EXTENSIONS
    ]
    for owner in serialized_files:
        if _is_excluded(owner, project_root):
            continue
        for guid, file_id in find_serialized_references(owner):
            reference_counts[(guid, file_id)] += 1
            usage_rows.append({
                "guid": guid,
                "fileId": file_id,
                "ownerPath": owner.relative_to(project_root).as_posix(),
                "hierarchyPath": None,
                "componentType": None,
                "evidenceKind": "unity-yaml-reference",
            })

    external_context = None
    if context_path:
        external_context = json.loads(context_path.read_text(encoding="utf-8"))
        if external_context.get("schema") != "hydracore.project-brain.visual-context/v1":
            raise ValueError("Unsupported Project Brain visual context schema")
        for usage in external_context.get("usages", []):
            usage_rows.append({
                "guid": usage["unityGuid"].lower(),
                "fileId": str(usage.get("fileId", "")),
                "ownerPath": usage["ownerPath"],
                "hierarchyPath": usage.get("hierarchyPath"),
                "componentType": usage.get("componentType"),
                "evidenceKind": "project-brain",
            })
            reference_counts[
                (usage["unityGuid"].lower(), str(usage.get("fileId", "")))
            ] += int(usage.get("referenceCount", 1))

    guid_reference_counts: Counter[str] = Counter()
    for (reference_guid, _), count in reference_counts.items():
        guid_reference_counts[reference_guid] += count

    existing = {
        row["asset_id"]: row
        for row in store.rows("source_kind='project' AND source_id=?", (project_id,))
    }
    records = []
    reused = 0
    warnings = []
    for image_path in assets_root.rglob("*"):
        if (
            not image_path.is_file()
            or image_path.suffix.casefold() not in IMAGE_EXTENSIONS
            or _is_excluded(image_path, project_root)
        ):
            continue
        meta_path = Path(str(image_path) + ".meta")
        guid = read_guid(meta_path)
        relative = image_path.relative_to(project_root).as_posix()
        content_hash = sha256_file(image_path)
        rects = parse_sprite_rects(meta_path)
        file_ids = parse_sprite_file_ids(meta_path)
        candidates = [
            (sprite_name, rect, file_ids.get(sprite_name))
            for sprite_name, rect in rects.items()
        ] or [(None, None, None)]
        for sprite_name, rect, sprite_file_id in candidates:
            semantic_name = sprite_name or image_path.stem
            name_tokens = re.sub(r"[_\-.]+", " ", semantic_name)
            asset_id = stable_asset_id(
                "project", project_id, guid, relative, sprite_name
            )
            exact_count = reference_counts.get((guid or "", sprite_file_id or ""), 0)
            guid_count = guid_reference_counts.get(guid or "", 0)
            reference_count = exact_count if sprite_name else guid_count
            cached = existing.get(asset_id)
            if cached and cached["content_hash"] == content_hash:
                cached["tags_json"] = json.dumps(
                    [name_tokens], ensure_ascii=False, sort_keys=True
                )
                cached["reference_count"] = reference_count
                cached["extra_json"] = json.dumps(
                    {
                        "metaPresent": meta_path.exists(),
                        "fileId": sprite_file_id,
                        "spriteRect": rect.__dict__ if rect else None,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                cached["updated_utc"] = utc_now()
                records.append(cached)
                reused += 1
                continue
            try:
                features = extract_image_features(image_path, rect)
            except (OSError, UnidentifiedImageError) as error:
                warnings.append(f"Unreadable image {image_path}: {error}")
                continue
            records.append(
                _record(
                    source_kind="project",
                    source_id=project_id,
                    source_version=None,
                    role=None,
                    tags=[name_tokens],
                    guid=guid,
                    sprite_name=sprite_name,
                    relative_path=relative,
                    content_hash=content_hash,
                    features=features,
                    license_id=None,
                    provenance="unity-project",
                    reference_count=reference_count,
                    extra={
                        "metaPresent": meta_path.exists(),
                        "fileId": sprite_file_id,
                        "spriteRect": rect.__dict__ if rect else None,
                    },
                )
            )

    store.replace_source("project", project_id, records)
    by_guid_file: dict[tuple[str, str | None], str] = {}
    for record in records:
        if not record["unity_guid"]:
            continue
        extra = json.loads(record["extra_json"])
        by_guid_file[(record["unity_guid"], extra.get("fileId"))] = record["asset_id"]
    index_values = [
        f"{record['asset_id']}:{record['content_hash']}:{record['reference_count']}"
        for record in records
    ]
    index_fingerprint = (
        external_context.get("indexFingerprint")
        if external_context
        else fingerprint(index_values)
    )
    store.initialize()
    with store.connect() as connection:
        connection.execute("DELETE FROM project_usages WHERE project_id=?", (project_id,))
        counts: Counter[tuple] = Counter()
        details: dict[tuple, dict] = {}
        for usage in usage_rows:
            asset_id = by_guid_file.get((usage["guid"], usage["fileId"]))
            if not asset_id:
                asset_id = by_guid_file.get((usage["guid"], None))
            if not asset_id:
                continue
            key = (
                asset_id, usage["guid"], usage["fileId"], usage["ownerPath"],
                usage["hierarchyPath"], usage["componentType"], usage["evidenceKind"],
            )
            counts[key] += 1
            details[key] = usage
        for key, count in counts.items():
            asset_id, guid, file_id, owner, hierarchy, component, evidence = key
            connection.execute(
                """INSERT INTO project_usages(
                    project_id,index_fingerprint,asset_id,unity_guid,file_id,owner_path,
                    hierarchy_path,component_type,evidence_kind,reference_count
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    project_id, index_fingerprint, asset_id, guid, file_id, owner,
                    hierarchy, component, evidence, count,
                ),
            )
    return {
        "source": project_id,
        "assets": len(records),
        "reused": reused,
        "computed": len(records) - reused,
        "serializedFiles": len(serialized_files),
        "references": sum(reference_counts.values()),
        "indexFingerprint": index_fingerprint,
        "warnings": warnings,
    }
