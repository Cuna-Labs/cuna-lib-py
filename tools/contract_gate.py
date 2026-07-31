"""Validate local contract artifacts and fail on unapproved provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> int:
    root = Path("contracts")
    required = (
        "runa-sdk-contract.snapshot.schema.json",
        "runa-sdk-contract.snapshot.json",
        "runa-sdk-contract.prd002-projection.json",
        "runa-sdk-contract.prd002-expected-manifest.json",
        "runa-sdk-contract.provenance.json",
    )
    if any(not (root / name).is_file() for name in required):
        print('{"requirement":"R-056-20","verdict":"blocked","category":"artifact-missing"}')
        return 1
    snapshot = (root / required[1]).read_bytes()
    projection = (root / required[2]).read_bytes()
    provenance = json.loads((root / required[4]).read_text(encoding="utf-8"))
    if snapshot != projection:
        print('{"requirement":"R-056-20","verdict":"blocked","category":"projection-drift"}')
        return 1
    if provenance.get("snapshot_sha256") != hashlib.sha256(snapshot).hexdigest():
        print('{"requirement":"R-056-20","verdict":"blocked","category":"digest-mismatch"}')
        return 1
    if provenance.get("status") != "approved" or provenance.get("approval_reference") is None:
        print('{"requirement":"R-056-20","verdict":"blocked","category":"approval-missing"}')
        return 1
    print('{"requirement":"R-056-20","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
