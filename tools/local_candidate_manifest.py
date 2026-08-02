"""Emit local-only candidate identity without claiming external admission."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

try:
    from _evidence_utils import file_sha256
    from release_readiness import source_digest
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256
    from tools.release_readiness import source_digest


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def build_manifest(artifacts: Path) -> dict[str, object]:
    candidates = sorted(
        path
        for path in artifacts.glob("runa_sdk-*")
        if path.suffix == ".whl" or path.name.endswith(".tar.gz")
    )
    if len(candidates) != 2:
        raise ValueError("exact-artifact-pair-required")
    dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
    return {
        "artifacts": [
            {"filename": path.name, "sha256": file_sha256(path)} for path in candidates
        ],
        "baseCommit": _git("rev-parse", "HEAD"),
        "evidenceClass": "local-only-unattested",
        "limitations": [
            "not-an-external-approval",
            "not-a-signature-or-provenance-statement",
            "not-a-release-admission",
        ],
        "schemaVersion": 1,
        "sourceDigest": source_digest(),
        "sourceState": "working-tree" if dirty else "commit",
        "uvLockSha256": file_sha256(Path("uv.lock")),
        "verdict": "local-pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=Path("dist"))
    parser.add_argument(
        "--output", type=Path, default=Path("dist/local-candidate-manifest.json")
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build_manifest(args.artifacts)
    except (OSError, ValueError, subprocess.SubprocessError):
        print('{"category":"local-candidate-identity-invalid","verdict":"blocked"}')
        return 1
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            print('{"category":"local-candidate-manifest-stale","verdict":"blocked"}')
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "evidenceClass": manifest["evidenceClass"],
                "sourceState": manifest["sourceState"],
                "verdict": manifest["verdict"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
