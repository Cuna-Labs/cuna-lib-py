"""Build the candidate-bound statement signed by the release-evidence workflow."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from _approval import environment_gate_evidence, github_environment_execution
    from _evidence_utils import canonical_json_sha256, file_sha256
except ModuleNotFoundError:
    from tools._approval import environment_gate_evidence, github_environment_execution
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


def release_manifest_binding(artifacts: Path) -> dict[str, str]:
    """Read the already-verified inherited manifest binding from the PRD-094 handoff."""

    manifests = list(artifacts.rglob("release-admission-manifest.json"))
    if len(manifests) != 1:
        raise ValueError("admission-manifest-missing")
    admission = json.loads(manifests[0].read_text(encoding="utf-8"))
    inherited = admission.get("inheritedEvidence")
    release_manifest = inherited.get("releaseManifest") if isinstance(inherited, dict) else None
    files = release_manifest.get("files") if isinstance(release_manifest, dict) else None
    if (
        not isinstance(files, list)
        or len(files) != 1
        or not isinstance(files[0], dict)
        or re.fullmatch(r"[0-9a-f]{64}", str(files[0].get("sha256", ""))) is None
        or not isinstance(files[0].get("path"), str)
        or not files[0]["path"]
    ):
        raise ValueError("release-manifest-binding-invalid")
    return {"path": files[0]["path"], "sha256": files[0]["sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--environment-reference", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--environment-protection", type=Path, required=True)
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
        execution_authority = github_environment_execution(
            args.environment_reference, args.environment
        )
        environment_protection = environment_gate_evidence(
            args.environment_protection, args.environment
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
    try:
        release_manifest = release_manifest_binding(args.artifacts)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(str(error)) from None
    trusted = policy["trustedPublisher"]
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    evidence = {
        "admissionRun": admission_run,
        "environmentGateEvidence": {
            "commit": args.source,
            "executionAuthority": execution_authority,
            "environmentProtection": environment_protection,
            "reference": args.environment_reference,
            "type": "github-environment-gate",
        },
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
        "releaseManifest": release_manifest,
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
