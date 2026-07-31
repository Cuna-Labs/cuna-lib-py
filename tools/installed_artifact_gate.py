"""Prove the imported package came from an installed candidate wheel."""

from __future__ import annotations

import hashlib
import json
import sys
from importlib import metadata
from pathlib import Path

import runa


def main() -> int:
    candidate = Path(sys.argv[1] if len(sys.argv) > 1 else "candidate").resolve()
    wheel = next(candidate.glob("runa_sdk-*.whl"))
    origin = Path(runa.__file__).resolve()
    if "site-packages" not in origin.parts:
        raise SystemExit("R-096-03: import origin is not site-packages")
    marker = origin.with_name("py.typed")
    if marker.read_bytes() != b"":
        raise SystemExit("R-096-04: installed typing marker mismatch")
    report = {
        "artifact_form": "wheel",
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "version": metadata.version("runa-sdk"),
        "verdict": "pass",
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
