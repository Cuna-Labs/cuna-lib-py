"""Bind protected external control evidence to one source, tag, policy, and artifact pair."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from _evidence_utils import canonical_json_sha256, file_sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--control-env", default="RUNA_RELEASE_CONTROL_EVIDENCE")
    args = parser.parse_args()
    source = os.environ.get("GITHUB_SHA", "")
    if re.fullmatch(r"[0-9a-f]{40}", source) is None:
        raise SystemExit("R-095-01: immutable source identity is missing")
    raw_control = os.environ.get(args.control_env)
    if raw_control is None:
        raise SystemExit("R-095-08: protected release-control evidence is missing")
    control = json.loads(raw_control)
    if not isinstance(control, dict):
        raise SystemExit("R-095-08: release-control evidence must be an object")
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in args.artifacts.glob("cuna_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    if len(artifacts) != 2:
        raise SystemExit("R-095-03: exact artifact pair is missing")
    evidence = {
        **control,
        "artifacts": artifacts,
        "policySha256": canonical_json_sha256(policy),
        "sourceCommit": source,
        "tag": args.tag,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
