from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


GUID_RE = re.compile(r"^guid:\s*([0-9a-fA-F]{32})\s*$", re.MULTILINE)
REFERENCE_RE = re.compile(
    r"\{fileID:\s*(-?\d+),\s*guid:\s*([0-9a-fA-F]{32}),\s*type:\s*\d+\}"
)


@dataclass(frozen=True)
class SpriteRect:
    name: str
    x: int
    y: int
    width: int
    height: int


def read_guid(meta_path: Path) -> str | None:
    if not meta_path.exists():
        return None
    match = GUID_RE.search(meta_path.read_text(encoding="utf-8", errors="ignore"))
    return match.group(1).lower() if match else None


def parse_sprite_rects(meta_path: Path) -> dict[str, SpriteRect]:
    if not meta_path.exists():
        return {}
    lines = meta_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    result: dict[str, SpriteRect] = {}
    current_name: str | None = None
    values: dict[str, int] = {}
    in_rect = False

    def flush() -> None:
        nonlocal current_name, values, in_rect
        if current_name and all(key in values for key in ("x", "y", "width", "height")):
            result[current_name] = SpriteRect(current_name, **values)
        current_name = None
        values = {}
        in_rect = False

    for line in lines:
        if line.startswith("    - serializedVersion:"):
            flush()
            continue
        name_match = re.match(r"^\s{6}name:\s*(.+?)\s*$", line)
        if name_match:
            current_name = name_match.group(1)
            continue
        if current_name and re.match(r"^\s{6}rect:\s*$", line):
            in_rect = True
            continue
        if in_rect:
            value_match = re.match(r"^\s{8}(x|y|width|height):\s*(-?\d+)\s*$", line)
            if value_match:
                values[value_match.group(1)] = int(value_match.group(2))
            elif line and not line.startswith("        "):
                in_rect = False
    flush()
    return result


def parse_sprite_file_ids(meta_path: Path) -> dict[str, str]:
    if not meta_path.exists():
        return {}
    lines = meta_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    result: dict[str, str] = {}
    pending_file_id: str | None = None
    for line in lines:
        file_id_match = re.match(r"^\s{6}213:\s*(-?\d+)\s*$", line)
        if file_id_match:
            pending_file_id = file_id_match.group(1)
            continue
        name_match = re.match(r"^\s{4}second:\s*(.+?)\s*$", line)
        if pending_file_id and name_match:
            result[name_match.group(1)] = pending_file_id
            pending_file_id = None
    return result


def find_serialized_references(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [(match.group(2).lower(), match.group(1)) for match in REFERENCE_RE.finditer(text)]
