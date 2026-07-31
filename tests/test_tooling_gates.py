from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from tools.performance_gate import evaluate_budget
from tools.release_gate import policy_reachability
from tools.release_handoff_gate import validate_handoff


def passing_budget() -> dict[str, object]:
    return {
        "allocationBytesMax": 1,
        "artifactBytes": 1,
        "baseline": {
            "approvalReference": "approved/profile",
            "dependencyClosureDigest": "0" * 64,
            "metrics": {
                "allocationBytesMax": 1,
                "artifactBytes": 1,
                "connectionEstablishments": 1,
                "constructionMillisecondsP95": 1,
                "importMillisecondsP95": 1,
                "requestMillisecondsP95": 1,
                "retainedBytesP95": 1,
            },
            "profile": "profile",
            "status": "accepted",
        },
        "baselineDigest": "0" * 64,
        "benchmarkCommand": "controlled",
        "caps": {},
        "connectionEstablishments": 1,
        "constructionMillisecondsP95": 1,
        "defaultTransportOwnershipClosed": True,
        "dependencyClosure": [],
        "dependencyClosureDigest": "0" * 64,
        "directDependencyReasons": [],
        "fixtureIds": [],
        "importMillisecondsP95": 1,
        "lifecycleRequestCount": 500,
        "matrixTuple": {},
        "originIsolationVerified": True,
        "profile": "profile",
        "profileVersion": "V1",
        "requestMillisecondsP95": 1,
        "retainedBytesP95": 1,
        "reuseRequestCount": 10,
        "resourceCounters": {
            "asyncTasks": 0,
            "callbackRegistrations": 0,
            "lifecycleRegistrations": 0,
            "openConnections": 0,
            "openThreads": 0,
            "poolEntries": 0,
            "timers": 0,
        },
        "statistics": {},
        "toolVersions": {},
    }


@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("retainedBytesP95", 8_388_609),
        ("connectionEstablishments", 2),
        ("reuseRequestCount", 9),
        ("lifecycleRequestCount", 499),
        ("defaultTransportOwnershipClosed", False),
        ("originIsolationVerified", False),
    ],
)
def test_performance_gate_rejects_mutated_measurements(field: str, value: int) -> None:
    budget = passing_budget()
    assert evaluate_budget(budget, 1_048_576)
    budget[field] = value
    assert not evaluate_budget(budget, 1_048_576)


@pytest.mark.hermetic
@pytest.mark.parametrize("counter", ["openThreads", "timers", "asyncTasks", "openConnections"])
def test_performance_gate_rejects_retained_resources(counter: str) -> None:
    budget = passing_budget()
    mutated = copy.deepcopy(budget)
    mutated["resourceCounters"][counter] = 1  # type: ignore[index]
    assert not evaluate_budget(mutated, 1_048_576)


@pytest.mark.hermetic
def test_performance_gate_rejects_self_baseline_and_regression() -> None:
    proposal = passing_budget()
    proposal["baseline"]["status"] = "proposal"  # type: ignore[index]
    assert not evaluate_budget(proposal, 1_048_576)
    regression = passing_budget()
    regression["artifactBytes"] = 2
    assert not evaluate_budget(regression, 1_048_576)


@pytest.mark.hermetic
def test_release_policy_is_reachable_and_rejects_self_dependency() -> None:
    policy = {
        "sourceControl": {
            "branchProtection": {"requiredStatusChecks": ["py-quality-gates", "release-admission"]},
            "preAdmissionStatusChecks": ["py-quality-gates"],
        },
        "tag": {
            "signature": {"certificateIdentity": "https://example/release.yml@refs/heads/main"}
        },
    }
    assert policy_reachability(policy)
    circular = copy.deepcopy(policy)
    circular["sourceControl"]["preAdmissionStatusChecks"].append(  # type: ignore[index,union-attr]
        "release-admission"
    )
    assert not policy_reachability(circular)
    wrong_ref = copy.deepcopy(policy)
    wrong_ref["tag"]["signature"]["certificateIdentity"] = (  # type: ignore[index]
        "https://example/release.yml@refs/tags/py-v1.0.0"
    )
    assert not policy_reachability(wrong_ref)


@pytest.mark.hermetic
def test_performance_gate_never_forces_garbage_collection() -> None:
    source = (Path(__file__).parents[1] / "tools/performance_gate.py").read_text(encoding="utf-8")
    forbidden = "gc" + ".collect("
    assert forbidden not in source


@pytest.mark.hermetic
def test_release_handoff_requires_exact_artifacts_and_inherited_evidence(tmp_path) -> None:
    source = "a" * 40
    artifacts = []
    for filename, content in (
        ("runa_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("runa_sdk-0.1.0.tar.gz", b"sdist"),
    ):
        path = tmp_path / filename
        path.write_bytes(content)
        artifacts.append({"filename": filename, "sha256": hashlib.sha256(content).hexdigest()})
    inherited = {
        name: {"verdict": "pass"}
        for name in (
            "prd013Security",
            "prd014Compatibility",
            "prd015Conformance",
            "prd016Quality",
            "prd017Budgets",
            "provenance",
            "releaseManifest",
            "sbom",
        )
    }
    manifest = {
        "artifacts": artifacts,
        "cells": [{}] * 10,
        "inheritedEvidence": inherited,
        "performanceCells": [{}] * 20,
        "source": source,
        "verdict": "pass",
    }
    (tmp_path / "admission-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_handoff(tmp_path, source) is None
    manifest["artifacts"][0]["sha256"] = "0" * 64
    (tmp_path / "admission-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_handoff(tmp_path, source) == "artifact-substitution"
