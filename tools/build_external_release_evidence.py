"""Build the candidate-bound statement signed by the release-evidence workflow."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from _approval import external_environment_approval
    from _evidence_utils import canonical_json_sha256, file_sha256
except ModuleNotFoundError:
    from tools._approval import external_environment_approval
    from tools._evidence_utils import canonical_json_sha256, file_sha256


def admission_run_evidence(
    run_id: str, head_sha: str, conclusion: str, workflow: str, source: str
) -> dict[str, str]:
    if (
        re.fullmatch(r"[1-9][0-9]*", run_id) is None
        or head_sha != source
        or conclusion != "success"
        or workflow != "py-quality-gates"
    ):
        raise ValueError("admission-run-evidence-invalid")
    return {
        "conclusion": conclusion,
        "headSha": head_sha,
        "runId": run_id,
        "workflow": workflow,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--approval-environment", required=True)
    parser.add_argument("--admission-run-id", required=True)
    parser.add_argument("--admission-head-sha", required=True)
    parser.add_argument("--admission-conclusion", required=True)
    parser.add_argument("--admission-workflow", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source) is None:
        raise SystemExit("immutable-source-invalid")
    try:
        admission_run = admission_run_evidence(
            args.admission_run_id,
            args.admission_head_sha,
            args.admission_conclusion,
            args.admission_workflow,
            args.source,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from None
    try:
        approval_authority = external_environment_approval(
            args.approval_reference, args.approval_environment
        )
    except ValueError as error:
        raise SystemExit(str(error)) from None
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in args.artifacts.rglob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    if len(artifacts) != 2:
        raise SystemExit("artifact-pair-invalid")
    trusted = policy["trustedPublisher"]
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    evidence = {
        "admissionRun": admission_run,
        "approvals": [
            {
                "commit": args.source,
                "authority": approval_authority,
                "reference": args.approval_reference,
                "role": "protected-environment-execution",
            }
        ],
        "artifacts": artifacts,
        "identity": {
            **{
                key: trusted[key]
                for key in (
                    "issuer",
                    "subject",
                    "audience",
                    "repository",
                    "workflow",
                    "environment",
                )
            },
            "expiresAt": expires.isoformat().replace("+00:00", "Z"),
        },
        "policySha256": canonical_json_sha256(policy),
        "sourceCommit": args.source,
        "tag": args.tag,
        "trustedPublisher": trusted,
    }
    args.output.write_text(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
