"""Artifact-only Griffe reference precondition and deterministic generator."""

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
EXTENSIONS: list[str] = []


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
        init_path = room / "runa" / "__init__.py"
        tree = ast.parse(init_path.read_text(encoding="utf-8"))
        root_names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            ):
                root_names = set(ast.literal_eval(node.value))
        griffe.load("runa", search_paths=[room], extensions=EXTENSIONS)
    missing = sorted(set(ERROR_MANIFEST) - root_names)
    if missing:
        print(
            json.dumps(
                {
                    "category": "errors-root-manifest-precondition",
                    "requirement": "R-091-18",
                    "symbols": missing,
                    "verdict": "blocked",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    raise SystemExit("R-091-02: renderer requires an accepted root-error manifest amendment")


if __name__ == "__main__":
    raise SystemExit(main())
