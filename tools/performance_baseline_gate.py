"""Verify the externally accepted and signed 20-cell performance baseline set."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from _evidence_utils import file_sha256
    from inherited_evidence_gate import verify_sigstore
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256
    from tools.inherited_evidence_gate import verify_sigstore


def validate_baselines(root: Path) -> str | None:
    index_path = root / "baseline-index.json"
    bundle = root / "baseline-index.sigstore.json"
    if not index_path.is_file() or not bundle.is_file():
        return "signed-baseline-index-missing"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "baseline-index-invalid"
    source = index.get("source")
    if not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{40}", source) is None:
        return "baseline-source-invalid"
    if not verify_sigstore(
        index_path, bundle, source, workflow_name="performance-baseline.yml"
    ):
        return "baseline-signature-invalid"
    entries = index.get("baselines")
    if not isinstance(entries, list) or len(entries) != 20:
        return "baseline-matrix-incomplete"
    expected = {
        f"baseline-{python}-{form}-{mode}.json"
        for python in ("3.10", "3.11", "3.12", "3.13", "3.14")
        for form in ("wheel", "sdist")
        for mode in ("sync", "async")
    }
    observed: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            return "baseline-index-invalid"
        name = entry["path"]
        if name not in expected:
            return "baseline-cell-invalid"
        path = root / name
        if not path.is_file() or entry.get("sha256") != file_sha256(path):
            return "baseline-digest-mismatch"
        baseline = json.loads(path.read_text(encoding="utf-8"))
        if (
            baseline.get("status") != "accepted"
            or not baseline.get("approvalReference")
            or not isinstance(baseline.get("metrics"), dict)
        ):
            return "baseline-not-accepted"
        observed.add(name)
    return None if observed == expected else "baseline-matrix-incomplete"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    category = validate_baselines(args.root)
    if category is not None:
        print(json.dumps({"category": category, "verdict": "blocked"}, sort_keys=True))
        return 1
    print('{"requirement":"R-017-21","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
