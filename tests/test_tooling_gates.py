from __future__ import annotations

import base64
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ruamel.yaml import YAML

from tools import performance_baseline_gate
from tools._approval import (
    environment_gate_evidence,
    github_environment_execution,
    verify_provider_receipt,
)
from tools._release_identity import (
    AUTHORITY_EVIDENCE_IDENTITIES,
    PERFORMANCE_EVIDENCE_IDENTITIES,
)
from tools.branch_protection_gate import validate_python_protection
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
from tools.performance_baseline_gate import (
    DEFAULT_EXPECTED_REPOSITORY,
    validate_baselines,
)
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
    (candidate / "cuna_sdk-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (candidate / "cuna_sdk-0.1.0.tar.gz").write_bytes(b"sdist")
    (handoff / "admission-manifest.json").write_text("{}", encoding="utf-8")
    (handoff / "evidence.json").write_text("{}", encoding="utf-8")

    output = tmp_path / "publish-dist"
    records = stage_publish_artifacts(handoff, output)
    assert {item["filename"] for item in records} == {
        "cuna_sdk-0.1.0-py3-none-any.whl",
        "cuna_sdk-0.1.0.tar.gz",
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
    assert "group: python-release-cuna-sdk-${{ inputs.tag || github.ref }}" in workflow
    assert "cancel-in-progress: false" in workflow
    create_job = workflow.index("  create-tag:")
    publish_job = workflow.index("  publish:")
    publish_section = workflow[
        publish_job : workflow.index("  github-release-promotion:", publish_job)
    ]
    assert "pypa/gh-action-pypi-publish" not in workflow[create_job:publish_job]
    assert "git tag -s" not in workflow[publish_job:]
    assert "git push" not in workflow[publish_job:]
    assert "git config --local gpg.format x509" in workflow[create_job:publish_job]
    assert "git config --local gpg.x509.program gitsign" in workflow[create_job:publish_job]
    assert 'git tag -s -m "cuna-sdk ${TAG}" "${TAG}" "${GITHUB_SHA}"' in workflow
    absence_gate = "python tools/pypi_absence_gate.py --version"
    assert absence_gate in workflow
    assert workflow.index(absence_gate) < workflow.index("pypa/gh-action-pypi-publish")
    release_validation = (
        "python -m uv run --locked python tools/release_gate.py "
        '--tag "${{ inputs.tag }}" --artifacts handoff '
        "--evidence handoff/external-release-evidence.json "
        "--bundle handoff/external-release-evidence.sigstore.json "
        "--approval-receipt handoff/approval-receipt.json "
        "--approval-signature handoff/approval-receipt.sig"
    )
    assert publish_section.count(release_validation) == 2
    late_validation = publish_section.rindex(release_validation)
    assert publish_section.index("publication_state.py init") < publish_section.index(
        "stage_publish_artifacts.py"
    )
    assert publish_section.index("stage_publish_artifacts.py") < publish_section.index(absence_gate)
    assert publish_section.index(absence_gate) < late_validation
    assert late_validation < publish_section.index("pypa/gh-action-pypi-publish")
    assert (
        'release_handoff_gate.py handoff --source "${GITHUB_SHA}"'
        in publish_section[publish_section.index(absence_gate) : late_validation]
    )
    release_gate = (Path(__file__).parents[1] / "tools/release_gate.py").read_text(encoding="utf-8")
    assert "expires <= datetime.now(timezone.utc)" in release_gate
    assert "verify_provider_receipt(" in release_gate
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
    assert "python tools/branch_protection_gate.py branch-protection.json" in workflow
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
        'gitsign verify --certificate-identity="https://github.com/Cuna-Labs/'
        'cuna-lib-py/.github/workflows/release.yml@refs/heads/main" '
        '--certificate-oidc-issuer="https://token.actions.githubusercontent.com"' in workflow
    )


@pytest.mark.hermetic
def test_python_branch_protection_is_exact_single_author_and_fail_closed() -> None:
    protection = {
        "allow_deletions": {"enabled": False},
        "allow_force_pushes": {"enabled": False},
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": 0,
        },
        "required_status_checks": {
            "contexts": [
                "static-security",
                "release-admission",
                "py-quality-gates",
                "CodeQL",
            ]
        },
    }
    result = validate_python_protection(protection)
    assert result["pullRequestRequired"] is True
    assert result["requiredApprovingReviews"] == 0
    assert result["requiredCodeOwnerReviews"] is False
    policy = json.loads(Path(".cuna/release-policy.json").read_text(encoding="utf-8"))
    assert policy["sourceControl"]["branchProtection"] == {
        "directPushes": False,
        "dismissStaleApprovals": True,
        "requireCodeOwnerReviews": False,
        "requiredApprovingReviews": 0,
        "requiredStatusChecks": result["requiredStatusChecks"],
    }

    mutations = []
    for path, value in (
        (("required_status_checks", "contexts"), ["py-quality-gates"]),
        (("required_status_checks", "contexts"), [*result["requiredStatusChecks"], "extra"]),
        (("required_pull_request_reviews",), None),
        (("required_pull_request_reviews", "required_approving_review_count"), 1),
        (("required_pull_request_reviews", "required_approving_review_count"), False),
        (("required_pull_request_reviews", "dismiss_stale_reviews"), False),
        (("required_pull_request_reviews", "require_code_owner_reviews"), True),
        (("enforce_admins", "enabled"), False),
        (("allow_force_pushes", "enabled"), True),
        (("allow_deletions", "enabled"), True),
    ):
        mutated = copy.deepcopy(protection)
        if len(path) == 1:
            mutated[path[0]] = value
        else:
            mutated[path[0]][path[1]] = value
        mutations.append(mutated)
    for mutated in mutations:
        with pytest.raises(ValueError, match="branch-protection-invalid"):
            validate_python_protection(mutated)


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
        ("cuna_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("cuna_sdk-0.1.0.tar.gz", b"sdist"),
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
            "https://github.com/Cuna-Labs/cuna-lib-py/.github/workflows/release.yml@refs/heads/main"
        ),
        "issuer": "https://token.actions.githubusercontent.com",
        "technology": "sigstore-keyless",
    }
    policy = {
        "sourceControl": {
            "provider": "github",
            "releaseBranch": "main",
            "repository": "Cuna-Labs/cuna-lib-py",
            "repositoryUri": "https://github.com/Cuna-Labs/cuna-lib-py",
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
            "repository": "Runa-Laboratories/runa-release-authority",
            "ref": "main",
            "retrievalUriPrefix": (
                "https://github.com/Runa-Laboratories/runa-release-authority/releases/download"
            ),
            "workflow": ".github/workflows/release-authority.yml",
        },
        "schemaVersion": 1,
        "status": "accepted",
    }
    trust_path = tmp_path / "trust.json"
    trust_path.write_text(json.dumps(trust), encoding="utf-8")
    artifacts = [
        {"filename": "cuna_sdk-0.1.0-py3-none-any.whl", "sha256": "1" * 64},
        {"filename": "cuna_sdk-0.1.0.tar.gz", "sha256": "2" * 64},
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
        "retrievalUri": (
            "https://github.com/Runa-Laboratories/runa-release-authority/releases/download/"
            "authority-run-123-1/approval-receipt.json"
        ),
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
    migrated_trust = copy.deepcopy(trust)
    migrated_trust["schemaVersion"] = 2
    migrated_trust["authority"]["repository"] = "Cuna-Labs/cuna-release-authority"  # type: ignore[index]
    migrated_trust["authority"]["retrievalUriPrefix"] = (  # type: ignore[index]
        "https://github.com/Cuna-Labs/cuna-release-authority/releases/download"
    )
    migrated_trust["legacyReceiptRetrievalUriPrefixes"] = [
        "https://github.com/Runa-Laboratories/runa-release-authority/releases/download"
    ]
    trust_path.write_text(json.dumps(migrated_trust), encoding="utf-8")
    assert (
        verify_provider_receipt(
            receipt_path,
            signature_path,
            trust_path,
            core_digest="3" * 64,
            artifacts=artifacts,
            now=datetime(2026, 8, 2, 18, tzinfo=timezone.utc),
        )["receiptId"]
        == "receipt-123"
    )
    for field, value in (
        ("decision", "reject"),
        ("coreDigest", "4" * 64),
        ("revoked", True),
        ("approverRole", "caller"),
        (
            "retrievalUri",
            "https://github.com/Runa-Laboratories/runa-release-authority/actions/runs/123",
        ),
        (
            "retrievalUri",
            "https://github.com/Runa-Laboratories/runa-release-authority/releases/"
            "download-evil/authority-run-123-1/approval-receipt.json",
        ),
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
    policy = json.loads(Path(".cuna/release-policy.json").read_text(encoding="utf-8"))
    tools = json.loads(Path(".cuna/supply-chain-tools.json").read_text(encoding="utf-8"))
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
    assert "static-security.yml" in validated


@pytest.mark.hermetic
def test_every_checkout_is_credentialless_and_recursive_and_contract_uses_node_24() -> None:
    workflow_root = Path(__file__).parents[1] / ".github/workflows"
    yaml = YAML(typ="safe", pure=True)
    yaml.version = (1, 2)
    checkout_count = 0
    for path in workflow_root.glob("*.yml"):
        document = yaml.load(path.read_text(encoding="utf-8"))
        for job in document["jobs"].values():
            for step in job.get("steps", []):
                if str(step.get("uses", "")).startswith("actions/checkout@"):
                    checkout_count += 1
                    assert step.get("with", {}).get("persist-credentials") is False
                    assert step.get("with", {}).get("submodules") == "recursive"
    assert checkout_count == 16

    codeql_text = (workflow_root / "codeql.yml").read_text(encoding="utf-8")
    codeql = yaml.load(codeql_text)
    assert codeql["permissions"] == {
        "actions": "read",
        "contents": "read",
        "security-events": "write",
    }
    assert "github/codeql-action/init@03e4368ac7daa2bd82b3e85262f3bf87ee112f57" in codeql_text
    assert "github/codeql-action/analyze@03e4368ac7daa2bd82b3e85262f3bf87ee112f57" in codeql_text
    assert "config-file:" not in codeql_text

    static_security_path = workflow_root / "static-security.yml"
    static_security_text = static_security_path.read_text(encoding="utf-8")
    static_security = yaml.load(static_security_text)
    assert static_security["permissions"] == {"contents": "read"}
    assert static_security["jobs"]["analyze"]["name"] == "static-security"
    assert "github/codeql-action" not in static_security_text
    assert "semgrep" not in static_security_text.lower()
    assert (
        "semgrep"
        not in (workflow_root.parents[1] / "pyproject.toml").read_text(encoding="utf-8").lower()
    )
    assert "python -m uv run --locked ruff check --select S" in static_security_text
    assert "python -m uv run --locked pip-audit" in static_security_text
    assert "python tools/safety_scan.py" in static_security_text

    quality = (workflow_root / "quality.yml").read_text(encoding="utf-8")
    assert "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020" in quality
    assert "node-version: 24.4.1" in quality
    assert "cache-dependency-path: contracts/package-lock.json" in quality
    assert "python tools/contract_gate.py" in quality
    assert "python -m uv run --locked pytest -q --cov=cuna --cov-report=term-missing" in quality
    assert (
        "python -m uv run --locked python tools/surface_snapshot.py "
        "dist/*.whl .cuna/public-surface.json --check"
    ) in quality
    assert (
        "python -m uv run --locked python tools/generate_api_reference.py "
        "dist/*.whl --report api-reference-gate.json"
    ) in quality
    assert "mkdir -p candidate-staging" in quality
    assert (
        "cp dist/*.whl dist/*.tar.gz contract-gate.json api-reference-gate.json candidate-staging/"
    ) in quality
    assert "path: candidate-staging/*" in quality
    assert "            dist/*" not in quality
    locked_harness = (
        "python -m uv export --locked --only-group dev --no-emit-project "
        '--output-file "${RUNNER_TEMP}/dev-requirements.txt"'
    )
    locked_install = (
        'python -m pip install --require-hashes -r "${RUNNER_TEMP}/dev-requirements.txt"'
    )
    assert quality.count(locked_harness) == 2
    assert quality.count(locked_install) == 2
    assert quality.count("python -m pip install uv==0.11.31") == 3
    assert (
        quality.count(
            "python -m uv export --locked --no-dev --no-emit-project "
            '--output-file "${RUNNER_TEMP}/runtime-requirements.txt"'
        )
        == 1
    )
    assert (
        quality.count(
            'python -m pip install --require-hashes -r "${RUNNER_TEMP}/runtime-requirements.txt"'
        )
        == 1
    )
    httpx_job = quality[quality.index("  httpx-compatibility:") : quality.index("  admission:")]
    assert httpx_job.index(locked_install) < httpx_job.index('"httpx==${{ matrix.httpx }}"')
    assert "runtime-requirements.txt" not in httpx_job


@pytest.mark.hermetic
def test_repository_approval_trust_is_bound_to_the_release_authority_key() -> None:
    root = Path(__file__).parents[1]
    trust = json.loads((root / ".cuna/approval-trust.json").read_text(encoding="utf-8"))
    authority = trust["authority"]
    public_key = root / ".cuna" / authority["publicKeyPath"]
    assert trust["status"] == "accepted"
    assert trust["schemaVersion"] == 2
    assert authority["repository"] == "Cuna-Labs/cuna-release-authority"
    assert authority["workflow"] == ".github/workflows/release-authority.yml"
    assert authority["providerId"] == "runa-release-authority-2026-08-02-v1"
    assert authority["artifactName"] == "runa-python-release-approval"
    assert authority["retrievalUriPrefix"] == (
        "https://github.com/Cuna-Labs/cuna-release-authority/releases/download"
    )
    assert trust["legacyReceiptRetrievalUriPrefixes"] == [
        "https://github.com/Runa-Laboratories/runa-release-authority/releases/download"
    ]
    assert hashlib.sha256(public_key.read_bytes()).hexdigest() == authority["publicKeySha256"]


@pytest.mark.hermetic
def test_safety_scanner_runs_before_runtime_dependencies_are_installed(tmp_path) -> None:
    root = Path(__file__).parents[1]
    command = [sys.executable, "-I", "-S", str(root / "tools/safety_scan.py")]
    completed = subprocess.run(  # noqa: S603 -- fixed interpreter and repository-owned scanner
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == '{"requirement":"R-085-01","verdict":"pass"}'

    for name in ("README.md", "CONTRIBUTING.md", "SECURITY.md"):
        (tmp_path / name).write_text("safe", encoding="utf-8")
    for name in ("src", "docs", "examples"):
        (tmp_path / name).mkdir()
    (tmp_path / "docs/leak.md").write_text("runa_sk_abcdefgh", encoding="utf-8")
    blocked = subprocess.run(  # noqa: S603 -- fixed interpreter and repository-owned scanner
        command,
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode != 0
    assert "safe-content violation usable-api-key at docs/leak.md" in blocked.stderr


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
    wheel = tmp_path / "cuna_sdk-0.1.0-py3-none-any.whl"
    surface = tmp_path / "public-surface.json"
    wheel.write_bytes(b"wheel")
    surface.write_text('{"root":[],"symbols":{}}\n', encoding="utf-8")
    receipt = tmp_path / ".public-surface-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "artifactSha256": hashlib.sha256(b"wheel").hexdigest(),
                "schemaVersion": 1,
                "surfaceSha256": hashlib.sha256(surface.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    assert public_surface_matches(wheel, surface)
    wheel.write_bytes(b"substituted")
    assert not public_surface_matches(wheel, surface)
    wheel.write_bytes(b"wheel")
    surface.write_text(
        '{"root":["hostile"],"symbols":{}}\n',
        encoding="utf-8",
    )
    assert not public_surface_matches(wheel, surface)


@pytest.mark.hermetic
def test_local_candidate_manifest_is_explicitly_unattested_and_digest_bound(tmp_path) -> None:
    (tmp_path / "cuna_sdk-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (tmp_path / "cuna_sdk-0.1.0.tar.gz").write_bytes(b"sdist")
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
                    "https://github.com/Cuna-Labs/cuna-lib-py/.github/workflows/"
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
def test_performance_gate_accepts_only_exact_current_or_legacy_authority() -> None:
    legacy = passing_budget()
    legacy["baseline"]["authority"]["certificateIdentity"] = (  # type: ignore[index]
        "https://github.com/Runa-Laboratories/runa-lib-py/.github/workflows/"
        "performance-baseline.yml@refs/heads/main"
    )
    assert evaluate_budget(legacy, 1_048_576)
    untrusted = passing_budget()
    untrusted["baseline"]["authority"]["certificateIdentity"] = (  # type: ignore[index]
        "https://github.com/attacker/cuna-lib-py/.github/workflows/"
        "performance-baseline.yml@refs/heads/main"
    )
    assert not evaluate_budget(untrusted, 1_048_576)


@pytest.mark.hermetic
def test_performance_gate_rejects_unledgered_direct_dependency() -> None:
    mutated = passing_budget()
    mutated["dependencyClosure"] = [
        {"name": "new-runtime", "path": "cuna-sdk -> new-runtime", "role": "direct"}
    ]
    assert not evaluate_budget(mutated, 1_048_576)


@pytest.mark.hermetic
def test_release_policy_is_reachable_and_rejects_self_dependency() -> None:
    policy = {
        "sourceControl": {
            "branchProtection": {
                "requiredStatusChecks": [
                    "CodeQL",
                    "py-quality-gates",
                    "release-admission",
                    "static-security",
                ]
            },
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
        ("cuna_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("cuna_sdk-0.1.0.tar.gz", b"sdist"),
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
    (retrieved / "cuna_sdk-0.1.0.tar.gz").write_bytes(b"substituted")
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
        ("cuna_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("cuna_sdk-0.1.0.tar.gz", b"sdist"),
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
        ("cuna_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("cuna_sdk-0.1.0.tar.gz", b"sdist"),
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
        ("cuna_sdk-0.1.0-py3-none-any.whl", b"wheel"),
        ("cuna_sdk-0.1.0.tar.gz", b"sdist"),
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
    assert AUTHORITY_REPOSITORY == "Cuna-Labs/cuna-release-authority"
    assert AUTHORITY_WORKFLOW == "release-authority.yml"
    assert CERTIFICATE_IDENTITY == (
        "https://github.com/Cuna-Labs/cuna-release-authority/.github/workflows/"
        "release-authority.yml@refs/heads/main"
    )
    assert AUTHORITY_EVIDENCE_IDENTITIES == {
        CERTIFICATE_IDENTITY: "Cuna-Labs/cuna-release-authority",
        (
            "https://github.com/Runa-Laboratories/runa-release-authority/"
            ".github/workflows/release-authority.yml@refs/heads/main"
        ): "Runa-Laboratories/runa-release-authority",
    }
    assert set(PERFORMANCE_EVIDENCE_IDENTITIES.values()) == {
        "Cuna-Labs/cuna-lib-py",
        "Runa-Laboratories/runa-lib-py",
    }
    source = (Path(__file__).parents[1] / "tools/inherited_evidence_gate.py").read_text(
        encoding="utf-8"
    )
    workflow = (Path(__file__).parents[1] / ".github/workflows/release-evidence.yml").read_text(
        encoding="utf-8"
    )
    assert "PromptExecution" not in source
    assert "Runta" not in source
    inherited_admission = (
        "python -m uv run --locked python tools/admission_manifest.py "
        "--receipts handoff/receipts --artifacts handoff/candidate "
        "--inherited-evidence inherited-evidence"
    )
    assert inherited_admission in workflow
    assert "run: python tools/admission_manifest.py --receipts handoff/receipts" not in workflow


@pytest.mark.hermetic
def test_inherited_evidence_is_signed_content_verified_and_candidate_bound(tmp_path) -> None:
    source = "a" * 40
    authority_head = "b" * 40
    artifacts = [
        {"filename": "cuna_sdk-0.1.0-py3-none-any.whl", "sha256": "1" * 64},
        {"filename": "cuna_sdk-0.1.0.tar.gz", "sha256": "2" * 64},
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
                        "id": "https://github.com/Cuna-Labs/cuna-release-authority/actions"
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

    def rewrite_provenance_builder(document: dict[str, object], repository: str) -> None:
        files = document["evidence"]["provenance"]["files"]  # type: ignore[index]
        for item in files:  # type: ignore[union-attr]
            path = tmp_path / item["path"]
            envelope = json.loads(path.read_text(encoding="utf-8"))
            payload = json.loads(base64.b64decode(envelope["payload"], validate=True))
            payload["predicate"]["runDetails"]["builder"]["id"] = (
                f"https://github.com/{repository}/actions"
            )
            envelope["payload"] = base64.b64encode(
                json.dumps(payload, sort_keys=True).encode()
            ).decode()
            path.write_text(
                json.dumps(envelope, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    legacy_statement = copy.deepcopy(statement)
    legacy_statement["certificateIdentity"] = (
        "https://github.com/Runa-Laboratories/runa-release-authority/"
        ".github/workflows/release-authority.yml@refs/heads/main"
    )
    rewrite_provenance_builder(legacy_statement, "Runa-Laboratories/runa-release-authority")
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(legacy_statement, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    assert (
        validate_inherited_evidence(
            tmp_path,
            source,
            authority_head,
            artifacts,
            signature_verifier=lambda statement, bundle, digest: True,
        )["authorityHeadSha"]
        == authority_head
    )

    rewrite_provenance_builder(statement, "Cuna-Labs/cuna-release-authority")
    untrusted_statement = copy.deepcopy(statement)
    untrusted_statement["certificateIdentity"] = (
        "https://github.com/attacker/cuna-release-authority/"
        ".github/workflows/release-authority.yml@refs/heads/main"
    )
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(untrusted_statement, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="inherited-evidence-authority-invalid"):
        validate_inherited_evidence(
            tmp_path,
            source,
            authority_head,
            artifacts,
            signature_verifier=lambda statement, bundle, digest: True,
        )
    (tmp_path / "inherited-evidence.json").write_text(
        json.dumps(statement, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )

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


# The run's authority, written as literals. These are deliberately not read from
# PERFORMANCE_EVIDENCE_IDENTITIES: a mutation that reorders or rewrites that map
# must break these tests instead of travelling into their expectations.
CUNA_BASELINE_IDENTITY = (
    "https://github.com/Cuna-Labs/cuna-lib-py/"
    ".github/workflows/performance-baseline.yml@refs/heads/main"
)
LEGACY_BASELINE_IDENTITY = (
    "https://github.com/Runa-Laboratories/runa-lib-py/"
    ".github/workflows/performance-baseline.yml@refs/heads/main"
)
UNTRUSTED_BASELINE_IDENTITY = (
    "https://github.com/attacker/cuna-lib-py/"
    ".github/workflows/performance-baseline.yml@refs/heads/main"
)
BASELINE_CELLS = tuple(
    f"baseline-{python}-{form}-{mode}.json"
    for python in ("3.10", "3.11", "3.12", "3.13", "3.14")
    for form in ("wheel", "sdist")
    for mode in ("sync", "async")
)


def _write_baseline_set(
    root: Path, identity: str, *, overrides: dict[str, str] | None = None
) -> str:
    """Write a complete accepted 20-cell baseline set and return its source sha."""

    source = "a" * 40
    entries: list[dict[str, str]] = []
    for name in BASELINE_CELLS:
        path = root / name
        path.write_text(
            json.dumps(
                {
                    "approvalReference": "https://github.com/Cuna-Labs/cuna-lib-py/actions/runs/1",
                    "authority": {
                        "certificateIdentity": (overrides or {}).get(name, identity),
                        "issuer": "https://token.actions.githubusercontent.com",
                    },
                    "metrics": {"importMillisecondsP95": 1},
                    "status": "accepted",
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        entries.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (root / "baseline-index.json").write_text(
        json.dumps(
            {"baselines": entries, "schemaVersion": 1, "source": source},
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    (root / "baseline-index.sigstore.json").write_text("{}", encoding="utf-8")
    return source


def _record_sigstore(monkeypatch, *, verdict: bool = True) -> list[dict[str, str]]:
    """Replace the signature check and record the authority it was handed."""

    calls: list[dict[str, str]] = []

    def fake_verify(statement, bundle, digest, *, workflow_name, repository):
        calls.append({"digest": digest, "repository": repository, "workflow": workflow_name})
        return verdict

    monkeypatch.setattr(performance_baseline_gate, "verify_sigstore", fake_verify)
    return calls


@pytest.mark.hermetic
def test_performance_baseline_matrix_is_the_twenty_named_cells() -> None:
    assert len(BASELINE_CELLS) == 20
    assert BASELINE_CELLS[0] == "baseline-3.10-wheel-sync.json"
    assert "baseline-3.14-sdist-async.json" in BASELINE_CELLS


@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("expected_repository", "identity"),
    [
        ("Cuna-Labs/cuna-lib-py", CUNA_BASELINE_IDENTITY),
        ("Runa-Laboratories/runa-lib-py", LEGACY_BASELINE_IDENTITY),
    ],
)
def test_performance_baseline_verifies_against_the_repository_the_run_pinned(
    tmp_path, monkeypatch, expected_repository: str, identity: str
) -> None:
    calls = _record_sigstore(monkeypatch)
    source = _write_baseline_set(tmp_path, identity)
    assert validate_baselines(tmp_path, expected_repository=expected_repository) is None
    assert calls == [
        {
            "digest": source,
            "repository": expected_repository,
            "workflow": "performance-baseline.yml",
        }
    ]


@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("expected_repository", "claimed_identity"),
    [
        ("Cuna-Labs/cuna-lib-py", LEGACY_BASELINE_IDENTITY),
        ("Runa-Laboratories/runa-lib-py", CUNA_BASELINE_IDENTITY),
    ],
)
def test_performance_baseline_document_cannot_choose_its_own_verifier(
    tmp_path, monkeypatch, expected_repository: str, claimed_identity: str
) -> None:
    calls = _record_sigstore(monkeypatch)
    _write_baseline_set(tmp_path, claimed_identity)
    assert (
        validate_baselines(tmp_path, expected_repository=expected_repository)
        == "baseline-authority-unexpected"
    )
    assert calls == []


@pytest.mark.hermetic
def test_performance_baseline_rejects_untrusted_unknown_and_mixed_authority(
    tmp_path, monkeypatch
) -> None:
    calls = _record_sigstore(monkeypatch)
    assert DEFAULT_EXPECTED_REPOSITORY == "Cuna-Labs/cuna-lib-py"

    _write_baseline_set(tmp_path, UNTRUSTED_BASELINE_IDENTITY)
    assert validate_baselines(tmp_path) == "baseline-not-accepted"

    source = _write_baseline_set(tmp_path, LEGACY_BASELINE_IDENTITY)
    assert validate_baselines(tmp_path) == "baseline-authority-unexpected"
    assert (
        validate_baselines(tmp_path, expected_repository="attacker/cuna-lib-py")
        == "baseline-expected-repository-unknown"
    )
    assert validate_baselines(tmp_path, expected_repository="Runa-Laboratories/runa-lib-py") is None

    _write_baseline_set(
        tmp_path,
        CUNA_BASELINE_IDENTITY,
        overrides={"baseline-3.12-sdist-async.json": LEGACY_BASELINE_IDENTITY},
    )
    assert validate_baselines(tmp_path) == "baseline-authority-unexpected"

    assert calls == [
        {
            "digest": source,
            "repository": "Runa-Laboratories/runa-lib-py",
            "workflow": "performance-baseline.yml",
        }
    ]


@pytest.mark.hermetic
def test_repository_control_plane_uses_only_the_cuna_evidence_namespace() -> None:
    root = Path(__file__).parents[1]
    governed = [root / ".github", root / "tools", root / ".cuna"]
    legacy_path_references = []
    for directory in governed:
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".py", ".yml", ".yaml"}:
                text = path.read_text(encoding="utf-8")
                if ".runa/" in text or ".runa\\" in text:
                    legacy_path_references.append(str(path.relative_to(root)))
    assert legacy_path_references == []

    binder = (root / "tools" / "bind_release_evidence.py").read_text(encoding="utf-8")
    assert 'default="CUNA_RELEASE_CONTROL_EVIDENCE"' in binder
    assert "RUNA_RELEASE_CONTROL_EVIDENCE" not in binder

    installed_gate = (root / "tools" / "installed_artifact_gate.py").read_text(encoding="utf-8")
    assert '"cuna_namespace"' in installed_gate
    assert '"legacy_namespace"' not in installed_gate
