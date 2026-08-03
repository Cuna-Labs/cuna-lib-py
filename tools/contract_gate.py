"""Verify the commit-pinned canonical contract, generated bindings, and attestation chain."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

CANONICAL_CONTRACT_COMMIT = "ffac863592620c6519072e447c6b6073092ea299"
CANONICAL_SNAPSHOT_SHA256 = "a5dd2ebb2c0cc509051774e3d184386cf5d9f845865267d8ba38278cb47ad6a4"
EXPECTED_OPERATIONS = {
    "me.get": ("GET", "/v1/me", 200),
    "records.list": ("GET", "/v1/records", 200),
    "sessions.checkpoint": ("POST", "/v1/sessions/:id/checkpoint", 200),
    "sessions.create": ("POST", "/v1/sessions", 201),
    "sessions.delete": ("DELETE", "/v1/sessions/:id", 200),
    "sessions.exec": ("POST", "/v1/sessions/:id/exec", 200),
    "sessions.get": ("GET", "/v1/sessions/:id", 200),
    "sessions.list": ("GET", "/v1/sessions", 200),
    "sessions.open": ("POST", "/v1/sessions/:id/open", 200),
    "sessions.pause": ("POST", "/v1/sessions/:id/pause", 200),
    "sessions.resume": ("POST", "/v1/sessions/:id/resume", 200),
    "sessions.start": ("POST", "/v1/sessions/:id/start", 200),
    "sessions.stop": ("POST", "/v1/sessions/:id/stop", 200),
}
_DESCRIPTOR_KEYS = {
    "error_facts",
    "http_binding",
    "method",
    "operation_key",
    "path_parameters",
    "path_template",
    "request",
    "source_refs",
    "success",
    "unresolved_refs",
}


def validate_snapshot(value: object) -> str | None:
    """Return a stable category when the canonical binding-complete shape drifts."""

    if not isinstance(value, dict) or value.get("contract_id") != "runa-sdk-contract":
        return "snapshot-root-shape"
    if value.get("snapshot_version") != "1.1.0" or value.get("schema_version") != 1:
        return "snapshot-version-drift"
    operations = value.get("operations")
    if not isinstance(operations, list) or len(operations) != 13:
        return "operation-set-drift"
    observed: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict) or set(operation) != _DESCRIPTOR_KEYS:
            return "operation-shape-invalid"
        key = operation.get("operation_key")
        expected = EXPECTED_OPERATIONS.get(str(key))
        selector = operation.get("success", {}).get("selector")
        if (
            expected is None
            or (operation.get("method"), operation.get("path_template")) != expected[:2]
            or selector != {"kind": "exact", "status": expected[2]}
            or operation.get("http_binding")
            != {
                "accept": "application/json",
                "authorization_scheme": "Bearer",
                "content_type_with_body": "application/json; charset=utf-8",
                "follow_redirects": False,
                "max_response_bytes": 8_388_608,
                "response_encoding": "utf-8",
                "response_media_type": "application/json",
                "source_ref": "PRD-002#6.1.1",
            }
        ):
            return "operation-semantics-drift"
        observed.add(str(key))
    if observed != set(EXPECTED_OPERATIONS):
        return "operation-set-drift"
    return None


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- fixed executables and repository-owned paths
        command, cwd=cwd, capture_output=True, text=True, check=False
    )


def _emit(category: str) -> int:
    print(
        json.dumps(
            {"category": category, "requirement": "R-056-20", "verdict": "blocked"},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 1


def main() -> int:
    contracts = Path("contracts")
    generated = Path("src/runa/_internal/contract/generated")
    node = shutil.which("node")
    git = shutil.which("git")
    if node is None or git is None:
        return _emit("canonical-verifier-runtime-missing")
    node_version = _run([node, "--version"])
    if node_version.returncode != 0 or not node_version.stdout.startswith("v24."):
        return _emit("canonical-node-version-mismatch")
    gitlink = _run([git, "ls-files", "--stage", "--", "contracts"])
    if gitlink.returncode != 0 or gitlink.stdout.split()[:2] != [
        "160000",
        CANONICAL_CONTRACT_COMMIT,
    ]:
        return _emit("canonical-gitlink-mismatch")
    head = _run([git, "rev-parse", "HEAD"], cwd=contracts)
    dirty = _run([git, "status", "--porcelain"], cwd=contracts)
    if head.stdout.strip() != CANONICAL_CONTRACT_COMMIT or dirty.stdout.strip():
        return _emit("canonical-checkout-mismatch")
    verified = _run([node, "tools/verify-contract.mjs"], cwd=contracts)
    if verified.returncode != 0:
        return _emit("canonical-currentness-failed")
    snapshot_path = contracts / "runa-sdk-contract.snapshot.json"
    snapshot_bytes = snapshot_path.read_bytes()
    if hashlib.sha256(snapshot_bytes).hexdigest() != CANONICAL_SNAPSHOT_SHA256:
        return _emit("snapshot-digest-mismatch")
    snapshot = json.loads(snapshot_bytes)
    category = validate_snapshot(snapshot)
    if category is not None:
        return _emit(category)
    provenance = json.loads(
        (contracts / "runa-sdk-contract.provenance.json").read_text(encoding="utf-8")
    )
    if (
        provenance.get("status") != "APPROVED"
        or provenance.get("approval_reference") is None
        or provenance.get("artifacts", {}).get("snapshot", {}).get("sha256")
        != CANONICAL_SNAPSHOT_SHA256
    ):
        return _emit("canonical-approval-missing")
    manifest_path = generated / "generated-manifest.json"
    if not manifest_path.is_file():
        return _emit("generated-manifest-missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_generator = {
        "path": provenance["generator_identity"]["path"],
        "sha256": provenance["generator_identity"]["sha256"],
        "version": provenance["generator_identity"]["version"],
    }
    if (
        manifest.get("language") != "python"
        or manifest.get("snapshot", {}).get("sha256") != CANONICAL_SNAPSHOT_SHA256
        or manifest.get("generator") != expected_generator
    ):
        return _emit("generated-generator-mismatch")
    expected_files = {item["path"]: item for item in manifest.get("files", [])}
    actual_files = {path.name for path in generated.iterdir() if path.is_file()}
    if actual_files != set(expected_files) | {"generated-manifest.json"}:
        return _emit("generated-file-set-drift")
    for name, item in expected_files.items():
        path = generated / name
        if (
            path.stat().st_size != item["bytes"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            return _emit("generated-file-drift")
    with tempfile.TemporaryDirectory(prefix="runa-canonical-contract-") as temporary:
        clean = Path(temporary) / "src" / "runa" / "_internal" / "contract" / "generated"
        regenerated = _run(
            [
                node,
                str((contracts / "tools/runa-contract-generator.mjs").resolve()),
                "--language",
                "python",
                "--output",
                str(clean),
            ]
        )
        if regenerated.returncode != 0:
            return _emit("canonical-regeneration-failed")
        for path in generated.iterdir():
            peer = clean / path.name
            if path.is_file() and (not peer.is_file() or path.read_bytes() != peer.read_bytes()):
                return _emit("canonical-regeneration-drift")
        attestation = Path(temporary) / "python-contract-attestation.json"
        emitted = _run(
            [
                node,
                str((contracts / "tools/emit-release-attestation.mjs").resolve()),
                "--language",
                "python",
                "--generated-root",
                str(clean),
                "--source-revision",
                str(provenance["source_revision"]),
                "--output",
                str(attestation),
            ]
        )
        if emitted.returncode != 0:
            return _emit("contract-attestation-failed")
        record = json.loads(attestation.read_text(encoding="utf-8"))
        if (
            record.get("status") != "PASS"
            or record.get("digests", {}).get("snapshot") != CANONICAL_SNAPSHOT_SHA256
        ):
            return _emit("contract-attestation-invalid")
    print(
        json.dumps(
            {
                "contractCommit": CANONICAL_CONTRACT_COMMIT,
                "requirement": "R-056-20",
                "snapshotSha256": CANONICAL_SNAPSHOT_SHA256,
                "verdict": "pass",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
