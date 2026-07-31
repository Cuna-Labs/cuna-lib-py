"""Deterministically generate the private Python binding from the local projection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def exact_schema(value: object) -> object:
    if isinstance(value, dict):
        return {
            "additionalProperties": False,
            "properties": {key: exact_schema(item) for key, item in sorted(value.items())},
            "required": sorted(value),
            "type": "object",
        }
    if isinstance(value, list):
        return {
            "items": False,
            "maxItems": len(value),
            "minItems": len(value),
            "prefixItems": [exact_schema(item) for item in value],
            "type": "array",
        }
    return {"const": value}


def component_name(descriptor: object) -> str | None:
    if not isinstance(descriptor, dict):
        return None
    if "$ref" in descriptor:
        return str(descriptor["$ref"]).rsplit("/", 1)[-1]
    content = descriptor.get("content")
    if isinstance(content, dict):
        media = content.get("application/json")
        if isinstance(media, dict):
            schema = media.get("schema")
            if isinstance(schema, dict) and schema.get("type") == "array":
                return component_name(schema.get("items"))
            return component_name(schema)
    return None


def fields(projection: dict[str, object], component: str | None) -> tuple[str, ...]:
    schemas = projection["schemas"]
    if not isinstance(schemas, dict) or component not in schemas:
        return ()
    schema = schemas[component]
    if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
        return ()
    return tuple(sorted(schema["properties"]))


def render_registry(projection: dict[str, object], snapshot_digest: str) -> bytes:
    operations = projection["operations"]
    if not isinstance(operations, dict):
        raise ValueError("operations must be an object")
    lines = [
        "# runa-contract-id: runa-sdk-contract",
        f"# runa-snapshot-version: {projection['contractVersion']}",
        f"# runa-snapshot-sha256: {snapshot_digest}",
        "# runa-generator-version: python-1",
        "# runa-snapshot-path: contracts/runa-sdk-contract.snapshot.json",
        '"""Generated private operation registry. Do not edit manually."""',
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True, slots=True)",
        "class Operation:",
        "    key: str",
        "    method: str",
        "    path_template: str",
        "    success_status: int",
        "    request_fields: tuple[str, ...]",
        "    response_fields: tuple[str, ...]",
        "    source_reference: str",
        "",
        "",
        "OPERATIONS: dict[str, Operation] = {",
    ]

    def literal(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    def tuple_lines(values: tuple[str, ...], indent: str) -> list[str]:
        if not values:
            return [f"{indent}(),"]
        body = ", ".join(literal(value) for value in values)
        if len(indent) + len(body) + 4 <= 100:
            suffix = "," if len(values) == 1 else ""
            return [f"{indent}({body}{suffix}),"]
        return [
            f"{indent}(",
            *(f"{indent}    {literal(value)}," for value in values),
            f"{indent}),",
        ]

    for key, raw in sorted(operations.items()):
        if not isinstance(raw, dict):
            raise ValueError("operation descriptor must be an object")
        request_component = component_name(raw.get("requestBody"))
        response_component = component_name(raw.get("response"))
        request_fields = fields(projection, request_component)
        response_fields = fields(projection, response_component)
        lines.extend(
            [
                f"    {literal(key)}: Operation(",
                f"        {literal(key)},",
                f"        {literal(raw['method'])},",
                f"        {literal(raw['path'])},",
                f"        {raw['successStatus']!r},",
                *tuple_lines(request_fields, "        "),
                *tuple_lines(response_fields, "        "),
                (
                    "        "
                    + literal(f"contracts/runa-sdk-contract.snapshot.json#/operations/{key}")
                    + ","
                ),
                "    ),",
            ]
        )
    lines.extend(["}", ""])
    return "\n".join(lines).encode()


def build_outputs(projection_path: Path, contracts: Path, generated: Path) -> dict[Path, bytes]:
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    snapshot = canonical(projection)
    snapshot_digest = hashlib.sha256(snapshot).hexdigest()
    registry = render_registry(projection, snapshot_digest)
    init = (
        b'"""Generator-owned private contract output."""\n\n'
        b"from .registry import OPERATIONS, Operation\n\n"
        b'__all__ = ("OPERATIONS", "Operation")\n'
    )
    generated_manifest = canonical(
        {
            "files": [
                {"path": "__init__.py", "sha256": hashlib.sha256(init).hexdigest()},
                {"path": "registry.py", "sha256": hashlib.sha256(registry).hexdigest()},
            ],
            "generatorVersion": "python-1",
            "snapshotSha256": snapshot_digest,
        }
    )
    expectation = canonical(
        {
            "operations": sorted(projection["operations"]),
            "schemas": sorted(projection["schemas"]),
            "source": "local-infra-projection",
        }
    )
    openapi = projection_path.with_name("runa-api.openapi.json")
    openapi_digest = hashlib.sha256(openapi.read_bytes()).hexdigest()
    declared_digest_path = projection_path.with_name("runa-api.openapi.sha256")
    declared_digest = declared_digest_path.read_text(encoding="utf-8").split()[0]
    provenance = canonical(
        {
            "approval_reference": None,
            "canonical_repository": "Runa-Laboratories/runa-sdk-contract",
            "declared_openapi_sha256": declared_digest,
            "observed_openapi_sha256": openapi_digest,
            "snapshot_sha256": snapshot_digest,
            "source": projection_path.as_posix(),
            "status": "blocked",
        }
    )
    return {
        contracts / "runa-sdk-contract.snapshot.json": snapshot,
        contracts / "runa-sdk-contract.prd002-projection.json": snapshot,
        contracts / "runa-sdk-contract.prd002-expected-manifest.json": expectation,
        contracts / "runa-sdk-contract.snapshot.schema.json": canonical(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                **exact_schema(projection),
            }
        ),
        contracts / "runa-sdk-contract.provenance.json": provenance,
        generated / "__init__.py": init,
        generated / "registry.py": registry,
        generated / "manifest.json": generated_manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("projection", type=Path)
    parser.add_argument("contracts", type=Path, nargs="?", default=Path("contracts"))
    parser.add_argument(
        "--generated",
        type=Path,
        default=Path("src/runa/_internal/contract/generated"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build_outputs(args.projection, args.contracts, args.generated)
    if args.check:
        mismatches = [
            path.as_posix()
            for path, content in outputs.items()
            if not path.is_file() or path.read_bytes() != content
        ]
        if mismatches:
            print(json.dumps({"mismatches": mismatches, "verdict": "blocked"}, sort_keys=True))
            return 1
    else:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    snapshot = outputs[args.contracts / "runa-sdk-contract.snapshot.json"]
    print(
        json.dumps(
            {
                "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
                "verdict": "blocked-provenance",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
