"""Generate a source-bound, fail-closed local release-readiness decision."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    from _evidence_utils import file_set_sha256, file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_set_sha256, file_sha256


def source_digest() -> str:
    paths = [
        *Path("src").rglob("*.py"),
        *Path("tools").rglob("*.py"),
        *Path("tests").rglob("*.py"),
        *Path(".github/workflows").glob("*.yml"),
        Path("pyproject.toml"),
        Path("uv.lock"),
        Path(".runa/ci-policy.json"),
        Path(".runa/public-surface.json"),
        Path(".runa/release-policy.json"),
    ]
    return file_set_sha256(paths)


def verify_local() -> dict[str, object]:
    commands = {
        "format": [sys.executable, "-m", "ruff", "format", "--check", "."],
        "lint": [sys.executable, "-m", "ruff", "check", "."],
        "mypy": [sys.executable, "-m", "mypy", "src", "tests/typing/consumer.py"],
        "pyright": [
            sys.executable,
            "-m",
            "pyright",
            "src",
            "tests/typing/consumer.py",
        ],
        "tests": [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--cov=runa",
            "--cov-branch",
            "--cov-report=term",
        ],
        "dependencyAudit": [sys.executable, "-m", "pip_audit"],
        "dependencyPolicy": [
            sys.executable,
            "tools/dependency_gate.py",
        ],
        "duplicateAbstractions": [
            sys.executable,
            "tools/duplicate_abstraction_gate.py",
        ],
        "documentation": [
            sys.executable,
            "tools/docs_gate.py",
        ],
        "evidence": [
            sys.executable,
            "tools/evidence_gate.py",
        ],
        "package": [
            sys.executable,
            "tools/package_gate.py",
            "dist",
        ],
        "localCandidate": [
            sys.executable,
            "tools/local_candidate_manifest.py",
            "--artifacts",
            "dist",
        ],
        "safety": [
            sys.executable,
            "tools/safety_scan.py",
        ],
    }
    shared_peers = [
        Path("../typescript/contracts/runa-sdk.projection.json"),
        Path("../../infra/contracts/runa-sdk.projection.json"),
    ]
    if all(path.is_file() for path in shared_peers):
        commands["sharedOracle"] = [
            sys.executable,
            "tools/shared_oracle_gate.py",
            "contracts/runa-sdk-contract.snapshot.json",
            *(str(path) for path in shared_peers),
        ]
    results: dict[str, str] = {}
    for name, command in commands.items():
        completed = subprocess.run(  # noqa: S603 - fixed local gate command vectors
            command, capture_output=True, text=True, check=False
        )
        results[name] = "pass" if completed.returncode == 0 else "fail"
        if completed.returncode != 0:
            break
    return {
        "commands": results,
        "sourceDigest": source_digest(),
        "verdict": "pass"
        if len(results) == len(commands) and set(results.values()) == {"pass"}
        else "fail",
    }


def readiness() -> dict[str, object]:
    blockers: list[dict[str, str]] = []
    provenance = json.loads(
        Path("contracts/runa-sdk-contract.provenance.json").read_text(encoding="utf-8")
    )
    if provenance.get("status") != "approved":
        blockers.append(
            {
                "category": "contract-provenance",
                "evidence": "contracts/runa-sdk-contract.provenance.json",
                "requirement": "R-056-20",
            }
        )
    reference_path = Path(".runa/api-reference-gate.json")
    reference = (
        json.loads(reference_path.read_text(encoding="utf-8"))
        if reference_path.is_file()
        else {"verdict": "not-run"}
    )
    if reference.get("verdict") != "pass":
        blockers.append(
            {
                "category": "api-reference-documentation-incomplete",
                "evidence": ".runa/api-reference-gate.json",
                "requirement": "R-091-03",
            }
        )
    ci_policy = json.loads(Path(".runa/ci-policy.json").read_text(encoding="utf-8"))
    if ci_policy.get("runnerApproval") is None:
        blockers.append(
            {
                "category": "runner-owner-approval-missing",
                "evidence": ".runa/ci-policy.json",
                "requirement": "R-094-01",
            }
        )
    blockers.extend(
        [
            {
                "category": "installed-matrix-not-run",
                "detail": "CPython 3.10-3.14 wheel/sdist receipts are absent",
                "requirement": "R-094-18",
            },
            {
                "category": "performance-baseline-approval-missing",
                "detail": "bootstrap-v1 proposals are local diagnostics, not accepted baselines",
                "requirement": "R-017-21",
            },
            {
                "category": "inherited-supply-chain-handoff-missing",
                "detail": "PRD-013-017, SBOM, provenance, and release-manifest evidence are absent",
                "requirement": "R-095-08",
            },
            {
                "category": "signed-tag-and-publisher-evidence-missing",
                "detail": (
                    "Sigstore tag, external controls, and PyPI trusted-publisher "
                    "evidence are absent"
                ),
                "requirement": "R-095-10",
            },
            {
                "category": "release-smoke-not-run",
                "detail": "published exact-artifact retrieval and withdrawal rehearsal are absent",
                "requirement": "R-096-17",
            },
            {
                "category": "cross-language-attestation-missing",
                "detail": "shared acceptance is not bound to immutable language artifacts",
                "requirement": "R-019-20",
            },
        ]
    )
    local_path = Path(".runa/local-verification.json")
    local = (
        json.loads(local_path.read_text(encoding="utf-8"))
        if local_path.is_file()
        else {"verdict": "not-run"}
    )
    if local.get("sourceDigest") != source_digest():
        local = {"verdict": "stale"}
    candidate_path = Path("dist/local-candidate-manifest.json")
    candidate = (
        json.loads(candidate_path.read_text(encoding="utf-8"))
        if candidate_path.is_file()
        else {"verdict": "not-run"}
    )
    current_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    observed_artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in Path("dist").glob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    if (
        candidate.get("evidenceClass") != "local-only-unattested"
        or candidate.get("sourceDigest") != source_digest()
        or candidate.get("baseCommit") != current_commit
        or candidate.get("artifacts") != observed_artifacts
        or len(observed_artifacts) != 2
    ):
        candidate = {"verdict": "stale"}
        blockers.append(
            {
                "category": "local-candidate-manifest-stale",
                "evidence": "dist/local-candidate-manifest.json",
                "requirement": "R-093-01",
            }
        )
    return {
        "blockers": blockers,
        "localCandidate": candidate,
        "localEvidence": local,
        "releaseEligible": not blockers,
        "verdict": "READY" if not blockers else "BLOCKED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".runa/release-readiness.json"))
    parser.add_argument("--verify-local", action="store_true")
    args = parser.parse_args()
    if args.verify_local:
        local = verify_local()
        Path(".runa/local-verification.json").write_text(
            json.dumps(local, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    report = readiness()
    args.output.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["releaseEligible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
