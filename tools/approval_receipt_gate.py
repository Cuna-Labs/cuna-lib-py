"""Verify an independently retrieved approval receipt for an exact release core."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from _approval import verify_provider_receipt
    from _evidence_utils import file_sha256
    from build_external_release_evidence import python_release_core_binding
except ModuleNotFoundError:
    from tools._approval import verify_provider_receipt
    from tools._evidence_utils import file_sha256
    from tools.build_external_release_evidence import python_release_core_binding


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--trust", type=Path, default=Path(".runa/approval-trust.json"))
    args = parser.parse_args()
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in args.root.rglob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    try:
        binding = python_release_core_binding(args.root)
        result = verify_provider_receipt(
            args.receipt,
            args.signature,
            args.trust,
            core_digest=binding["coreDigest"],
            artifacts=artifacts,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"category": str(error), "verdict": "blocked"}, sort_keys=True))
        return 1
    print(json.dumps({**result, "verdict": "pass"}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
