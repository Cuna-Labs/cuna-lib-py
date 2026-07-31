"""Verify externally signed, candidate-bound inherited release evidence."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256

REQUIRED_EVIDENCE = {
    "prd013Security",
    "prd014Compatibility",
    "prd015Conformance",
    "prd016Quality",
    "prd017Budgets",
    "releaseManifest",
    "sbom",
    "provenance",
}
CERTIFICATE_IDENTITY = (
    "https://github.com/PromptExecution/Runa/.github/workflows/release.yml@refs/heads/main"
)
CERTIFICATE_ISSUER = "https://token.actions.githubusercontent.com"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _safe_file(root: Path, name: object) -> Path:
    if not isinstance(name, str):
        raise ValueError("evidence-path-invalid")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise ValueError("evidence-path-invalid")
    path = root / name
    if not path.is_file():
        raise ValueError("evidence-file-missing")
    return path


def _artifact_map(artifacts: list[dict[str, str]]) -> dict[str, str]:
    result = {item["filename"]: item["sha256"] for item in artifacts}
    invalid_digest = any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in result.values())
    if len(result) != 2 or invalid_digest:
        raise ValueError("candidate-artifacts-invalid")
    return result


def _subjects(payload: dict[str, Any]) -> dict[str, str]:
    return {
        item["name"]: item["digest"]["sha256"]
        for item in payload.get("subject", [])
        if isinstance(item, dict)
        and isinstance(item.get("digest"), dict)
        and isinstance(item.get("name"), str)
        and isinstance(item["digest"].get("sha256"), str)
    }


def _validate_content(
    key: str,
    documents: list[dict[str, Any]],
    artifacts: dict[str, str],
    source: str,
) -> None:
    if key == "sbom":
        observed: dict[str, str] = {}
        for document in documents:
            component = document.get("metadata", {}).get("component", {})
            hashes = component.get("hashes", []) if isinstance(component, dict) else []
            if document.get("bomFormat") != "CycloneDX" or document.get("specVersion") != "1.6":
                raise ValueError("sbom-format-invalid")
            digest = next(
                (item.get("content") for item in hashes if item.get("alg") == "SHA-256"),
                None,
            )
            observed[str(component.get("name"))] = str(digest)
        if observed != artifacts:
            raise ValueError("sbom-candidate-binding-mismatch")
        return
    if key == "provenance":
        observed: dict[str, str] = {}
        for document in documents:
            if document.get("payloadType") != "application/vnd.in-toto+json" or not document.get(
                "signatures"
            ):
                raise ValueError("provenance-envelope-invalid")
            try:
                payload = json.loads(base64.b64decode(document["payload"], validate=True))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError("provenance-payload-invalid") from exc
            observed.update(_subjects(payload))
        if observed != artifacts:
            raise ValueError("provenance-candidate-binding-mismatch")
        return
    if key == "releaseManifest":
        if len(documents) != 1 or documents[0].get("source") != source:
            raise ValueError("release-manifest-source-mismatch")
        listed = {
            item["filename"]: item["sha256"]
            for item in documents[0].get("artifacts", [])
            if isinstance(item, dict) and "filename" in item and "sha256" in item
        }
        if listed != artifacts:
            raise ValueError("release-manifest-candidate-binding-mismatch")
        return
    if len(documents) != 1:
        raise ValueError("gate-report-count-invalid")
    report = documents[0]
    if report.get("verdict") != "pass" or report.get("source") != source:
        raise ValueError("gate-report-blocked")
    listed = {
        item["filename"]: item["sha256"]
        for item in report.get("artifacts", [])
        if isinstance(item, dict) and "filename" in item and "sha256" in item
    }
    if listed != artifacts:
        raise ValueError("gate-report-candidate-binding-mismatch")


def verify_sigstore(statement: Path, bundle: Path, source: str) -> bool:
    command = [
        "python",
        "-m",
        "sigstore",
        "verify",
        "github",
        "--offline",
        "--bundle",
        str(bundle),
        "--repository",
        "PromptExecution/Runa",
        "--sha",
        source,
        "--name",
        "release.yml",
        "--ref",
        "refs/heads/main",
        str(statement),
    ]
    return (
        subprocess.run(  # noqa: S603 -- fixed executable and literal argument vector
            command, check=False, capture_output=True
        ).returncode
        == 0
    )


def validate_inherited_evidence(
    root: Path,
    source: str,
    artifacts: list[dict[str, str]],
    *,
    signature_verifier: Callable[[Path, Path, str], bool] = verify_sigstore,
) -> dict[str, object]:
    """Return normalized inherited evidence, or raise a fail-closed category."""
    if re.fullmatch(r"[0-9a-f]{40}", source) is None:
        raise ValueError("immutable-source-invalid")
    statement = root / "inherited-evidence.json"
    bundle = root / "inherited-evidence.sigstore.json"
    if not statement.is_file() or not bundle.is_file():
        raise ValueError("signed-inherited-evidence-missing")
    if not signature_verifier(statement, bundle, source):
        raise ValueError("inherited-evidence-signature-invalid")
    document = json.loads(statement.read_text(encoding="utf-8"))
    candidate = _artifact_map(artifacts)
    if (
        document.get("schemaVersion") != 1
        or document.get("source") != source
        or document.get("artifacts") != artifacts
        or document.get("certificateIdentity") != CERTIFICATE_IDENTITY
        or document.get("certificateIssuer") != CERTIFICATE_ISSUER
    ):
        raise ValueError("inherited-evidence-candidate-mismatch")
    evidence = document.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != REQUIRED_EVIDENCE:
        raise ValueError("inherited-evidence-set-invalid")
    normalized: dict[str, object] = {}
    for key in sorted(REQUIRED_EVIDENCE):
        entry = evidence[key]
        files = entry.get("files") if isinstance(entry, dict) else None
        if entry.get("verdict") != "pass" or not isinstance(files, list) or not files:
            raise ValueError(f"{key}-blocked")
        documents: list[dict[str, Any]] = []
        digests: list[dict[str, str]] = []
        for item in files:
            path = _safe_file(root, item.get("path") if isinstance(item, dict) else None)
            digest = file_sha256(path)
            if item.get("sha256") != digest:
                raise ValueError(f"{key}-digest-mismatch")
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError(f"{key}-content-invalid")
            documents.append(parsed)
            digests.append({"path": path.name, "sha256": digest})
        expected_count = 2 if key in {"sbom", "provenance"} else 1
        if len(documents) != expected_count:
            raise ValueError(f"{key}-file-count-invalid")
        _validate_content(key, documents, candidate, source)
        normalized[key] = {"files": digests, "verdict": "pass"}
    return {
        "bundleSha256": file_sha256(bundle),
        "evidence": normalized,
        "statementSha256": file_sha256(statement),
        "statementCanonicalSha256": __import__("hashlib").sha256(_canonical(document)).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in args.artifacts.glob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    try:
        result = validate_inherited_evidence(args.root, args.source, artifacts)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"category": str(exc), "verdict": "blocked"}, sort_keys=True))
        return 1
    print(json.dumps({**result, "verdict": "pass"}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
