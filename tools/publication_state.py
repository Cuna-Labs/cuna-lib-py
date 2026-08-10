"""Maintain an append-only, core-bound publication transition record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from _evidence_utils import canonical_json_sha256, file_sha256
    from build_external_release_evidence import python_release_core_binding
except ModuleNotFoundError:
    from tools._evidence_utils import canonical_json_sha256, file_sha256
    from tools.build_external_release_evidence import python_release_core_binding


TRANSITIONS = {
    "planned": "uploaded-unverified",
    "uploaded-unverified": "registry-verified",
    "registry-verified": "release-assets-verified",
    "release-assets-verified": "promoted",
}
STATE_SEQUENCE = ["planned", *TRANSITIONS.values()]


def _binding_digest(document: dict[str, object]) -> str:
    return canonical_json_sha256(
        {key: value for key, value in document.items() if key not in {"events", "state"}}
    )


def initialize(root: Path) -> dict[str, object]:
    admissions = list(root.rglob("release-admission-manifest.json"))
    if len(admissions) != 1:
        raise ValueError("publication-admission-envelope-missing")
    admission = json.loads(admissions[0].read_text(encoding="utf-8"))
    core = python_release_core_binding(root)
    if (
        admission.get("state") != "admitted"
        or admission.get("coreDigest") != core["coreDigest"]
        or admission.get("core") != {"path": core["path"], "sha256": core["sha256"]}
        or not isinstance(admission.get("approvalReceipt"), dict)
    ):
        raise ValueError("publication-admission-envelope-invalid")
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in root.rglob("cuna_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    if len(artifacts) != 2:
        raise ValueError("publication-artifact-pair-invalid")
    document: dict[str, object] = {
        "approvalReceipt": admission["approvalReceipt"],
        "artifacts": artifacts,
        "core": {"path": core["path"], "sha256": core["sha256"]},
        "coreDigest": core["coreDigest"],
        "schemaVersion": 1,
        "state": "planned",
    }
    document["events"] = [{"bindingDigest": _binding_digest(document), "state": "planned"}]
    return document


def transition(document: dict[str, object], target: str) -> dict[str, object]:
    current = document.get("state")
    events = document.get("events")
    binding_digest = _binding_digest(document)
    observed_states = (
        [item.get("state") for item in events if isinstance(item, dict)]
        if isinstance(events, list)
        else []
    )
    if (
        document.get("schemaVersion") != 1
        or not isinstance(current, str)
        or TRANSITIONS.get(current) != target
        or not isinstance(events, list)
        or observed_states != STATE_SEQUENCE[: len(events)]
        or observed_states[-1:] != [current]
        or any(
            set(item) != {"bindingDigest", "state"} or item.get("bindingDigest") != binding_digest
            for item in events
            if isinstance(item, dict)
        )
        or len(observed_states) != len(events)
    ):
        raise ValueError("publication-transition-invalid")
    return {
        **document,
        "events": [*events, {"bindingDigest": binding_digest, "state": target}],
        "state": target,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.add_argument("root", type=Path)
    init.add_argument("output", type=Path)
    advance = subparsers.add_parser("transition")
    advance.add_argument("record", type=Path)
    advance.add_argument("target", choices=tuple(TRANSITIONS.values()))
    args = parser.parse_args()
    try:
        document = (
            initialize(args.root)
            if args.command == "init"
            else transition(json.loads(args.record.read_text(encoding="utf-8")), args.target)
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"category": str(error), "verdict": "blocked"}, sort_keys=True))
        return 1
    output = args.output if args.command == "init" else args.record
    output.write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"state": document["state"], "verdict": "pass"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
