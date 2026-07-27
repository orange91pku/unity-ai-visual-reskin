from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath

from .features import cosine, extract_image_features, semantic_vector, tokenize
from .store import VisualRagStore, vector_from_row


def search(
    store: VisualRagStore,
    *,
    text: str | None = None,
    image: Path | None = None,
    semantic_role: str | None = None,
    source_kind: str | None = None,
    source_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    conditions = []
    parameters = []
    if source_kind:
        conditions.append("source_kind=?")
        parameters.append(source_kind)
    if source_id:
        conditions.append("source_id=?")
        parameters.append(source_id)
    if semantic_role:
        conditions.append("(semantic_role=? OR semantic_role LIKE ?)")
        parameters.extend([semantic_role, semantic_role + ".%"])
    rows = store.rows(" AND ".join(conditions), tuple(parameters))

    query_semantic = semantic_vector(text, semantic_role) if (text or semantic_role) else None
    query_visual = extract_image_features(image).visual_vector if image else None
    results = []
    for row in rows:
        semantic_score = (
            cosine(query_semantic, vector_from_row(row, "semantic_vector_json"))
            if query_semantic else 0.0
        )
        visual_score = (
            cosine(query_visual, vector_from_row(row, "visual_vector_json"))
            if query_visual else 0.0
        )
        exact_role = 1.0 if semantic_role and row["semantic_role"] == semantic_role else 0.0
        if query_semantic and query_visual:
            score = 0.45 * semantic_score + 0.45 * visual_score + 0.10 * exact_role
        elif query_visual:
            score = 0.90 * visual_score + 0.10 * exact_role
        elif query_semantic:
            score = 0.85 * semantic_score + 0.15 * exact_role
        else:
            score = float(row["reference_count"])
        results.append({
            "assetId": row["asset_id"],
            "sourceKind": row["source_kind"],
            "sourceId": row["source_id"],
            "semanticRole": row["semantic_role"],
            "unityGuid": row["unity_guid"],
            "spriteName": row["sprite_name"],
            "relativePath": row["relative_path"],
            "score": round(score, 6),
            "scores": {
                "semantic": round(semantic_score, 6),
                "visual": round(visual_score, 6),
                "exactRole": exact_role,
            },
            "dimensions": [row["width"], row["height"]],
            "palette": json.loads(row["palette_json"]),
            "referenceCount": row["reference_count"],
        })
    return sorted(results, key=lambda item: (-item["score"], -item["referenceCount"], item["assetId"]))[:limit]


def propose_mappings(
    store: VisualRagStore,
    project_id: str,
    theme_id: str,
    role_prefix: str | None = None,
    limit: int = 100,
    *,
    include_unreferenced: bool = False,
    include_editor_assets: bool = False,
) -> dict:
    source_rows = store.rows("source_kind='project' AND source_id=?", (project_id,))
    if role_prefix:
        destination_rows = store.rows(
            "source_kind='theme' AND source_id=? AND semantic_role LIKE ?",
            (theme_id, role_prefix + "%"),
        )
    else:
        destination_rows = store.rows(
            "source_kind='theme' AND source_id=?",
            (theme_id,),
        )
    usage_types: dict[str, set[str]] = {}
    with store.connect() as connection:
        for row in connection.execute(
            """
            SELECT asset_id, component_type
            FROM project_usages
            WHERE project_id=?
            """,
            (project_id,),
        ):
            usage_types.setdefault(row[0], set()).add(row[1])

    proposals = []
    for source in sorted(source_rows, key=lambda row: -row["reference_count"]):
        normalized_source_path = "/" + source["relative_path"].replace("\\", "/").lower().strip("/")
        if not include_editor_assets and "/editor/" in normalized_source_path:
            continue
        if not include_unreferenced and source["reference_count"] <= 0:
            continue
        source_visual = vector_from_row(source, "visual_vector_json")
        source_semantic = vector_from_row(source, "semantic_vector_json")
        source_name = source["sprite_name"] or PurePosixPath(source["relative_path"]).stem
        source_tokens = set(
            tokenize(source_name)
        )
        aliases = {
            "btn": "button",
            "panel": "surface",
            "background": "surface",
            "bg": "surface",
            "gear": "settings",
            "cog": "settings",
            "setting": "settings",
            "store": "shop",
            "ad": "video",
            "frame": "slot",
        }
        source_tokens.update(
            aliases[token] for token in list(source_tokens) if token in aliases
        )
        compact_source_name = "".join(tokenize(source_name))
        technical_name = any(
            token in compact_source_name
            for token in (
                "normalmap",
                "noisetexture",
                "roughness",
                "metallic",
                "occlusion",
                "heightmap",
            )
        )
        source_usage_types = {
            value for value in usage_types.get(source["asset_id"], set()) if value
        }
        material_only = bool(source_usage_types) and source_usage_types == {"Material"}
        candidates = []
        for destination in destination_rows:
            if technical_name or material_only:
                continue
            role_tokens = set(tokenize(destination["semantic_role"]))
            ordered_role_tokens = tokenize(destination["semantic_role"])
            specific_role_tokens = set(ordered_role_tokens[1:])
            required_tokens = specific_role_tokens or role_tokens
            if not required_tokens.issubset(source_tokens):
                continue
            if (
                source["unity_guid"]
                and source["unity_guid"] == destination["unity_guid"]
                and (
                    not source["sprite_name"]
                    or source["sprite_name"] == destination["sprite_name"]
                )
            ):
                continue
            if source["content_hash"] == destination["content_hash"]:
                continue
            visual_score = cosine(source_visual, vector_from_row(destination, "visual_vector_json"))
            semantic_score = cosine(
                source_semantic, vector_from_row(destination, "semantic_vector_json")
            )
            aspect_ratio_score = max(
                0.0,
                1.0 - abs(source["aspect_ratio"] - destination["aspect_ratio"]) /
                max(0.01, source["aspect_ratio"], destination["aspect_ratio"]),
            )
            destination_extra = json.loads(destination["extra_json"])
            destination_role = destination["semantic_role"] or ""
            if (
                destination_role.startswith("icon.")
                or destination_role == "button.close"
            ) and aspect_ratio_score < 0.65:
                continue
            if (
                destination_extra.get("imageMode") == "simple"
                and aspect_ratio_score < 0.50
            ):
                continue
            score = 0.55 * visual_score + 0.25 * semantic_score + 0.20 * aspect_ratio_score
            candidates.append((score, visual_score, semantic_score, aspect_ratio_score, destination))
        if not candidates:
            continue
        score, visual, semantic, aspect, destination = max(candidates, key=lambda item: item[0])
        proposal_key = "|".join(
            [project_id, theme_id, source["asset_id"], destination["asset_id"]]
        )
        proposals.append({
            "proposalId": "vrmap_" + hashlib.sha256(
                proposal_key.encode("utf-8")
            ).hexdigest()[:32],
            "source": {
                "assetId": source["asset_id"],
                "unityGuid": source["unity_guid"],
                "spriteName": source["sprite_name"],
                "relativePath": source["relative_path"],
                "contentHash": source["content_hash"],
            },
            "destination": {
                "assetId": destination["asset_id"],
                "themeId": theme_id,
                "unityGuid": destination["unity_guid"],
                "spriteName": destination["sprite_name"],
                "semanticRole": destination["semantic_role"],
                "relativePath": destination["relative_path"],
            },
            "score": round(score, 6),
            "scoreBreakdown": {
                "visual": round(visual, 6),
                "semantic": round(semantic, 6),
                "aspectRatio": round(aspect, 6),
            },
            "technicalConstraints": json.loads(destination["extra_json"]),
            "evidence": {
                "sourceReferenceCount": source["reference_count"],
                "sourceDimensions": [source["width"], source["height"]],
                "destinationDimensions": [destination["width"], destination["height"]],
            },
            "approval": {"status": "pending", "required": True},
        })
        if len(proposals) >= limit:
            break
    envelope = {
        "schema": "hydracore.visual-rag.mapping-proposals/v1",
        "projectId": project_id,
        "themeId": theme_id,
        "createdUtc": datetime.now(timezone.utc).isoformat(),
        "mutationAuthorized": False,
        "proposals": proposals,
    }
    store.initialize()
    with store.connect() as connection:
        connection.execute(
            "DELETE FROM mapping_proposals WHERE project_id=? AND theme_id=?",
            (project_id, theme_id),
        )
        for proposal in proposals:
            connection.execute(
                """INSERT INTO mapping_proposals(
                    proposal_id,project_id,theme_id,source_asset_id,destination_asset_id,
                    score,score_json,explanation_json,approval_status,created_utc
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    proposal["proposalId"],
                    project_id,
                    theme_id,
                    proposal["source"]["assetId"],
                    proposal["destination"]["assetId"],
                    proposal["score"],
                    json.dumps(proposal["scoreBreakdown"], sort_keys=True),
                    json.dumps(
                        {
                            "technicalConstraints": proposal["technicalConstraints"],
                            "evidence": proposal["evidence"],
                        },
                        sort_keys=True,
                    ),
                    "pending",
                    envelope["createdUtc"],
                ),
            )
    return envelope
