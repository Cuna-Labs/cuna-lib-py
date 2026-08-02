from __future__ import annotations

import base64
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools._approval import (
    environment_gate_evidence,
    github_environment_execution,
    verify_provider_receipt,
)
from tools.build_external_release_evidence import (
    admission_run_evidence,
    python_release_core_binding,
    release_manifest_binding,
)
from tools.github_release_assets import stage as stage_github_release_assets
from tools.github_release_assets import verify as verify_github_release_assets
from tools.inherited_evidence_gate import (
    AUTHORITY_REPOSITORY,
    AUTHORITY_WORKFLOW,
    CERTIFICATE_IDENTITY,
    CERTIFICATE_ISSUER,
    REQUIRED_EVIDENCE,
    validate_inherited_evidence,
)
from tools.local_candidate_manifest import build_manifest
from tools.package_gate import public_surface_matches
from tools.performance_gate import evaluate_budget
from tools.postpublish_gate import recovery_action, verify_published
from tools.publication_state import initialize as initialize_publication_state
from tools.publication_state import transition as transition_publication_state
from tools.pypi_absence_gate import version_is_absent
from tools.release_gate import policy_reachability
from tools.release_handoff_gate import validate_candidate_handoff, validate_handoff
from tools.sbom_gate import EXPECTED_SBOM_POLICY, validate_configuration, validate_sboms
from tools.shared_oracle_gate import compare_shared_oracles
from tools.stage_publish_artifacts import stage_publish_artifacts
from tools.tag_creation_gate import validate_tag_candidate
from tools.tag_handoff import build_tag_handoff, validate_tag_handoff
from tools.trace_requirements import ACCEPTANCE_ROW, REQUIREMENT_ROW, table_ids
from tools.workflow_yaml_gate import validate_workflows


@pytest.mark.hermetic
def test_environment_execution_rejects_self_asserted_or_wrong_references() -> None:
    reference = (
        "github-environment://repositories/123/environments/pypi/runs/456/attempts/1/actors/789"
    )
    assert github_environment_execution(reference, "pypi") == {
        "attempt": "1",
        "environment": "pypi",
        "executionActorId": "789",
        "repositoryId": "123",
        "runId": "456",
        "type": "github-environment-execution",
    }
    for mutation in (
        "release-owner",
        reference.replace("/pypi/", "/production/"),
        reference.replace("/actors/789", "/actors/0"),
        reference + "/approved",
    ):
        with pytest.raises(ValueError, match="github-environment-execution-invalid"):
            github_environment_execution(mutation, "pypi")


@pytest.mark.hermetic
def test_external_evidence_uses_observed_admission_run_not_synthesized_passes() -> None:
    builder = (Path(__file__).parents[1] / "tools/build_external_release_evidence.py").read_text(
        encoding="utf-8"
    )
    workflow = (Path(__file__).parents[1] / ".github/workflows/release-evidence.yml").read_text(
        encoding="utf-8"
    )
    assert '"statusChecks"' not in builder
    assert '"branchProtection"' not in builder
    assert '"approvals":' not in builder
    assert '"admissionRun"' in builder
    assert '"environmentGateEvidence"' in builder
    assert '--json workflowName --jq .workflowName)" = "py-quality-gates"' in workflow
    assert 'gh api "repos/${GITHUB_REPOSITORY}/environments/pypi"' in workflow
    assert 'select(.type=="required_reviewers")' in workflow

    source = "a" * 40
    assert admission_run_evidence("123", source, "success", "py-quality-gates", source) == {
        "conclusion": "success",
        "headSha": source,
        "runId": "123",
        "workflow": "py-quality-gates",
    }
    for mutation in (
        ("0", source, "success", "py-quality-gates"),
        ("123", "b" * 40, "success", "py-quality-gates"),
        ("123", source, "failure", "py-quality-gates"),
        ("123", source, "success", "another-workflow"),
    ):
        with pytest.raises(ValueError, match="admission-run-evidence-invalid"):
            admission_run_evidence(*mutation, source)


