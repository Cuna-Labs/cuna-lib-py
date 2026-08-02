"""Create and verify the immutable join between Python release dispatch phases."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

try:
    from _evidence_utils import file_sha256
    from release_handoff_gate import validate_candidate_handoff
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256
    from tools.release_handoff_gate import validate_candidate_handoff


def _tag_object(tag: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise ValueError("git-verifier-missing")
    result = subprocess.run(  # noqa: S603 -- resolved git executable and one validated ref
        [git, "rev-parse", f"{tag}^{{tag}}"], capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40,64}", value) is None:
        raise ValueError("annotated-tag-object-missing")
    return value


def build_tag_handoff(
    root: Path, source: str, tag: str, candidate_run_id: str
) -> dict[str, object]:
    if validate_candidate_handoff(root, source) is not None:
        raise ValueError("candidate-handoff-invalid")
    if (
        re.fullmatch(r"py-v\d+\.\d+\.\d+", tag) is None
        or re.fullmatch(r"[1-9][0-9]*", candidate_run_id) is None
    ):
        raise ValueError("tag-handoff-identity-invalid")
    manifests = list(root.rglob("candidate-manifest.json"))
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in root.rglob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    return {
        "artifacts": artifacts,
        "candidateManifestSha256": file_sha256(manifests[0]),
        "candidateRunId": candidate_run_id,
        "phase": "create-tag",
        "source": source,
        "tag": tag,
        "tagObject": _tag_object(tag),
    }


def validate_tag_handoff(root: Path, source: str, tag: str) -> str | None:
    records = list(root.rglob("tag-handoff.json"))
    if len(records) != 1:
        return "tag-handoff-missing"
    try:
        observed = json.loads(records[0].read_text(encoding="utf-8"))
        expected = build_tag_handoff(root, source, tag, str(observed.get("candidateRunId", "")))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return "tag-handoff-invalid"
    return None if observed == expected else "tag-handoff-mismatch"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("create", "check"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-run-id")
    args = parser.parse_args()
    if args.mode == "create":
        if args.candidate_run_id is None:
            raise SystemExit("candidate-run-id-missing")
        try:
            value = build_tag_handoff(
                root=args.root,
                source=args.source,
                tag=args.tag,
                candidate_run_id=args.candidate_run_id,
            )
        except ValueError as error:
            raise SystemExit(str(error)) from None
        (args.root / "tag-handoff.json").write_text(
            json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        return 0
    category = validate_tag_handoff(args.root, args.source, args.tag)
    if category is not None:
        raise SystemExit(category)
    print('{"requirement":"R-095-23","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
