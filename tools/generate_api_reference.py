"""Generate deterministic API-reference pages from a clean candidate wheel."""

from __future__ import annotations

import argparse
import ast
import json
import tempfile
import zipfile
from importlib.metadata import version
from pathlib import Path

import griffe

ERROR_MANIFEST = ("ApiError", "CommandError", "ConfigError", "RunaError")
ROOT_MANIFEST = (
    "Acknowledgement",
    "AssignedWorkspace",
    "AsyncRecordsManager",
    "AsyncRuna",
    "AsyncSession",
    "AsyncSessionsManager",
    "EstimatedUsage",
    "ExecOptions",
    "ExecResult",
    "Me",
    "OpenSessionResult",
    "Record",
    "RecordsManager",
    "Runa",
    "Session",
    "SessionAgent",
    "SessionCreateOptions",
    "SessionSnapshot",
    "SessionsManager",
    "SessionStatus",
    "UNSET",
    "UnassignedWorkspace",
    "UnsetType",
)
EXTENSIONS: list[str] = []


def _all(tree: ast.Module) -> tuple[str, ...]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
    return ()


def _section(name: str) -> str:
    if name.startswith("Async"):
        return "async"
    if name in {"Runa", "Session", "SessionsManager", "RecordsManager"}:
        return "sync"
    return "shared"


def _page(name: str, import_path: str) -> str:
    return (
        f"# `{name}`\n\n"
        f"Stable public API symbol. Import with `{import_path}`.\n\n"
        "Signatures, annotations, members, and fields are governed by the candidate-wheel "
        "public-surface snapshot and inline package documentation.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/api"))
    args = parser.parse_args()
    if version("griffe") != "2.1.0" or EXTENSIONS:
        raise SystemExit("R-091-19: documentation tool configuration mismatch")
    with tempfile.TemporaryDirectory() as room_name:
        room = Path(room_name)
        with zipfile.ZipFile(args.wheel) as archive:
            archive.extractall(room)
        root_names = _all(ast.parse((room / "runa" / "__init__.py").read_text(encoding="utf-8")))
        error_names = _all(ast.parse((room / "runa" / "errors.py").read_text(encoding="utf-8")))
        if root_names != ROOT_MANIFEST:
            raise SystemExit("R-091-01: candidate root manifest mismatch")
        if error_names != ERROR_MANIFEST or set(error_names) & set(root_names):
            raise SystemExit("R-091-18: accepted errors submodule manifest mismatch")
        griffe.load("runa", search_paths=[room], extensions=EXTENSIONS)
    sections: dict[str, list[tuple[str, str]]] = {
        "sync": [],
        "async": [],
        "shared": [],
        "errors": [],
    }
    for name in root_names:
        sections[_section(name)].append((name, f"from runa import {name}"))
    for name in error_names:
        sections["errors"].append((name, f"from runa.errors import {name}"))
    args.output.mkdir(parents=True, exist_ok=True)
    index_lines = ["# Python API reference", ""]
    page_count = 0
    for section, symbols in sections.items():
        directory = args.output / section
        directory.mkdir(parents=True, exist_ok=True)
        section_lines = [f"# {section.title()}", ""]
        index_lines.append(f"- [{section.title()}]({section}/README.md)")
        for name, import_path in symbols:
            filename = f"{name}.md"
            (directory / filename).write_text(
                _page(name, import_path), encoding="utf-8", newline="\n"
            )
            section_lines.append(f"- [`{name}`]({filename})")
            page_count += 1
        (directory / "README.md").write_text(
            "\n".join(section_lines) + "\n", encoding="utf-8", newline="\n"
        )
    (args.output / "README.md").write_text(
        "\n".join(index_lines) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {"pages": page_count, "requirement": "R-091-18", "verdict": "pass"},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
