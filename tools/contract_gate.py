"""Validate generated contract evidence and fail closed on provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

EXPECTED_OPERATIONS = {
    "me.get": ("GET", "/v1/me", 200),
    "records.list": ("GET", "/v1/records", 200),
    "sessions.checkpoint": ("POST", "/v1/sessions/{id}/checkpoint", 200),
    "sessions.create": ("POST", "/v1/sessions", 201),
    "sessions.delete": ("DELETE", "/v1/sessions/{id}", 200),
    "sessions.exec": ("POST", "/v1/sessions/{id}/exec", 200),
    "sessions.get": ("GET", "/v1/sessions/{id}", 200),
    "sessions.list": ("GET", "/v1/sessions", 200),
    "sessions.open": ("POST", "/v1/sessions/{id}/open", 200),
    "sessions.pause": ("POST", "/v1/sessions/{id}/pause", 200),
    "sessions.resume": ("POST", "/v1/sessions/{id}/resume", 200),
    "sessions.start": ("POST", "/v1/sessions/{id}/start", 200),
    "sessions.stop": ("POST", "/v1/sessions/{id}/stop", 200),
}
EXPECTED_WIRE = {
    "followRedirects": False,
    "maxResponseBytes": 8_388_608,
    "requestAccept": "application/json",
    "requestContentTypeWithBody": "application/json; charset=utf-8",
    "responseEncoding": "utf-8",
    "responseMediaType": "application/json",
    "sdkOperationCount": 13,
}


def validate_snapshot(value: object) -> str | None:
    """Return a stable drift category for a malformed canonical projection."""

    if not isinstance(value, dict) or set(value) != {
        "contractVersion",
        "operations",
        "schemas",
        "wire",
    }:
        return "snapshot-root-shape"
    if value["contractVersion"] != "1.0.0" or value["wire"] != EXPECTED_WIRE:
        return "version-or-wire-drift"
    operations = value["operations"]
    schemas = value["schemas"]
    if not isinstance(operations, dict) or set(operations) != set(EXPECTED_OPERATIONS):
        return "operation-set-drift"
    if not isinstance(schemas, dict):
        return "schema-set-invalid"
    for key, (method, path, status) in EXPECTED_OPERATIONS.items():
        operation = operations[key]
        if not isinstance(operation, dict):
            return "operation-shape-invalid"
        if (
            operation.get("method") != method
            or operation.get("path") != path
            or operation.get("successStatus") != status
            or set(operation) != {"method", "path", "requestBody", "response", "successStatus"}
        ):
            return "operation-semantics-drift"
    required_closed = {
        "CheckpointRequest",
        "Error",
        "ExecRequest",
        "ExecResult",
        "Me",
        "Ok",
        "Record",
        "SdkCreateSession",
        "Session",
    }
    if not required_closed.issubset(schemas):
        return "schema-set-invalid"
    if any(
        cast(dict[str, object], schemas[name]).get("additionalProperties") is not False
        for name in required_closed
    ):
        return "outer-container-open"
    try:
        usage = schemas["Me"]["properties"]["workspace"]["oneOf"][0]["properties"]["usage"]
    except (KeyError, TypeError):
        return "workspace-usage-missing"
    if not isinstance(usage, dict) or usage.get("additionalProperties") is False:
        return "workspace-usage-not-open"
    if schemas.get("Record", {}).get("properties", {}).get("detail") != {}:
        return "record-detail-not-opaque"
    return None


def _emit(category: str, *, requirement: str = "R-056-20") -> int:
    print(
        json.dumps(
            {"category": category, "requirement": requirement, "verdict": "blocked"},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 1


def main() -> int:
    root = Path("contracts")
    required = (
        "runa-sdk-contract.snapshot.schema.json",
        "runa-sdk-contract.snapshot.json",
        "runa-sdk-contract.prd002-projection.json",
        "runa-sdk-contract.prd002-expected-manifest.json",
        "runa-sdk-contract.provenance.json",
    )
    if any(not (root / name).is_file() for name in required):
        return _emit("artifact-missing")
    snapshot = (root / required[1]).read_bytes()
    projection = (root / required[2]).read_bytes()
    provenance = json.loads((root / required[4]).read_text(encoding="utf-8"))
    if snapshot != projection:
        return _emit("projection-drift")
    try:
        parsed = json.loads(snapshot)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _emit("snapshot-invalid-json")
    category = validate_snapshot(parsed)
    if category is not None:
        return _emit(category)
    if provenance.get("snapshot_sha256") != hashlib.sha256(snapshot).hexdigest():
        return _emit("digest-mismatch")
    source = Path(str(provenance.get("source", "")))
    openapi = source.with_name("runa-api.openapi.json")
    if (
        not openapi.is_file()
        or provenance.get("observed_openapi_sha256")
        != hashlib.sha256(openapi.read_bytes()).hexdigest()
    ):
        return _emit("observed-openapi-digest-mismatch")
    generated = Path("src/runa/_internal/contract/generated")
    manifest_path = generated / "manifest.json"
    if not manifest_path.is_file():
        return _emit("generated-manifest-missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("snapshotSha256") != provenance["snapshot_sha256"]:
        return _emit("generated-snapshot-mismatch")
    for item in manifest.get("files", []):
        path = generated / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            return _emit("generated-file-drift")
    if provenance.get("declared_openapi_sha256") != provenance.get("observed_openapi_sha256"):
        return _emit("openapi-declaration-drift")
    if provenance.get("status") != "approved" or provenance.get("approval_reference") is None:
        return _emit("approval-missing")
    print('{"requirement":"R-056-20","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
