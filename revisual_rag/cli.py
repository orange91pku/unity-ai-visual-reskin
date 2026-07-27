from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ingest import ingest_project, ingest_theme
from .retrieval import propose_mappings, search
from .store import VisualRagStore


def _emit(value: object, output: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="revisual-rag")
    parser.add_argument("--db", type=Path, default=Path(".revisual/visual-rag.sqlite3"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")

    theme = commands.add_parser("ingest-theme")
    theme.add_argument("--manifest", type=Path, required=True)

    project = commands.add_parser("ingest-project")
    project.add_argument("--project-root", type=Path, required=True)
    project.add_argument("--project-id", required=True)
    project.add_argument("--context", type=Path)

    query = commands.add_parser("search")
    query.add_argument("--text")
    query.add_argument("--image", type=Path)
    query.add_argument("--role")
    query.add_argument("--source-kind", choices=["theme", "project"])
    query.add_argument("--source-id")
    query.add_argument("--limit", type=int, default=10)

    mapping = commands.add_parser("propose")
    mapping.add_argument("--project-id", required=True)
    mapping.add_argument("--theme-id", required=True)
    mapping.add_argument("--role-prefix")
    mapping.add_argument("--limit", type=int, default=100)
    mapping.add_argument("--output", type=Path)

    commands.add_parser("stats")
    commands.add_parser("validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    store = VisualRagStore(arguments.db.resolve())
    try:
        if arguments.command == "init":
            store.initialize()
            result = {"ok": True, "database": str(store.path), **store.integrity()}
        elif arguments.command == "ingest-theme":
            result = ingest_theme(store, arguments.manifest)
        elif arguments.command == "ingest-project":
            result = ingest_project(
                store, arguments.project_root, arguments.project_id, arguments.context
            )
        elif arguments.command == "search":
            result = search(
                store,
                text=arguments.text,
                image=arguments.image,
                semantic_role=arguments.role,
                source_kind=arguments.source_kind,
                source_id=arguments.source_id,
                limit=arguments.limit,
            )
        elif arguments.command == "propose":
            result = propose_mappings(
                store,
                arguments.project_id,
                arguments.theme_id,
                arguments.role_prefix,
                arguments.limit,
            )
            _emit(result, arguments.output)
            return 0
        elif arguments.command == "stats":
            result = store.stats()
        else:
            result = store.integrity()
        _emit(result)
        return 0
    except Exception as error:
        _emit({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
