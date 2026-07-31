"""Stage local contract-shaped evidence while keeping provenance fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("projection", type=Path)
    parser.add_argument("output", type=Path, default=Path("contracts"), nargs="?")
    args = parser.parse_args()
    projection = json.loads(args.projection.read_text(encoding="utf-8"))
    encoded = canonical(projection)
    digest = hashlib.sha256(encoded).hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "runa-sdk-contract.snapshot.json").write_bytes(encoded)
    (args.output / "runa-sdk-contract.prd002-projection.json").write_bytes(encoded)
    manifest = {
        "operations": sorted(projection["operations"]),
        "schemas": sorted(projection["schemas"]),
        "source": "local-infra-projection",
    }
    (args.output / "runa-sdk-contract.prd002-expected-manifest.json").write_bytes(
        canonical(manifest)
    )
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}
    (args.output / "runa-sdk-contract.snapshot.schema.json").write_bytes(canonical(schema))
    provenance = {
        "approval_reference": None,
        "canonical_repository": "Runa-Laboratories/runa-sdk-contract",
        "snapshot_sha256": digest,
        "source": args.projection.as_posix(),
        "status": "blocked",
    }
    (args.output / "runa-sdk-contract.provenance.json").write_bytes(canonical(provenance))
    print(json.dumps({"snapshot_sha256": digest, "verdict": "blocked"}, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
