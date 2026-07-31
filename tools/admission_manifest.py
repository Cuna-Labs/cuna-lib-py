"""Emit a deterministic, artifact-bound Python quality admission manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--require-success", nargs="+", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source) is None:
        raise SystemExit("R-094-18: immutable source digest is invalid")
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": digest(path)}
            for path in args.artifacts.glob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    if len(artifacts) != 2:
        raise SystemExit("R-094-04: exact artifact pair is missing")
    expected = {
        (python, form)
        for python in ("3.10", "3.11", "3.12", "3.13", "3.14")
        for form in ("wheel", "sdist")
    }
    receipts: list[dict[str, object]] = []
    observed: set[tuple[str, str]] = set()
    artifact_digests = {item["sha256"] for item in artifacts}
    for path in sorted(args.receipts.glob("receipt-*.json")):
        match = re.fullmatch(r"receipt-(3\.\d+)-(wheel|sdist)\.json", path.name)
        if match is None:
            raise SystemExit("R-094-14: receipt identity is invalid")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        cell = (match.group(1), match.group(2))
        if (
            receipt.get("artifact_form") != cell[1]
            or receipt.get("sha256") not in artifact_digests
            or receipt.get("verdict") != "pass"
        ):
            raise SystemExit("R-094-18: receipt binding mismatch")
        observed.add(cell)
        receipts.append({"artifact": cell[1], "python": cell[0], **receipt})
    upstream = all(result == "success" for result in args.require_success)
    passed = upstream and observed == expected
    manifest = {
        "artifacts": artifacts,
        "cells": sorted(receipts, key=lambda item: (item["python"], item["artifact"])),
        "source": args.source,
        "verdict": "pass" if passed else "blocked",
    }
    print(json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
