"""Emit a deterministic, artifact-bound Python quality admission manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _evidence_utils import file_sha256
from inherited_evidence_gate import validate_inherited_evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--inherited-evidence", type=Path)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--candidate-only", action="store_true")
    parser.add_argument("--require-success", nargs="+", required=True)
    args = parser.parse_args()
    if args.local_only and args.candidate_only:
        raise SystemExit("R-094-19: candidate mode is ambiguous")
    if re.fullmatch(r"[0-9a-f]{40}", args.source) is None:
        raise SystemExit("R-094-18: immutable source digest is invalid")
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in args.artifacts.glob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    if len(artifacts) != 2:
        raise SystemExit("R-094-04: exact artifact pair is missing")
    expected = {
        (python, form)
        for python in ("3.10", "3.11", "3.12", "3.13", "3.14")
        for form in ("wheel", "sdist")
    }
    receipts: list[dict[str, object]] = []
    observed: set[tuple[str, str]] = set()
    artifact_digests = {item["sha256"] for item in artifacts}
    for path in sorted(args.receipts.glob("receipt-*.json")):
        match = re.fullmatch(r"receipt-(3\.\d+)-(wheel|sdist)\.json", path.name)
        if match is None:
            raise SystemExit("R-094-14: receipt identity is invalid")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        cell = (match.group(1), match.group(2))
        if (
            receipt.get("artifact_form") != cell[1]
            or receipt.get("sha256") not in artifact_digests
            or receipt.get("verdict") != "pass"
        ):
            raise SystemExit("R-094-18: receipt binding mismatch")
        observed.add(cell)
        receipts.append({"artifact": cell[1], "python": cell[0], **receipt})
    expected_budgets = {
        (python, form, mode) for python, form in expected for mode in ("sync", "async")
    }
    budgets: list[dict[str, object]] = []
    observed_budgets: set[tuple[str, str, str]] = set()
    for path in sorted(args.receipts.glob("budget-*.json")):
        match = re.fullmatch(r"budget-(3\.\d+)-(wheel|sdist)-(sync|async)\.json", path.name)
        if match is None:
            raise SystemExit("R-094-14: budget identity is invalid")
        budget = json.loads(path.read_text(encoding="utf-8"))
        cell = (match.group(1), match.group(2), match.group(3))
        expected_catalog = f"P-017-PY-{cell[1].upper()}-{cell[2].upper()}-V1"
        required_fields = {
            "benchmarkCommand",
            "caps",
            "dependencyClosure",
            "dependencyClosureDigest",
            "directDependencyReasons",
            "fixtureIds",
            "matrixTuple",
            "profileVersion",
            "statistics",
            "toolVersions",
        }
        if args.local_only:
            required_fields |= {"baselineProposal", "baselineProposalDigest"}
        else:
            required_fields |= {"baseline", "baselineDigest"}
        matrix = budget.get("matrixTuple")
        baseline = budget.get("baseline")
        if (
            budget.get("artifactForm") != cell[1]
            or budget.get("mode") != cell[2]
            or not str(budget.get("profile", "")).startswith(expected_catalog + "-")
            or budget.get("profileVersion") != "V1"
            or budget.get("artifactSha256") not in artifact_digests
            or budget.get("source") != args.source
            or budget.get("verdict") != ("diagnostic-pass" if args.local_only else "pass")
            or not required_fields.issubset(budget)
            or not isinstance(matrix, dict)
            or matrix.get("python") != cell[0]
            or matrix.get("artifactForm") != cell[1]
            or matrix.get("executionMode") != cell[2]
            or (
                not args.local_only
                and (
                    not isinstance(baseline, dict)
                    or re.fullmatch(
                        r"[0-9a-f]{64}",
                        str(baseline.get("referenceArtifactSha256", "")),
                    )
                    is None
                    or baseline.get("matrixTuple") != matrix
                    or re.fullmatch(r"[0-9a-f]{64}", str(budget.get("baselineDigest", ""))) is None
                )
            )
            or re.fullmatch(r"[0-9a-f]{64}", str(budget.get("dependencyClosureDigest", ""))) is None
        ):
            raise SystemExit("R-094-18: performance budget binding mismatch")
        observed_budgets.add(cell)
        budgets.append({"artifact": cell[1], "python": cell[0], "mode": cell[2], **budget})
    upstream = all(result == "success" for result in args.require_success)
    passed = upstream and observed == expected and observed_budgets == expected_budgets
    inherited: dict[str, object] | None = None
    if args.inherited_evidence is not None:
        if args.local_only:
            raise SystemExit("R-095-08: local admission cannot inherit release evidence")
        try:
            inherited = validate_inherited_evidence(args.inherited_evidence, args.source, artifacts)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise SystemExit(f"R-095-08: {exc}") from exc
    manifest = {
        "artifacts": artifacts,
        "cells": sorted(receipts, key=lambda item: (item["python"], item["artifact"])),
        "performanceCells": sorted(
            budgets, key=lambda item: (item["python"], item["artifact"], item["mode"])
        ),
        "releaseEligible": passed and inherited is not None and not args.local_only,
        "source": args.source,
        "verdict": (
            "pass"
            if passed and inherited is not None
            else "candidate-pass"
            if passed and args.candidate_only
            else "local-pass"
            if passed
            else "blocked"
        ),
    }
    if inherited is not None:
        manifest.update(
            {
                "inheritedEvidence": inherited["evidence"],
                "inheritedEvidenceBundleSha256": inherited["bundleSha256"],
                "inheritedEvidenceStatementSha256": inherited["statementSha256"],
            }
        )
    print(json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
