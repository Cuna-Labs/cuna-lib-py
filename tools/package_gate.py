"""Validate the clean candidate artifact pair without installing the checkout."""

from __future__ import annotations

import json
import sys
import tarfile
import zipfile
from pathlib import Path

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256


def public_surface_matches(wheel: Path, surface_path: Path) -> bool:
    receipt_path = wheel.parent / ".public-surface-receipt.json"
    if not surface_path.is_file() or not receipt_path.is_file():
        return False
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (
        set(receipt) == {"artifactSha256", "schemaVersion", "surfaceSha256"}
        and receipt["schemaVersion"] == 1
        and receipt["artifactSha256"] == file_sha256(wheel)
        and receipt["surfaceSha256"] == file_sha256(surface_path)
    )


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    wheels = sorted(root.glob("cuna_sdk-*.whl"))
    sdists = sorted(root.glob("cuna_sdk-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("R-093-01: candidate must contain exactly one wheel and one sdist")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        if not any(name == "cuna/py.typed" for name in names):
            raise SystemExit("R-093-04: wheel typing marker is missing")
        if any(name.startswith(("tests/", "docs/", "examples/", "tools/")) for name in names):
            raise SystemExit("R-093-03: wheel contains a non-package path")
    with tarfile.open(sdists[0], "r:gz") as archive:
        names = archive.getnames()
        if not any(name.endswith("/pyproject.toml") for name in names):
            raise SystemExit("R-093-02: sdist build definition is missing")
    surface_path = Path(".cuna/public-surface.json")
    if not public_surface_matches(wheels[0], surface_path):
        raise SystemExit("R-058-14: public-surface evidence is stale")
    report = {
        "artifacts": [
            {"form": "wheel", "sha256": file_sha256(wheels[0])},
            {"form": "sdist", "sha256": file_sha256(sdists[0])},
        ],
        "verdict": "pass",
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