@pytest.mark.hermetic
def test_environment_protection_requires_observed_required_reviewer(tmp_path) -> None:
    evidence = tmp_path / "environment-protection.json"
    evidence.write_text('{"environment":"pypi","requiredReviewerCount":1}', encoding="utf-8")
    record = environment_gate_evidence(evidence, "pypi")
    assert record["requiredReviewerCount"] == 1
    assert record["sha256"] == hashlib.sha256(evidence.read_bytes()).hexdigest()

    for mutation in (
        {"environment": "pypi", "requiredReviewerCount": 0},
        {"environment": "other", "requiredReviewerCount": 1},
        {"environment": "pypi", "requiredReviewerCount": True},
        {"environment": "pypi", "requiredReviewerCount": 1, "reviewer": "self"},
    ):
        evidence.write_text(json.dumps(mutation), encoding="utf-8")
        with pytest.raises(ValueError, match="environment-gate-evidence-invalid"):
            environment_gate_evidence(evidence, "pypi")

    performance_workflow = (
        Path(__file__).parents[1] / ".github/workflows/performance-baseline.yml"
    ).read_text(encoding="utf-8")
    assert (
        'gh api "repos/${GITHUB_REPOSITORY}/environments/performance-baseline"'
        in performance_workflow
    )
    assert 'select(.type=="required_reviewers")' in performance_workflow


