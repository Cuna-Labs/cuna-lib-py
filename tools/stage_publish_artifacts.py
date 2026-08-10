"""Stage only the verified wheel and sdist into a flat publish directory."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256


def stage_publish_artifacts(handoff: Path, output: Path) -> list[dict[str, str]]:
    candidates = sorted(
        path
        for path in handoff.rglob("cuna_sdk-*")
        if path.suffix == ".whl" or path.name.endswith(".tar.gz")
    )
    if len(candidates) != 2 or sum(path.suffix == ".whl" for path in candidates) != 1:
        raise ValueError("exact-artifact-pair-required")
    if output.exists() and any(output.iterdir()):
        raise ValueError("publish-directory-not-empty")
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    for source in candidates:
        target = output / source.name
        shutil.copyfile(source, target)
        if file_sha256(target) != file_sha256(source):
            raise ValueError("publish-artifact-copy-mismatch")
        records.append({"filename": target.name, "sha256": file_sha256(target)})
    if sorted(path.name for path in output.iterdir()) != sorted(
        item["filename"] for item in records
    ):
        raise ValueError("publish-directory-contaminated")
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        artifacts = stage_publish_artifacts(args.handoff, args.output)
    except (OSError, ValueError):
        print('{"category":"publish-layout-invalid","verdict":"blocked"}')
        return 1
    print(
        json.dumps(
            {"artifacts": artifacts, "verdict": "pass"},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
