from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from revisual_rag.features import extract_image_features
from revisual_rag.identity import stable_asset_id
from revisual_rag.ingest import ingest_project, ingest_theme
from revisual_rag.retrieval import propose_mappings, search
from revisual_rag.store import VisualRagStore
from revisual_rag.unity_meta import parse_sprite_file_ids, parse_sprite_rects


GUID = "0123456789abcdef0123456789abcdef"
PROJECT_GUID = "fedcba9876543210fedcba9876543210"


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

    def test_visual_similarity_prefers_same_art(self) -> None:
        manifest = self._theme()
        ingest_theme(self.store, manifest)
        query_image = manifest.parent.parent / "Art" / "button.png"
        matches = search(self.store, image=query_image, source_kind="theme")
        self.assertGreater(matches[0]["scores"]["visual"], 0.99)

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


if __name__ == "__main__":
    unittest.main()
