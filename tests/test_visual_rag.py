from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from revisual_rag.features import extract_image_features
from revisual_rag.identity import stable_asset_id
from revisual_rag.ingest import ingest_project, ingest_theme
from revisual_rag.retrieval import propose_mappings, search
from revisual_rag.raster_transaction import (
    apply_candidate,
    materialize_candidate,
    rollback_transaction,
)
from revisual_rag.store import VisualRagStore
from revisual_rag.unity_meta import parse_sprite_file_ids, parse_sprite_rects


GUID = "0123456789abcdef0123456789abcdef"
PROJECT_GUID = "fedcba9876543210fedcba9876543210"
WIDE_GUID = "11111111111111111111111111111111"
UNUSED_GUID = "22222222222222222222222222222222"
EDITOR_GUID = "33333333333333333333333333333333"


def make_png(path: Path, color: tuple[int, int, int, int], size=(64, 64)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, size[0] - 5, size[1] - 5), radius=10, fill=color)
    image.save(path)


class VisualRagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = VisualRagStore(self.root / "visual-rag.sqlite3")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _theme(self) -> Path:
        theme_root = self.root / "theme"
        image_path = theme_root / "Art" / "button.png"
        make_png(image_path, (20, 180, 250, 255))
        Path(str(image_path) + ".meta").write_text(
            f"fileFormatVersion: 2\nguid: {GUID}\n", encoding="utf-8"
        )
        manifest_path = theme_root / "Theme" / "hydra-theme.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps({
                "schemaVersion": 1,
                "themeId": "test.theme",
                "displayName": "Test Theme",
                "version": "1.0.0",
                "styleTags": ["rounded", "cyan"],
                "assets": [
                    {
                        "semanticRole": "button.primary",
                        "assetGuid": GUID,
                        "imageMode": "sliced",
                        "border": [8, 8, 8, 8],
                    }
                ],
            }),
            encoding="utf-8",
        )
        return manifest_path

    def _project(self) -> Path:
        project = self.root / "project"
        image_path = project / "Assets" / "UI" / "old_primary_button.png"
        make_png(image_path, (15, 150, 230, 255), (80, 60))
        Path(str(image_path) + ".meta").write_text(
            f"fileFormatVersion: 2\nguid: {PROJECT_GUID}\n", encoding="utf-8"
        )
        scene = project / "Assets" / "Scenes" / "Home.unity"
        scene.parent.mkdir(parents=True)
        scene.write_text(
            f"m_Sprite: {{fileID: 21300000, guid: {PROJECT_GUID}, type: 3}}\n",
            encoding="utf-8",
        )
        return project

    def test_stable_identity_separates_semantic_bindings(self) -> None:
        first = stable_asset_id("theme", "x", GUID, "a.png", "sprite", "button.primary")
        second = stable_asset_id("theme", "x", GUID, "a.png", "sprite", "button.purchase")
        self.assertNotEqual(first, second)
        self.assertEqual(
            first,
            stable_asset_id("theme", "x", GUID, "a.png", "sprite", "button.primary"),
        )

    def test_theme_ingestion_and_retrieval(self) -> None:
        result = ingest_theme(self.store, self._theme())
        self.assertEqual(1, result["assets"])
        matches = search(
            self.store,
            text="rounded primary button",
            semantic_role="button.primary",
            source_kind="theme",
        )
        self.assertEqual("button.primary", matches[0]["semanticRole"])
        self.assertGreater(matches[0]["score"], 0.5)

    def test_project_usage_and_pending_proposal(self) -> None:
        ingest_theme(self.store, self._theme())
        result = ingest_project(self.store, self._project(), "test.project")
        self.assertEqual(1, result["assets"])
        self.assertEqual(1, result["references"])
        proposal = propose_mappings(self.store, "test.project", "test.theme")
        self.assertEqual(1, len(proposal["proposals"]))
        self.assertFalse(proposal["mutationAuthorized"])
        self.assertEqual("pending", proposal["proposals"][0]["approval"]["status"])

    def test_proposal_excludes_unreferenced_and_editor_assets_by_default(self) -> None:
        ingest_theme(self.store, self._theme())
        project = self._project()

        unused = project / "Assets" / "UI" / "old_primary_button_unused.png"
        make_png(unused, (15, 150, 230, 255), (80, 60))
        Path(str(unused) + ".meta").write_text(
            f"fileFormatVersion: 2\nguid: {UNUSED_GUID}\n", encoding="utf-8"
        )

        editor = project / "Assets" / "ThirdParty" / "Editor" / "old_primary_button.png"
        make_png(editor, (15, 150, 230, 255), (80, 60))
        Path(str(editor) + ".meta").write_text(
            f"fileFormatVersion: 2\nguid: {EDITOR_GUID}\n", encoding="utf-8"
        )
        scene = project / "Assets" / "Scenes" / "Home.unity"
        with scene.open("a", encoding="utf-8") as stream:
            stream.write(
                f"m_EditorIcon: {{fileID: 21300000, guid: {EDITOR_GUID}, type: 3}}\n"
            )

        ingest_project(self.store, project, "test.project")
        safe = propose_mappings(
            self.store, "test.project", "test.theme", limit=20
        )["proposals"]
        self.assertEqual(
            [PROJECT_GUID],
            [item["source"]["unityGuid"] for item in safe],
        )

        broad = propose_mappings(
            self.store,
            "test.project",
            "test.theme",
            limit=20,
            include_unreferenced=True,
            include_editor_assets=True,
        )["proposals"]
        self.assertEqual(
            {PROJECT_GUID, UNUSED_GUID, EDITOR_GUID},
            {item["source"]["unityGuid"] for item in broad},
        )

    def test_visual_similarity_prefers_same_art(self) -> None:
        manifest = self._theme()
        ingest_theme(self.store, manifest)
        query_image = manifest.parent.parent / "Art" / "button.png"
        matches = search(self.store, image=query_image, source_kind="theme")
        self.assertGreater(matches[0]["scores"]["visual"], 0.99)

    def test_proposal_rejects_wide_banner_for_square_icon(self) -> None:
        manifest_path = self._theme()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["assets"].append(
            {
                "semanticRole": "icon.settings",
                "assetGuid": GUID,
                "imageMode": "simple",
                "preserveAspect": True,
            }
        )
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        ingest_theme(self.store, manifest_path)

        project = self._project()
        banner = project / "Assets" / "UI" / "tx_settings.png"
        make_png(banner, (80, 120, 220, 255), (264, 72))
        Path(str(banner) + ".meta").write_text(
            f"fileFormatVersion: 2\nguid: {WIDE_GUID}\n",
            encoding="utf-8",
        )
        ingest_project(self.store, project, "test.project")
        proposals = propose_mappings(
            self.store, "test.project", "test.theme", limit=20
        )["proposals"]
        self.assertFalse(
            any(
                item["source"]["unityGuid"] == WIDE_GUID
                and item["destination"]["semanticRole"] == "icon.settings"
                for item in proposals
            )
        )

    def test_sprite_rect_parser(self) -> None:
        meta = self.root / "atlas.png.meta"
        meta.write_text(
            """fileFormatVersion: 2
guid: 11111111111111111111111111111111
TextureImporter:
  internalIDToNameTable:
  - first:
      213: 123456
    second: icon_play
  spriteSheet:
    serializedVersion: 2
    sprites:
    - serializedVersion: 2
      name: icon_play
      rect:
        serializedVersion: 2
        x: 10
        y: 20
        width: 30
        height: 40
      alignment: 0
""",
            encoding="utf-8",
        )
        rect = parse_sprite_rects(meta)["icon_play"]
        self.assertEqual((10, 20, 30, 40), (rect.x, rect.y, rect.width, rect.height))
        self.assertEqual("123456", parse_sprite_file_ids(meta)["icon_play"])

    def test_database_integrity(self) -> None:
        self.store.initialize()
        self.assertTrue(self.store.integrity()["ok"])

    def test_raster_transaction_preserves_unity_identity_and_rolls_back(self) -> None:
        project = self._project()
        source = project / "Assets" / "UI" / "old_primary_button.png"
        source_meta = Path(str(source) + ".meta")
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        meta_hash = hashlib.sha256(source_meta.read_bytes()).hexdigest()

        theme_root = self.root / "theme-atlas"
        atlas = theme_root / "Art" / "atlas.png"
        atlas.parent.mkdir(parents=True)
        atlas_image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        atlas_draw = ImageDraw.Draw(atlas_image)
        atlas_draw.rectangle((10, 10, 29, 29), fill=(220, 40, 80, 255))
        atlas_image.save(atlas)

        proposal_id = "vrmap_transaction_test"
        proposal_file = self.root / "proposal.json"
        proposal_file.write_text(
            json.dumps(
                {
                    "projectId": "test.project",
                    "themeId": "test.theme",
                    "proposals": [
                        {
                            "proposalId": proposal_id,
                            "source": {
                                "relativePath": "Assets/UI/old_primary_button.png",
                                "contentHash": source_hash,
                                "unityGuid": PROJECT_GUID,
                            },
                            "destination": {
                                "relativePath": "Art/atlas.png",
                                "spriteName": "settings",
                                "semanticRole": "icon.settings",
                            },
                            "technicalConstraints": {
                                "spriteRect": {
                                    "x": 10,
                                    "y": 10,
                                    "width": 20,
                                    "height": 20,
                                }
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        candidate = materialize_candidate(
            proposal_file,
            proposal_id,
            project,
            theme_root,
            self.root / "candidates",
        )
        self.assertEqual([80, 60], candidate["candidate"]["dimensions"])
        self.assertEqual(
            candidate["source"]["alphaSha256"],
            candidate["candidate"]["alphaSha256"],
        )

        applied = apply_candidate(
            Path(candidate["manifest"]),
            proposal_id,
            project,
            self.root / "transactions",
        )
        self.assertEqual("applied", applied["state"])
        self.assertTrue(all(applied["invariants"].values()))
        self.assertEqual(meta_hash, applied["post"]["metaSha256"])

        rolled_back = rollback_transaction(Path(applied["transaction"]))
        self.assertEqual("rolled_back", rolled_back["state"])
        self.assertEqual(source_hash, rolled_back["restored"]["imageSha256"])

    def test_project_brain_context_preserves_distinct_hierarchy_usage(self) -> None:
        project = self._project()
        context = self.root / "visual-context.json"
        context.write_text(
            json.dumps(
                {
                    "schema": "hydracore.project-brain.visual-context/v1",
                    "projectId": "test.project",
                    "indexFingerprint": "a" * 64,
                    "assets": [
                        {
                            "unityGuid": PROJECT_GUID,
                            "relativePath": "Assets/UI/old_primary_button.png",
                        }
                    ],
                    "usages": [
                        {
                            "unityGuid": PROJECT_GUID,
                            "fileId": "21300000",
                            "ownerPath": "Assets/UI/Panel.prefab",
                            "hierarchyPath": "Canvas/Top/Button",
                            "componentType": "Image",
                            "propertyName": "m_Sprite",
                            "referenceCount": 2,
                        },
                        {
                            "unityGuid": PROJECT_GUID,
                            "fileId": "21300000",
                            "ownerPath": "Assets/UI/Panel.prefab",
                            "hierarchyPath": "Canvas/Bottom/Button",
                            "componentType": "Image",
                            "propertyName": "m_Sprite",
                            "referenceCount": 1,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        result = ingest_project(
            self.store, project, "test.project", context
        )
        self.assertEqual("a" * 64, result["indexFingerprint"])
        self.assertEqual(3, result["references"])
        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT hierarchy_path, property_name, reference_count
                FROM project_usages ORDER BY hierarchy_path
                """
            ).fetchall()
        self.assertEqual(2, len(rows))
        self.assertEqual(3, sum(row[2] for row in rows))
        self.assertEqual({"m_Sprite"}, {row[1] for row in rows})

    def test_migrates_usage_schema_v1_without_data_loss(self) -> None:
        self.store.initialize()
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE schema_meta SET value='1' WHERE key='schema_version'"
            )
            connection.execute("ALTER TABLE project_usages RENAME TO project_usages_v2")
            connection.execute(
                """
                CREATE TABLE project_usages (
                    project_id TEXT NOT NULL,
                    index_fingerprint TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    unity_guid TEXT NOT NULL,
                    file_id TEXT,
                    owner_path TEXT NOT NULL,
                    hierarchy_path TEXT,
                    component_type TEXT,
                    evidence_kind TEXT NOT NULL,
                    reference_count INTEGER NOT NULL,
                    PRIMARY KEY(project_id, asset_id, owner_path, file_id)
                )
                """
            )
            connection.execute("DROP TABLE project_usages_v2")
        self.store.initialize()
        with self.store.connect() as connection:
            columns = {
                row[1] for row in connection.execute(
                    "PRAGMA table_info(project_usages)"
                )
            }
        self.assertIn("property_name", columns)
        self.assertEqual(2, self.store.integrity()["schemaVersion"])


if __name__ == "__main__":
    unittest.main()
