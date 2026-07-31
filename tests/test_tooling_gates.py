from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.inherited_evidence_gate import (
    CERTIFICATE_IDENTITY,
    CERTIFICATE_ISSUER,
    REQUIRED_EVIDENCE,
    validate_inherited_evidence,
)
from tools.performance_gate import evaluate_budget
from tools.postpublish_gate import recovery_action, verify_published
from tools.release_gate import policy_reachability
from tools.release_handoff_gate import validate_handoff


def passing_budget() -> dict[str, object]:
    return {
        "allocationBytesMax": 1,
        "artifactBytes": 1,
        "baseline": {
            "approvalReference": "approved/profile",
            "authority": {
                "certificateIdentity": (
                    "https://github.com/Runa-Laboratories/runa-lib-py/.github/workflows/"
                    "performance-baseline.yml@refs/heads/main"
                ),
                "issuer": "https://token.actions.githubusercontent.com",
            },
            "dependencyClosureDigest": "0" * 64,
            "matrixTuple": {},
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
            "referenceArtifactSha256": "f" * 64,
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
def test_performance_gate_rejects_unledgered_direct_dependency() -> None:
    mutated = passing_budget()
    mutated["dependencyClosure"] = [
        {"name": "new-runtime", "path": "runa-sdk -> new-runtime", "role": "direct"}
    ]
    assert not evaluate_budget(mutated, 1_048_576)


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
def test_postpublish_recovery_requires_explicit_owner_authorization() -> None:
    assert recovery_action("digest-mismatch", None) == "blocked-owner-decision"
    assert recovery_action("digest-mismatch", "no-yank") == "no-yank"
    assert recovery_action("digest-mismatch", "yank") == "yank"
    assert recovery_action("digest-mismatch", "advisory") == "advisory"


@pytest.mark.hermetic
def test_postpublish_promotes_only_exact_attested_pair(tmp_path, monkeypatch) -> None:
    expected = tmp_path / "expected"
    retrieved = tmp_path / "retrieved"
    expected.mkdir()
    retrieved.mkdir()
    for name, content in (
        ("runa_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("runa_sdk-0.1.0.tar.gz", b"sdist"),
    ):
        (expected / name).write_bytes(content)
        (retrieved / name).write_bytes(content)
    monkeypatch.setattr("tools.postpublish_gate.shutil.which", lambda name: "gh")
    monkeypatch.setattr(
        "tools.postpublish_gate.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    passed = verify_published(expected, retrieved, "owner/repository")
    assert passed["transitions"] == ["uploaded-unverified", "verified", "promoted"]
    (retrieved / "runa_sdk-0.1.0.tar.gz").write_bytes(b"substituted")
    blocked = verify_published(expected, retrieved, "owner/repository")
    assert blocked["state"] == "uploaded-unverified"
    assert blocked["recovery"] == "blocked-owner-decision"


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
        name: {"files": [{"path": f"{name}.json", "sha256": "1" * 64}], "verdict": "pass"}
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
        "inheritedEvidenceBundleSha256": "2" * 64,
        "inheritedEvidenceStatementSha256": "3" * 64,
        "performanceCells": [{}] * 20,
        "source": source,
        "verdict": "pass",
    }
    (tmp_path / "admission-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_handoff(tmp_path, source) is None
    manifest["artifacts"][0]["sha256"] = "0" * 64
    (tmp_path / "admission-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_handoff(tmp_path, source) == "artifact-substitution"


@pytest.mark.hermetic
def test_inherited_evidence_is_signed_content_verified_and_candidate_bound(tmp_path) -> None:
    source = "a" * 40
    artifacts = [
        {"filename": "runa_sdk-0.1.0-py3-none-any.whl", "sha256": "1" * 64},
        {"filename": "runa_sdk-0.1.0.tar.gz", "sha256": "2" * 64},
    ]
    evidence: dict[str, object] = {}

    def write(name: str, value: object) -> dict[str, str]:
        path = tmp_path / name
        path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    for key in sorted(REQUIRED_EVIDENCE - {"sbom", "provenance", "releaseManifest"}):
        item = write(
            f"{key}.json",
            {"artifacts": artifacts, "source": source, "verdict": "pass"},
        )
        evidence[key] = {"files": [item], "verdict": "pass"}
    sboms = []
    provenance = []
    closure = [{"name": "httpx", "version": "0.28.1"}]
    for artifact in artifacts:
        sboms.append(
            write(
                f"{artifact['filename']}.cdx.json",
                {
                    "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
                    "bomFormat": "CycloneDX",
                    "components": [
                        {"bom-ref": "pkg:pypi/httpx@0.28.1", "name": "httpx", "version": "0.28.1"}
                    ],
                    "dependencies": [
                        {
                            "dependsOn": ["pkg:pypi/httpx@0.28.1"],
                            "ref": f"pkg:pypi/{artifact['filename']}",
                        },
                        {"dependsOn": [], "ref": "pkg:pypi/httpx@0.28.1"},
                    ],
                    "metadata": {
                        "component": {
                            "bom-ref": f"pkg:pypi/{artifact['filename']}",
                            "hashes": [{"alg": "SHA-256", "content": artifact["sha256"]}],
                            "name": artifact["filename"],
                        }
                    },
                    "serialNumber": f"urn:uuid:{'1' * 32}",
                    "specVersion": "1.6",
                    "version": 1,
                },
            )
        )
        payload = {
            "_type": "https://in-toto.io/Statement/v1",
            "predicate": {
                "buildDefinition": {
                    "buildType": "https://github.com/Attestations/GitHubActionsWorkflow@v1",
                    "externalParameters": {"source": source, "tag": "py-v0.1.0"},
                    "resolvedDependencies": [
                        {"digest": {"sha256": "3" * 64}, "uri": "pkg:pypi/httpx@0.28.1"}
                    ],
                },
                "runDetails": {
                    "builder": {"id": "https://github.com/PromptExecution/Runa/actions"},
                    "metadata": {
                        "finishedOn": "2026-01-01T00:01:00Z",
                        "invocationId": "run-1",
                        "startedOn": "2026-01-01T00:00:00Z",
                    },
                },
            },
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [
                {
                    "digest": {"sha256": artifact["sha256"]},
                    "name": artifact["filename"],
                }
            ],
        }
        provenance.append(
            write(
                f"{artifact['filename']}.intoto.json",
                {
                    "payload": base64.b64encode(
                        json.dumps(payload, sort_keys=True).encode()
                    ).decode(),
                    "payloadType": "application/vnd.in-toto+json",
                    "signatures": [{"keyid": "github", "sig": "external"}],
                },
            )
        )
    evidence["sbom"] = {"files": sboms, "verdict": "pass"}
    evidence["provenance"] = {"files": provenance, "verdict": "pass"}
    evidence["releaseManifest"] = {
        "files": [
            write(
                "release-manifest.json",
                {"artifacts": artifacts, "source": source, "verdict": "pass"},
            )
        ],
        "verdict": "pass",
    }
    statement = {
        "artifacts": artifacts,
        "certificateIdentity": CERTIFICATE_IDENTITY,
        "certificateIssuer": CERTIFICATE_ISSUER,
        "dependencyClosure": closure,
        "evidence": evidence,
        "schemaVersion": 1,
        "source": source,
        "tag": "py-v0.1.0",
    }
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(statement, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    (tmp_path / "inherited-evidence.sigstore.json").write_text("{}", encoding="utf-8")
    result = validate_inherited_evidence(
        tmp_path,
        source,
        artifacts,
        signature_verifier=lambda statement, bundle, digest: True,
    )
    assert set(result["evidence"]) == REQUIRED_EVIDENCE

    sparse_statement = copy.deepcopy(statement)
    sparse_sbom_path = tmp_path / sboms[0]["path"]
    sparse_sbom = json.loads(sparse_sbom_path.read_text(encoding="utf-8"))
    sparse_sbom.pop("components")
    sparse_sbom_path.write_text(json.dumps(sparse_sbom), encoding="utf-8")
    sparse_statement["evidence"]["sbom"]["files"][0]["sha256"] = hashlib.sha256(  # type: ignore[index]
        sparse_sbom_path.read_bytes()
    ).hexdigest()
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(sparse_statement, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="sbom-components-missing"):
        validate_inherited_evidence(
            tmp_path,
            source,
            artifacts,
            signature_verifier=lambda statement, bundle, digest: True,
        )

    sparse_sbom_path.write_text(
        json.dumps(
            {
                "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
                "bomFormat": "CycloneDX",
                "components": [
                    {"bom-ref": "pkg:pypi/httpx@0.28.1", "name": "httpx", "version": "0.28.1"}
                ],
                "dependencies": [
                    {
                        "dependsOn": ["pkg:pypi/httpx@0.28.1"],
                        "ref": f"pkg:pypi/{artifacts[0]['filename']}",
                    },
                    {"dependsOn": [], "ref": "pkg:pypi/httpx@0.28.1"},
                ],
                "metadata": {
                    "component": {
                        "bom-ref": f"pkg:pypi/{artifacts[0]['filename']}",
                        "hashes": [{"alg": "SHA-256", "content": artifacts[0]["sha256"]}],
                        "name": artifacts[0]["filename"],
                    }
                },
                "serialNumber": f"urn:uuid:{'1' * 32}",
                "specVersion": "1.6",
                "version": 1,
            }
        ),
        encoding="utf-8",
    )
    unsigned_statement = copy.deepcopy(statement)
    unsigned_provenance_path = tmp_path / provenance[0]["path"]
    unsigned_provenance = json.loads(unsigned_provenance_path.read_text(encoding="utf-8"))
    unsigned_provenance["signatures"] = [{}]
    unsigned_provenance_path.write_text(json.dumps(unsigned_provenance), encoding="utf-8")
    unsigned_statement["evidence"]["sbom"]["files"][0]["sha256"] = hashlib.sha256(  # type: ignore[index]
        sparse_sbom_path.read_bytes()
    ).hexdigest()
    unsigned_statement["evidence"]["provenance"]["files"][0]["sha256"] = hashlib.sha256(  # type: ignore[index]
        unsigned_provenance_path.read_bytes()
    ).hexdigest()
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(unsigned_statement, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="provenance-envelope-invalid"):
        validate_inherited_evidence(
            tmp_path,
            source,
            artifacts,
            signature_verifier=lambda statement, bundle, digest: True,
        )

    statement["source"] = "b" * 40
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(statement, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="candidate-mismatch"):
        validate_inherited_evidence(
            tmp_path,
            source,
            artifacts,
            signature_verifier=lambda statement, bundle, digest: True,
        )