@pytest.mark.hermetic
def test_publish_handoff_stages_only_a_flat_exact_artifact_pair(tmp_path) -> None:
    handoff = tmp_path / "handoff"
    candidate = handoff / "candidate"
    candidate.mkdir(parents=True)
    (candidate / "runa_sdk-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (candidate / "runa_sdk-0.1.0.tar.gz").write_bytes(b"sdist")
    (handoff / "admission-manifest.json").write_text("{}", encoding="utf-8")
    (handoff / "evidence.json").write_text("{}", encoding="utf-8")

    output = tmp_path / "publish-dist"
    records = stage_publish_artifacts(handoff, output)
    assert {item["filename"] for item in records} == {
        "runa_sdk-0.1.0-py3-none-any.whl",
        "runa_sdk-0.1.0.tar.gz",
    }
    assert sorted(path.name for path in output.iterdir()) == sorted(
        item["filename"] for item in records
    )

    (output / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="publish-directory-not-empty"):
        stage_publish_artifacts(handoff, output)


@pytest.mark.hermetic
def test_release_workflow_publishes_from_exclusive_flat_directory() -> None:
    workflow = (Path(__file__).parents[1] / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    assert "python tools/stage_publish_artifacts.py handoff publish-dist" in workflow
    assert "packages-dir: publish-dist" in workflow
    assert "packages-dir: handoff\n" not in workflow
    assert "- create-tag" in workflow
    assert "- publish" in workflow
    assert "if: inputs.phase == 'create-tag'" in workflow
    assert "if: inputs.phase == 'publish'" in workflow
    assert 'git push origin "refs/tags/${TAG}"' in workflow
    assert "pypa/gh-action-pypi-publish" in workflow
    assert 'gh release create "${TAG}" --verify-tag' in workflow
    assert 'gh release upload "${TAG}" github-release-assets/*' in workflow
    assert "--clobber" not in workflow
    assert 'gh release download "${TAG}" --dir github-release-retrieved' in workflow
    assert "python tools/github_release_assets.py verify" in workflow
    assert "          - create-tag\n          - publish\n" in workflow
    assert "- recover" not in workflow
    assert "recovery_run_id:" not in workflow
    assert "  recover-publication:" not in workflow
    verify_handoff_job = workflow[
        workflow.index("  verify-handoff:") : workflow.index("  tag-authority:")
    ]
    assert "if: github.event_name == 'workflow_dispatch'" in verify_handoff_job
    assert "group: python-release-runa-sdk-${{ inputs.tag || github.ref }}" in workflow
    assert "cancel-in-progress: false" in workflow
    create_job = workflow.index("  create-tag:")
    publish_job = workflow.index("  publish:")
    assert "pypa/gh-action-pypi-publish" not in workflow[create_job:publish_job]
    assert "git tag -s" not in workflow[publish_job:]
    assert "git push" not in workflow[publish_job:]
    assert "git config --local gpg.format x509" in workflow[create_job:publish_job]
    assert "git config --local gpg.x509.program gitsign" in workflow[create_job:publish_job]
    assert 'git tag -s -m "runa-sdk ${TAG}" "${TAG}" "${GITHUB_SHA}"' in workflow
    absence_gate = "python tools/pypi_absence_gate.py --version"
    assert absence_gate in workflow
    assert workflow.index(absence_gate) < workflow.index("pypa/gh-action-pypi-publish")
    assert "name: python-tagged-candidate-handoff" in workflow
    assert "tag_run_id:" in workflow
    assert "python tools/tag_handoff.py check handoff" in workflow
    assert workflow.count("actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5") == 3
    assert workflow.count('go-version: "1.24.11"') == 3
    assert "  pull_request:" in workflow
    branch_job = workflow[workflow.index("  branch-policy:") : workflow.index("  verify-handoff:")]
    assert "name: release-admission" in branch_job
    assert "pypa/gh-action-pypi-publish" not in branch_job
    assert "git tag" not in branch_job
    assert "id-token: write" not in branch_job
    assert (
        workflow.count("git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main") >= 2
    )
    assert 'gh attestation verify handoff/candidate/*.whl --repo "${GITHUB_REPOSITORY}"' in workflow
    assert (
        'gh attestation verify handoff/candidate/*.tar.gz --repo "${GITHUB_REPOSITORY}"' in workflow
    )
    tag_authority = workflow[
        workflow.index("  tag-authority:") : workflow.index("  publish-authority:")
    ]
    assert "environment: pypi" not in tag_authority
    assert "approval" not in tag_authority
    publish_authority = workflow[
        workflow.index("  publish-authority:") : workflow.index("  create-tag:")
    ]
    assert "environment: pypi" in publish_authority
    assert "--approval-receipt handoff/approval-receipt.json" in publish_authority
    assert (
        'gitsign verify --certificate-identity="https://github.com/Runa-Laboratories/'
        'runa-lib-py/.github/workflows/release.yml@refs/heads/main" '
        '--certificate-oidc-issuer="https://token.actions.githubusercontent.com"' in workflow
    )


@pytest.mark.hermetic
def test_publication_recovery_is_isolated_and_never_republishes() -> None:
    workflow = (Path(__file__).parents[1] / ".github/workflows/publication-recovery.yml").read_text(
        encoding="utf-8"
    )
    assert "name: python-publication-recovery" in workflow
    assert "pypa/gh-action-pypi-publish" not in workflow
    assert "pypi_absence_gate.py" not in workflow
    assert "id-token: write" not in workflow
    assert "environment: pypi" not in workflow
    assert "ref: ${{ inputs.tag }}" in workflow
    assert workflow.index("ref: ${{ inputs.tag }}") < workflow.index("python -m uv lock --check")
    assert "python-publication-recovery --dir recovery" in workflow
    assert 'gh release upload "${TAG}" "${asset}"' in workflow
    assert "--clobber" not in workflow
    assert 'grep -Fxq "$(basename "${asset}")"' in workflow


@pytest.mark.hermetic
def test_pypi_absence_gate_permits_only_authoritative_404() -> None:
    assert version_is_absent(404)
    for status in (0, 200, 201, 301, 302, 307, 308, 400, 401, 403, 429, 500, True):
        assert not version_is_absent(status)


@pytest.mark.hermetic
def test_github_release_assets_are_exact_digest_bound_and_retrieved(tmp_path) -> None:
    root = tmp_path / "handoff"
    inherited = root / "inherited"
    inherited.mkdir(parents=True)
    files: dict[str, list[dict[str, str]]] = {"sbom": [], "provenance": []}
    for key, suffix in (("sbom", "cdx.json"), ("provenance", "intoto.json")):
        for index in range(2):
            path = inherited / f"artifact-{index}.{suffix}"
            path.write_text(json.dumps({"index": index, "kind": key}), encoding="utf-8")
            files[key].append(
                {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            )
    (inherited / "inherited-evidence.json").write_text(
        json.dumps(
            {"evidence": {key: {"files": value, "verdict": "pass"} for key, value in files.items()}}
        ),
        encoding="utf-8",
    )
    (root / "release-core-manifest.json").write_text('{"verdict":"core-pass"}', encoding="utf-8")
    (root / "release-admission-manifest.json").write_text('{"state":"admitted"}', encoding="utf-8")
    staged = tmp_path / "staged"
    records = stage_github_release_assets(root, staged)
    assert len(records) == 6
    retrieved = tmp_path / "retrieved"
    retrieved.mkdir()
    for path in staged.iterdir():
        (retrieved / path.name).write_bytes(path.read_bytes())
    assert verify_github_release_assets(staged, retrieved) == records
    next(retrieved.iterdir()).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="github-release-retrieval-mismatch"):
        verify_github_release_assets(staged, retrieved)


@pytest.mark.hermetic
def test_publication_state_is_append_only_and_core_bound(tmp_path) -> None:
    for filename, content in (
        ("runa_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("runa_sdk-0.1.0.tar.gz", b"sdist"),
    ):
        (tmp_path / filename).write_bytes(content)
    core = {
        "artifacts": [],
        "releaseEligible": False,
        "source": "a" * 40,
        "verdict": "core-pass",
    }
    core_path = tmp_path / "release-core-manifest.json"
    core_path.write_text(json.dumps(core), encoding="utf-8")
    core_binding = python_release_core_binding(tmp_path)
    admission = {
        "approvalReceipt": {
            "receiptId": "receipt-1",
            "receiptSha256": "1" * 64,
            "verifier": "ed25519-detached-v1",
        },
        "core": {"path": core_binding["path"], "sha256": core_binding["sha256"]},
        "coreDigest": core_binding["coreDigest"],
        "schemaVersion": 1,
        "state": "admitted",
    }
    (tmp_path / "release-admission-manifest.json").write_text(
        json.dumps(admission), encoding="utf-8"
    )
    document = initialize_publication_state(tmp_path)
    uploaded = transition_publication_state(document, "uploaded-unverified")
    verified = transition_publication_state(uploaded, "registry-verified")
    assert [item["state"] for item in verified["events"]] == [
        "planned",
        "uploaded-unverified",
        "registry-verified",
    ]
    tampered = copy.deepcopy(uploaded)
    tampered["artifacts"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="publication-transition-invalid"):
        transition_publication_state(tampered, "registry-verified")
    stale = copy.deepcopy(uploaded)
    stale["events"] = stale["events"][1:]
    with pytest.raises(ValueError, match="publication-transition-invalid"):
        transition_publication_state(stale, "registry-verified")
    with pytest.raises(ValueError, match="publication-transition-invalid"):
        transition_publication_state(uploaded, "promoted")


@pytest.mark.hermetic
def test_tag_candidate_preflight_rejects_existing_or_policy_mutations() -> None:
    source = "a" * 40
    signature = {
        "certificateIdentity": (
            "https://github.com/Runa-Laboratories/runa-lib-py/.github/workflows/"
            "release.yml@refs/heads/main"
        ),
        "issuer": "https://token.actions.githubusercontent.com",
        "technology": "sigstore-keyless",
    }
    policy = {
        "sourceControl": {
            "provider": "github",
            "releaseBranch": "main",
            "repository": "Runa-Laboratories/runa-lib-py",
            "repositoryUri": "https://github.com/Runa-Laboratories/runa-lib-py",
        },
        "tag": {"signature": signature, "template": "py-v${version}"},
    }
    assert validate_tag_candidate("py-v0.1.0", source, policy, "0.1.0", tag_exists=False) is None
    assert (
        validate_tag_candidate("py-v0.1.0", source, policy, "0.1.0", tag_exists=True)
        == "tag-already-exists"
    )
    mutated = copy.deepcopy(policy)
    mutated["tag"]["signature"]["certificateIdentity"] = "self"  # type: ignore[index]
    assert (
        validate_tag_candidate("py-v0.1.0", source, mutated, "0.1.0", tag_exists=False)
        == "release-policy-tag-mismatch"
    )


@pytest.mark.hermetic
def test_release_manifest_binding_is_exact_and_environment_gate_is_not_approval(tmp_path) -> None:
    core = {"artifacts": [], "source": "a" * 40, "tag": "py-v0.1.0"}
    core_path = tmp_path / "release-manifest.json"
    core_path.write_text(json.dumps(core), encoding="utf-8")
    core_sha = hashlib.sha256(core_path.read_bytes()).hexdigest()
    admission = {
        "inheritedEvidence": {
            "releaseManifest": {
                "files": [{"path": "release-manifest.json", "sha256": core_sha}],
                "verdict": "pass",
            }
        }
    }
    (tmp_path / "release-core-manifest.json").write_text(json.dumps(admission), encoding="utf-8")
    assert release_manifest_binding(tmp_path) == {
        "canonicalDigest": hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "path": "release-manifest.json",
        "sha256": core_sha,
    }
    gate = (Path(__file__).parents[1] / "tools/release_gate.py").read_text(encoding="utf-8")
    assert "verify_provider_receipt(" in gate
    assert '"approval-envelope-binding-invalid"' in gate


@pytest.mark.hermetic
def test_python_release_core_digest_binds_every_core_field(tmp_path) -> None:
    core = {
        "artifacts": [{"filename": "artifact.whl", "sha256": "1" * 64}],
        "cells": [{"python": "3.13", "verdict": "pass"}],
        "inheritedEvidence": {"sbom": {"files": [], "verdict": "pass"}},
        "performanceCells": [{"python": "3.13", "verdict": "pass"}],
        "releaseEligible": False,
        "source": "a" * 40,
        "verdict": "core-pass",
    }
    path = tmp_path / "release-core-manifest.json"
    path.write_text(json.dumps(core), encoding="utf-8")
    expected = python_release_core_binding(tmp_path)
    assert expected["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    for field in ("artifacts", "cells", "inheritedEvidence", "performanceCells", "source"):
        mutated = copy.deepcopy(core)
        mutated[field] = [] if field != "source" else "b" * 40
        path.write_text(json.dumps(mutated), encoding="utf-8")
        assert python_release_core_binding(tmp_path)["coreDigest"] != expected["coreDigest"]


@pytest.mark.hermetic
def test_provider_receipt_verifier_binds_signature_core_artifacts_and_trust(tmp_path) -> None:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_path = tmp_path / "approval-public-key.pem"
    public_path.write_bytes(public)
    trust = {
        "authority": {
            "approverRole": "release-owner",
            "artifactName": "python-release-approval",
            "event": "workflow_dispatch",
            "maximumValiditySeconds": 7200,
            "policyId": "runa-python-release-v1",
            "providerId": "provider-1",
            "publicKeyPath": public_path.name,
            "publicKeySha256": hashlib.sha256(public).hexdigest(),
            "repository": "Runa-Laboratories/runa-lib-py",
            "ref": "main",
            "retrievalUriPrefix": "github-actions://Runa-Laboratories/runa-lib-py/runs/",
            "workflow": "python-release-approval",
        },
        "schemaVersion": 1,
        "status": "accepted",
    }
    trust_path = tmp_path / "trust.json"
    trust_path.write_text(json.dumps(trust), encoding="utf-8")
    artifacts = [
        {"filename": "runa_sdk-0.1.0-py3-none-any.whl", "sha256": "1" * 64},
        {"filename": "runa_sdk-0.1.0.tar.gz", "sha256": "2" * 64},
    ]
    receipt = {
        "approverRole": "release-owner",
        "artifacts": artifacts,
        "coreDigest": "3" * 64,
        "decision": "approve",
        "expiresAt": "2026-08-02T19:00:00Z",
        "issuedAt": "2026-08-02T17:00:00Z",
        "policyId": "runa-python-release-v1",
        "providerId": "provider-1",
        "receiptId": "receipt-123",
        "retrievalUri": "github-actions://Runa-Laboratories/runa-lib-py/runs/123",
        "revoked": False,
        "schemaVersion": 1,
    }
    receipt_path = tmp_path / "receipt.json"
    signature_path = tmp_path / "receipt.sig"

    def write_signed(value: dict[str, object]) -> None:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        receipt_path.write_bytes(encoded)
        signature_path.write_text(
            base64.b64encode(private.sign(encoded)).decode(), encoding="ascii"
        )

    write_signed(receipt)
    result = verify_provider_receipt(
        receipt_path,
        signature_path,
        trust_path,
        core_digest="3" * 64,
        artifacts=artifacts,
        now=datetime(2026, 8, 2, 18, tzinfo=timezone.utc),
    )
    assert result["receiptId"] == "receipt-123"
    for field, value in (
        ("decision", "reject"),
        ("coreDigest", "4" * 64),
        ("revoked", True),
        ("approverRole", "caller"),
        ("retrievalUri", "github-actions://Runa-Laboratories/runa-lib-py/runs-evil/123"),
    ):
        mutated = copy.deepcopy(receipt)
        mutated[field] = value
        write_signed(mutated)
        with pytest.raises(ValueError, match="approval-receipt-binding-invalid"):
            verify_provider_receipt(
                receipt_path,
                signature_path,
                trust_path,
                core_digest="3" * 64,
                artifacts=artifacts,
                now=datetime(2026, 8, 2, 18, tzinfo=timezone.utc),
            )
    write_signed(receipt)
    signature_path.write_text(base64.b64encode(b"invalid").decode(), encoding="ascii")
    with pytest.raises(ValueError, match="approval-receipt-signature-invalid"):
        verify_provider_receipt(
            receipt_path,
            signature_path,
            trust_path,
            core_digest="3" * 64,
            artifacts=artifacts,
            now=datetime(2026, 8, 2, 18, tzinfo=timezone.utc),
        )
    excessive = copy.deepcopy(receipt)
    excessive["expiresAt"] = "2026-08-03T17:00:01Z"
    write_signed(excessive)
    with pytest.raises(ValueError, match="approval-receipt-time-invalid"):
        verify_provider_receipt(
            receipt_path,
            signature_path,
            trust_path,
            core_digest="3" * 64,
            artifacts=artifacts,
            now=datetime(2026, 8, 2, 18, tzinfo=timezone.utc),
        )


@pytest.mark.hermetic
def test_sbom_policy_schema_and_cli_validation_are_all_required(tmp_path) -> None:
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    tools = json.loads(Path(".runa/supply-chain-tools.json").read_text(encoding="utf-8"))
    validate_configuration(policy, tools)
    assert policy["sbom"] == EXPECTED_SBOM_POLICY
    files = []
    for index in range(2):
        path = tmp_path / f"artifact-{index}.cdx.json"
        path.write_text(
            json.dumps(
                {
                    "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.6",
                }
            ),
            encoding="utf-8",
        )
        files.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps({"evidence": {"sbom": {"files": files, "verdict": "pass"}}}),
        encoding="utf-8",
    )
    commands: list[list[str]] = []
    assert (
        len(validate_sboms(tmp_path, "cyclonedx-cli", runner=lambda cmd: not commands.append(cmd)))
        == 2
    )
    assert commands[0] == ["cyclonedx-cli", "--version"]
    assert all("--input-version" in command and "v1_6" in command for command in commands[1:])
    mutated = copy.deepcopy(tools)
    mutated["cyclonedxCli"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="supply-chain-tool-policy-invalid"):
        validate_configuration(policy, mutated)


@pytest.mark.hermetic
def test_quality_workflow_covers_httpx_declared_range_edges() -> None:
    workflow = (Path(__file__).parents[1] / ".github/workflows/quality.yml").read_text(
        encoding="utf-8"
    )
    assert 'httpx: ["0.27.2", "latest"]' in workflow
    assert '"httpx>=0.27.2,<1"' in workflow
    assert '"httpx==${{ matrix.httpx }}"' in workflow
    assert "needs: [build-once, installed-artifact, httpx-compatibility]" in workflow
    assert "inherited_run_id:" not in workflow
    assert "--candidate-only" in workflow
    assert "name: python-candidate-handoff" in workflow
    assert "name: python-admitted-handoff" not in workflow


@pytest.mark.hermetic
def test_every_workflow_is_strict_yaml_1_2() -> None:
    workflow_root = Path(__file__).parents[1] / ".github/workflows"
    validated = validate_workflows(workflow_root)
    assert set(validated) == {path.name for path in workflow_root.glob("*.yml")}
    assert "quality.yml" in validated


@pytest.mark.hermetic
def test_shared_contract_oracle_detects_cross_language_semantic_mutation(tmp_path) -> None:
    local = tmp_path / "python.json"
    peer = tmp_path / "typescript.json"
    local.write_text('{"operations":{"me.get":{"method":"GET"}}}', encoding="utf-8")
    peer.write_text('{\n  "operations": {"me.get": {"method": "GET"}}\n}', encoding="utf-8")
    assert compare_shared_oracles(local, [peer])["verdict"] == "pass"

    peer.write_text('{"operations":{"me.get":{"method":"POST"}}}', encoding="utf-8")
    with pytest.raises(ValueError, match="shared-contract-semantic-drift"):
        compare_shared_oracles(local, [peer])


@pytest.mark.hermetic
def test_public_surface_binding_rejects_artifact_substitution(tmp_path) -> None:
    wheel = tmp_path / "runa_sdk-0.1.0-py3-none-any.whl"
    surface = tmp_path / "public-surface.json"
    wheel.write_bytes(b"wheel")
    surface.write_text(
        json.dumps({"artifactSha256": hashlib.sha256(b"wheel").hexdigest()}),
        encoding="utf-8",
    )
    assert public_surface_matches(wheel, surface)
    wheel.write_bytes(b"substituted")
    assert not public_surface_matches(wheel, surface)


@pytest.mark.hermetic
def test_local_candidate_manifest_is_explicitly_unattested_and_digest_bound(tmp_path) -> None:
    (tmp_path / "runa_sdk-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (tmp_path / "runa_sdk-0.1.0.tar.gz").write_bytes(b"sdist")
    manifest = build_manifest(tmp_path)
    assert manifest["evidenceClass"] == "local-only-unattested"
    assert manifest["verdict"] == "local-pass"
    assert manifest["sourceState"] == "source-tree"
    assert manifest["limitations"] == [
        "not-an-external-approval",
        "not-a-signature-or-provenance-statement",
        "not-a-release-admission",
    ]
    assert {item["sha256"] for item in manifest["artifacts"]} == {
        hashlib.sha256(b"wheel").hexdigest(),
        hashlib.sha256(b"sdist").hexdigest(),
    }


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
def test_requirement_trace_owns_only_exact_table_rows() -> None:
    text = """
Prose mentions R-073-18 and TC-073-99 but does not define either.

| ID | Force | Requirement |
| --- | --- | --- |
| R-073-17 | MUST | Defined. |

| Test | Given | When |
| --- | --- | --- |
| TC-073-09 | Fixture | Gate runs. |
"""
    assert table_ids(text, REQUIREMENT_ROW, 73) == ["R-073-17"]
    assert table_ids(text, ACCEPTANCE_ROW, 73) == ["TC-073-09"]


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
    assert passed["transitions"] == ["uploaded-unverified", "registry-verified"]
    assert passed["state"] == "registry-verified"
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
    core = {
        "artifacts": artifacts,
        "cells": [{}] * 10,
        "inheritedEvidence": inherited,
        "inheritedEvidenceBundleSha256": "2" * 64,
        "inheritedEvidenceStatementSha256": "3" * 64,
        "performanceCells": [{}] * 20,
        "releaseEligible": False,
        "source": source,
        "verdict": "core-pass",
    }
    core_path = tmp_path / "release-core-manifest.json"
    core_path.write_text(json.dumps(core), encoding="utf-8")
    envelope = {
        "approvalReceipt": {
            "receiptId": "receipt-1",
            "receiptSha256": "4" * 64,
            "verifier": "ed25519-detached-v1",
        },
        "core": {
            "path": "release-core-manifest.json",
            "sha256": hashlib.sha256(core_path.read_bytes()).hexdigest(),
        },
        "coreDigest": hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "schemaVersion": 1,
        "state": "admitted",
    }
    envelope_path = tmp_path / "release-admission-manifest.json"
    envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
    assert validate_handoff(tmp_path, source) is None
    core["artifacts"][0]["sha256"] = "0" * 64
    core_path.write_text(json.dumps(core), encoding="utf-8")
    assert validate_handoff(tmp_path, source) == "artifact-substitution"


@pytest.mark.hermetic
def test_candidate_handoff_is_pre_tag_and_cannot_claim_release_eligibility(tmp_path) -> None:
    source = "a" * 40
    artifacts = []
    for filename, content in (
        ("runa_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("runa_sdk-0.1.0.tar.gz", b"sdist"),
    ):
        (tmp_path / filename).write_bytes(content)
        artifacts.append({"filename": filename, "sha256": hashlib.sha256(content).hexdigest()})
    manifest = {
        "artifacts": artifacts,
        "cells": [{}] * 10,
        "performanceCells": [{}] * 20,
        "releaseEligible": False,
        "source": source,
        "verdict": "candidate-pass",
    }
    path = tmp_path / "candidate-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_candidate_handoff(tmp_path, source) is None
    manifest["releaseEligible"] = True
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_candidate_handoff(tmp_path, source) == "candidate-manifest-overclaim"


@pytest.mark.hermetic
def test_tag_handoff_binds_two_dispatches_to_exact_candidate(tmp_path, monkeypatch) -> None:
    source = "a" * 40
    artifacts = []
    for filename, content in (
        ("runa_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("runa_sdk-0.1.0.tar.gz", b"sdist"),
    ):
        (tmp_path / filename).write_bytes(content)
        artifacts.append({"filename": filename, "sha256": hashlib.sha256(content).hexdigest()})
    (tmp_path / "candidate-manifest.json").write_text(
        json.dumps(
            {
                "artifacts": artifacts,
                "cells": [{}] * 10,
                "performanceCells": [{}] * 20,
                "releaseEligible": False,
                "source": source,
                "verdict": "candidate-pass",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("tools.tag_handoff._tag_object", lambda tag: "b" * 40)
    record = build_tag_handoff(tmp_path, source, "py-v0.1.0", "123")
    (tmp_path / "tag-handoff.json").write_text(json.dumps(record), encoding="utf-8")
    assert validate_tag_handoff(tmp_path, source, "py-v0.1.0") is None
    record["phase"] = "publish"
    (tmp_path / "tag-handoff.json").write_text(json.dumps(record), encoding="utf-8")
    assert validate_tag_handoff(tmp_path, source, "py-v0.1.0") == "tag-handoff-mismatch"


@pytest.mark.hermetic
def test_inherited_evidence_uses_independent_release_authority() -> None:
    assert AUTHORITY_REPOSITORY == "Runa-Laboratories/runa-release-authority"
    assert AUTHORITY_WORKFLOW == "release-authority.yml"
    assert CERTIFICATE_IDENTITY == (
        "https://github.com/Runa-Laboratories/runa-release-authority/.github/workflows/"
        "release-authority.yml@refs/heads/main"
    )
    source = (Path(__file__).parents[1] / "tools/inherited_evidence_gate.py").read_text(
        encoding="utf-8"
    )
    assert "PromptExecution" not in source
    assert "Runta" not in source


@pytest.mark.hermetic
def test_inherited_evidence_is_signed_content_verified_and_candidate_bound(tmp_path) -> None:
    source = "a" * 40
    authority_head = "b" * 40
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
                    "builder": {
                        "id": "https://github.com/Runa-Laboratories/runa-release-authority/actions"
                    },
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
        "authorityHeadSha": authority_head,
        "candidateSourceSha": source,
        "certificateIdentity": CERTIFICATE_IDENTITY,
        "certificateIssuer": CERTIFICATE_ISSUER,
        "dependencyClosure": closure,
        "evidence": evidence,
        "schemaVersion": 1,
        "tag": "py-v0.1.0",
    }
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(statement, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    (tmp_path / "inherited-evidence.sigstore.json").write_text("{}", encoding="utf-8")
    verified_authority_heads: list[str] = []
    result = validate_inherited_evidence(
        tmp_path,
        source,
        authority_head,
        artifacts,
        signature_verifier=lambda statement, bundle, digest: (
            verified_authority_heads.append(digest) or True
        ),
    )
    assert set(result["evidence"]) == REQUIRED_EVIDENCE
    assert verified_authority_heads == [authority_head]
    assert result["candidateSourceSha"] == source
    assert result["authorityHeadSha"] == authority_head

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
            authority_head,
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
            authority_head,
            artifacts,
            signature_verifier=lambda statement, bundle, digest: True,
        )

    statement["candidateSourceSha"] = "c" * 40
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(statement, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="candidate-mismatch"):
        validate_inherited_evidence(
            tmp_path,
            source,
            authority_head,
            artifacts,
            signature_verifier=lambda statement, bundle, digest: True,
        )
