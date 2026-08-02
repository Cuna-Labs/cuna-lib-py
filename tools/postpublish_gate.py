"""Verify exact published artifacts and govern fail-closed recovery transitions."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256


def recovery_action(category: str, authorization: str | None) -> str:
    """Choose only an explicitly authorized recovery adapter."""
    if authorization in {"no-yank", "yank", "advisory"}:
        return authorization
    if category in {"digest-mismatch", "attestation-invalid", "retrieval-missing"}:
        return "blocked-owner-decision"
    return "no-yank"


def verify_published(expected: Path, retrieved: Path, repository: str) -> dict[str, object]:
    expected_files = {
        path.name: file_sha256(path)
        for path in expected.rglob("runa_sdk-*")
        if path.suffix == ".whl" or path.name.endswith(".tar.gz")
    }
    retrieved_files = {
        path.name: file_sha256(path)
        for path in retrieved.glob("runa_sdk-*")
        if path.suffix == ".whl" or path.name.endswith(".tar.gz")
    }
    if len(expected_files) != 2 or retrieved_files != expected_files:
        return {
            "category": "digest-mismatch",
            "recovery": recovery_action("digest-mismatch", None),
            "state": "uploaded-unverified",
            "verdict": "blocked",
        }
    gh = shutil.which("gh")
    if gh is None:
        return {
            "category": "attestation-verifier-missing",
            "recovery": "blocked-owner-decision",
            "state": "uploaded-unverified",
            "verdict": "blocked",
        }
    for path in sorted(retrieved.glob("runa_sdk-*")):
        completed = subprocess.run(  # noqa: S603 - fixed gh verification command
            [gh, "attestation", "verify", str(path), "--repo", repository],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            return {
                "category": "attestation-invalid",
                "recovery": recovery_action("attestation-invalid", None),
                "state": "uploaded-unverified",
                "verdict": "blocked",
            }
    return {
        "artifacts": [
            {"filename": name, "sha256": digest} for name, digest in sorted(retrieved_files.items())
        ],
        "state": "registry-verified",
        "transitions": ["uploaded-unverified", "registry-verified"],
        "verdict": "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--retrieved", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    result = verify_published(args.expected, args.retrieved, args.repository)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
