"""Stage and verify the exact Python GitHub Release supply-chain asset set."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path, PurePosixPath

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256


def _one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError("github-release-core-asset-set-invalid")
    return matches[0]


def expected_assets(root: Path) -> list[dict[str, str]]:
    statement_path = _one(root, "inherited-evidence.json")
    statement = json.loads(statement_path.read_text(encoding="utf-8"))
    evidence = statement.get("evidence") if isinstance(statement, dict) else None
    selected = [
        _one(root, "release-core-manifest.json"),
        _one(root, "release-admission-manifest.json"),
    ]
    for key in ("sbom", "provenance"):
        record = evidence.get(key) if isinstance(evidence, dict) else None
        files = record.get("files") if isinstance(record, dict) else None
        if not isinstance(files, list) or len(files) != 2:
            raise ValueError("github-release-supply-chain-asset-set-invalid")
        for item in files:
            relative = PurePosixPath(str(item.get("path", ""))) if isinstance(item, dict) else None
            if (
                relative is None
                or relative.is_absolute()
                or ".." in relative.parts
                or len(relative.parts) != 1
            ):
                raise ValueError("github-release-supply-chain-asset-path-invalid")
            path = _one(root, relative.name)
            if item.get("sha256") != file_sha256(path):
                raise ValueError("github-release-supply-chain-asset-digest-mismatch")
            selected.append(path)
    if len({path.name for path in selected}) != 6:
        raise ValueError("github-release-asset-name-collision")
    return sorted(
        ({"filename": path.name, "sha256": file_sha256(path)} for path in selected),
        key=lambda item: item["filename"],
    )


def stage(root: Path, output: Path) -> list[dict[str, str]]:
    if output.exists() and any(output.iterdir()):
        raise ValueError("github-release-stage-not-empty")
    output.mkdir(parents=True, exist_ok=True)
    records = expected_assets(root)
    for record in records:
        source = _one(root, record["filename"])
        shutil.copyfile(source, output / record["filename"])
    return records


def verify(expected: Path, retrieved: Path) -> list[dict[str, str]]:
    expected_records = sorted(
        ({"filename": path.name, "sha256": file_sha256(path)} for path in expected.iterdir()),
        key=lambda item: item["filename"],
    )
    retrieved_records = sorted(
        ({"filename": path.name, "sha256": file_sha256(path)} for path in retrieved.iterdir()),
        key=lambda item: item["filename"],
    )
    if len(expected_records) != 6 or retrieved_records != expected_records:
        raise ValueError("github-release-retrieval-mismatch")
    return expected_records


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    stage_parser = subparsers.add_parser("stage")
    stage_parser.add_argument("root", type=Path)
    stage_parser.add_argument("output", type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("expected", type=Path)
    verify_parser.add_argument("retrieved", type=Path)
    args = parser.parse_args()
    try:
        records = (
            stage(args.root, args.output)
            if args.command == "stage"
            else verify(args.expected, args.retrieved)
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"category": str(error), "verdict": "blocked"}, sort_keys=True))
        return 1
    result: dict[str, object] = {"assets": records, "verdict": "pass"}
    if args.command == "verify":
        result["state"] = "promoted"
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
