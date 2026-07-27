from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 1


DDL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_version TEXT,
    index_fingerprint TEXT NOT NULL,
    asset_count INTEGER NOT NULL,
    created_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL CHECK(source_kind IN ('theme','project')),
    source_id TEXT NOT NULL,
    source_version TEXT,
    semantic_role TEXT,
    tags_json TEXT NOT NULL,
    unity_guid TEXT,
    sprite_name TEXT,
    relative_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    aspect_ratio REAL NOT NULL,
    alpha_coverage REAL NOT NULL,
    opaque_bounds_ratio REAL NOT NULL,
    brightness REAL NOT NULL,
    saturation REAL NOT NULL,
    edge_density REAL NOT NULL,
    palette_json TEXT NOT NULL,
    perceptual_hash TEXT NOT NULL,
    visual_provider TEXT NOT NULL,
    visual_vector_json TEXT NOT NULL,
    semantic_provider TEXT NOT NULL,
    semantic_vector_json TEXT NOT NULL,
    license_id TEXT,
    provenance TEXT,
    reference_count INTEGER NOT NULL DEFAULT 0,
    extra_json TEXT NOT NULL,
    updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_assets_source ON assets(source_kind, source_id);
CREATE INDEX IF NOT EXISTS ix_assets_role ON assets(semantic_role);
CREATE INDEX IF NOT EXISTS ix_assets_guid ON assets(unity_guid);
CREATE TABLE IF NOT EXISTS project_usages (
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
    PRIMARY KEY(project_id, asset_id, owner_path, file_id),
    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_usages_project ON project_usages(project_id);
CREATE TABLE IF NOT EXISTS mapping_proposals (
    proposal_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    theme_id TEXT NOT NULL,
    source_asset_id TEXT NOT NULL,
    destination_asset_id TEXT NOT NULL,
    score REAL NOT NULL,
    score_json TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    created_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_evidence (
    evidence_id TEXT PRIMARY KEY,
    asset_id TEXT,
    proposal_id TEXT,
    reviewer_kind TEXT NOT NULL,
    metric TEXT NOT NULL,
    score REAL,
    verdict TEXT,
    details_json TEXT NOT NULL,
    created_utc TEXT NOT NULL
);
"""


class VisualRagStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(DDL)
            connection.execute(
                "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def replace_source(self, source_kind: str, source_id: str, assets: list[dict]) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM assets WHERE source_kind = ? AND source_id = ?",
                (source_kind, source_id),
            )
            columns = [
                "asset_id", "source_kind", "source_id", "source_version", "semantic_role",
                "tags_json", "unity_guid", "sprite_name", "relative_path", "content_hash",
                "width", "height", "aspect_ratio", "alpha_coverage", "opaque_bounds_ratio",
                "brightness", "saturation", "edge_density", "palette_json", "perceptual_hash",
                "visual_provider", "visual_vector_json", "semantic_provider",
                "semantic_vector_json", "license_id", "provenance", "reference_count",
                "extra_json", "updated_utc",
            ]
            placeholders = ",".join("?" for _ in columns)
            statement = f"INSERT INTO assets({','.join(columns)}) VALUES({placeholders})"
            connection.executemany(statement, [[asset[column] for column in columns] for asset in assets])

    def rows(self, where: str = "", parameters: tuple = ()) -> list[dict]:
        self.initialize()
        query = "SELECT * FROM assets"
        if where:
            query += " WHERE " + where
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, parameters)]

    def stats(self) -> dict:
        self.initialize()
        with self.connect() as connection:
            assets = connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
            themes = connection.execute(
                "SELECT COUNT(DISTINCT source_id) FROM assets WHERE source_kind='theme'"
            ).fetchone()[0]
            projects = connection.execute(
                "SELECT COUNT(DISTINCT source_id) FROM assets WHERE source_kind='project'"
            ).fetchone()[0]
            usages = connection.execute("SELECT COUNT(*) FROM project_usages").fetchone()[0]
            proposals = connection.execute("SELECT COUNT(*) FROM mapping_proposals").fetchone()[0]
        return {
            "schemaVersion": SCHEMA_VERSION,
            "assets": assets,
            "themes": themes,
            "projects": projects,
            "usages": usages,
            "mappingProposals": proposals,
        }

    def integrity(self) -> dict:
        self.initialize()
        with self.connect() as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            schema = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
        return {"ok": result == "ok" and schema is not None, "sqlite": result, "schemaVersion": int(schema[0])}


def vector_from_row(row: dict, name: str) -> list[float]:
    return [float(value) for value in json.loads(row[name])]
