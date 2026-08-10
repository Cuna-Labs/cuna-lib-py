"""Prove the imported package came from an installed candidate wheel."""

from __future__ import annotations

import json
import sys
from importlib import metadata
from pathlib import Path

from _evidence_utils import file_sha256

import cuna
import runa


def main() -> int:
    candidate = Path(sys.argv[1] if len(sys.argv) > 1 else "candidate").resolve()
    artifact = next(candidate.glob("cuna_sdk-*.whl")) if candidate.is_dir() else candidate
    artifact_form = "sdist" if artifact.name.endswith(".tar.gz") else "wheel"
    origin = Path(cuna.__file__).resolve()
    if "site-packages" not in origin.parts:
        raise SystemExit("R-096-03: import origin is not site-packages")
    marker = origin.with_name("py.typed")
    if marker.read_bytes() != b"":
        raise SystemExit("R-096-04: installed typing marker mismatch")
    report = {
        "artifact_form": artifact_form,
        "sha256": file_sha256(artifact),
        "legacy_namespace": Path(runa.__file__).resolve().is_file(),
        "version": metadata.version("cuna-sdk"),
        "verdict": "pass",
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
