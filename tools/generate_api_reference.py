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


PAIRS = {
    "Runa": "AsyncRuna",
    "Session": "AsyncSession",
    "SessionsManager": "AsyncSessionsManager",
    "RecordsManager": "AsyncRecordsManager",
    "AsyncRuna": "Runa",
    "AsyncSession": "Session",
    "AsyncSessionsManager": "SessionsManager",
    "AsyncRecordsManager": "RecordsManager",
}


def _summary(obj: object) -> str | None:
    docstring = getattr(obj, "docstring", None)
    value = getattr(docstring, "value", None)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().splitlines()[0]


def _signature(obj: object) -> str | None:
    signature = getattr(obj, "signature", None)
    if not callable(signature):
        return None
    try:
        return str(signature())
    except (AttributeError, TypeError, ValueError):
        return None


def _page(name: str, import_path: str, obj: object) -> tuple[str, list[str]]:
    target = getattr(obj, "final_target", obj)
    summary = _summary(target)
    missing: list[str] = []
    if summary is None:
        missing.append(f"{name}:summary")
        summary = "Documentation summary is missing from the candidate wheel."
    lines = [f"# `{name}`", "", summary, "", "## Import", "", f"`{import_path}`", ""]
    signature = _signature(target)
    if signature is not None:
        lines.extend(["## Signature", "", f"`{name}{signature}`", ""])
    members = getattr(target, "members", {})
    public = [
        (member_name, member)
        for member_name, member in members.items()
        if not member_name.startswith("_")
    ]
    if public:
        lines.extend(
            [
                "## Public members and fields",
                "",
                "| Name | Kind | Signature or annotation | Summary |",
                "| --- | --- | --- | --- |",
            ]
        )
        for member_name, member in public:
            member_target = getattr(member, "final_target", member)
            member_summary = _summary(member_target)
            if member_summary is None:
                missing.append(f"{name}.{member_name}:summary")
                member_summary = "Missing from candidate docstring."
            detail = _signature(member_target)
            if detail is None:
                annotation = getattr(member_target, "annotation", None)
                detail = str(annotation) if annotation is not None else "value"
            kind = str(getattr(member_target, "kind", type(member_target).__name__))
            lines.append(f"| `{member_name}` | {kind} | `{detail}` | {member_summary} |")
        lines.append("")
    if name in PAIRS:
        pair = PAIRS[name]
        lines.extend(
            ["## Sync/async pair", "", f"See [`{pair}`](../{_section(pair)}/{pair}.md).", ""]
        )
    lines.extend(
        [
            "## Raises and examples",
            "",
            "Raises information and safe examples must come from candidate-wheel docstrings.",
            "",
        ]
    )
    if public and any(
        _summary(getattr(member, "final_target", member)) is None for _, member in public
    ):
        missing.append(f"{name}:raises-or-examples")
    return "\n".join(lines), missing


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
        module = griffe.load("runa", search_paths=[room], extensions=EXTENSIONS)
        errors_module = griffe.load("runa.errors", search_paths=[room], extensions=EXTENSIONS)
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
    missing_documentation: list[str] = []
    for section, symbols in sections.items():
        directory = args.output / section
        directory.mkdir(parents=True, exist_ok=True)
        section_lines = [f"# {section.title()}", ""]
        index_lines.append(f"- [{section.title()}]({section}/README.md)")
        for name, import_path in symbols:
            filename = f"{name}.md"
            source = errors_module.members[name] if section == "errors" else module.members[name]
            page, missing = _page(name, import_path, source)
            (directory / filename).write_text(page, encoding="utf-8", newline="\n")
            missing_documentation.extend(missing)
            section_lines.append(f"- [`{name}`]({filename})")
            page_count += 1
        (directory / "README.md").write_text(
            "\n".join(section_lines) + "\n", encoding="utf-8", newline="\n"
        )
    (args.output / "README.md").write_text(
        "\n".join(index_lines) + "\n", encoding="utf-8", newline="\n"
    )
    passed = not missing_documentation
    print(
        json.dumps(
            {
                "missingDocumentation": sorted(set(missing_documentation)),
                "pages": page_count,
                "requirement": "R-091-03",
                "verdict": "pass" if passed else "blocked",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
