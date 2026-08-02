"""Validate exact inherited SBOMs with the pinned CycloneDX CLI and schema set."""

from __future__ import annotations

import argparse
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

EXPECTED_SBOM_POLICY = {
    "format": "CycloneDX 1.6 JSON",
    "schemaPath": ".runa/schemas/cyclonedx-1.6.schema.json",
    "verifier": "cyclonedx-cli validate --input-format json",
}
EXPECTED_TOOL = {
    "asset": "cyclonedx-linux-x64",
    "downloadUrl": (
        "https://github.com/CycloneDX/cyclonedx-cli/releases/download/v0.32.0/cyclonedx-linux-x64"
    ),
    "sha256": "454879e6a4a405c8a13bff49b8982adcb0596f3019b26b0811c66e4d7f0783e1",
    "version": "0.32.0",
}
EXPECTED_SCHEMAS = {
    ".runa/schemas/cyclonedx-1.6.schema.json": (
        "3e92dddbc30cf7f6a02b80f0942b1a4cfd4fb1c26f1dfc4310afa9d613cafb93"
    ),
    ".runa/schemas/jsf-0.82.schema.json": (
        "8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae"
    ),
    ".runa/schemas/spdx.schema.json": (
        "baa9d3bd1ed57b6751b0887edead6b5063ff53ff7429cf85d476c6c94af0166e"
    ),
}


def validate_configuration(policy: object, tools: object) -> None:
    if not isinstance(policy, dict) or policy.get("sbom") != EXPECTED_SBOM_POLICY:
        raise ValueError("sbom-release-policy-mismatch")
    if not isinstance(tools, dict):
        raise ValueError("supply-chain-tool-policy-invalid")
    schema = tools.get("cyclonedxSchema")
    files = schema.get("files") if isinstance(schema, dict) else None
    configured = (
        {item.get("path"): item.get("sha256") for item in files if isinstance(item, dict)}
        if isinstance(files, list)
        else {}
    )
    if (
        tools.get("cyclonedxCli") != EXPECTED_TOOL
        or not isinstance(schema, dict)
        or schema.get("specVersion") != "1.6"
        or configured != EXPECTED_SCHEMAS
    ):
        raise ValueError("supply-chain-tool-policy-invalid")
    for path, digest in EXPECTED_SCHEMAS.items():
        candidate = Path(path)
        if not candidate.is_file() or file_sha256(candidate) != digest:
            raise ValueError("cyclonedx-schema-integrity-invalid")
    root = json.loads(Path(EXPECTED_SBOM_POLICY["schemaPath"]).read_text(encoding="utf-8"))
    if (
        root.get("$id") != "http://cyclonedx.org/schema/bom-1.6.schema.json"
        or root.get("$schema") != "http://json-schema.org/draft-07/schema#"
    ):
        raise ValueError("cyclonedx-schema-identity-invalid")


def validate_sboms(
    root: Path,
    cli: str,
    *,
    runner: Callable[[list[str]], bool] | None = None,
) -> list[dict[str, str]]:
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    tools = json.loads(Path(".runa/supply-chain-tools.json").read_text(encoding="utf-8"))
    validate_configuration(policy, tools)
    statement = json.loads((root / "inherited-evidence.json").read_text(encoding="utf-8"))
    evidence = statement.get("evidence")
    sbom = evidence.get("sbom") if isinstance(evidence, dict) else None
    files = sbom.get("files") if isinstance(sbom, dict) else None
    if not isinstance(files, list) or len(files) != 2:
        raise ValueError("sbom-evidence-set-invalid")

    def execute(command: list[str]) -> bool:
        if runner is not None:
            return runner(command)
        return subprocess.run(command, capture_output=True, check=False).returncode == 0  # noqa: S603

    if not execute([cli, "--version"]):
        raise ValueError("cyclonedx-cli-unavailable")
    results: list[dict[str, str]] = []
    for item in files:
        relative = PurePosixPath(str(item.get("path", ""))) if isinstance(item, dict) else None
        if relative is None or relative.is_absolute() or len(relative.parts) != 1:
            raise ValueError("sbom-evidence-path-invalid")
        path = root / relative.name
        if not path.is_file() or item.get("sha256") != file_sha256(path):
            raise ValueError("sbom-evidence-digest-mismatch")
        document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if (
            document.get("$schema") != "http://cyclonedx.org/schema/bom-1.6.schema.json"
            or document.get("bomFormat") != "CycloneDX"
            or document.get("specVersion") != "1.6"
        ):
            raise ValueError("sbom-schema-identity-mismatch")
        command = [
            cli,
            "validate",
            "--input-format",
            "json",
            "--input-version",
            "v1_6",
            "--input-file",
            str(path),
            "--fail-on-errors",
        ]
        if not execute(command):
            raise ValueError("cyclonedx-cli-validation-failed")
        results.append({"path": path.name, "sha256": file_sha256(path)})
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--cli", default="cyclonedx-cli")
    args = parser.parse_args()
    try:
        results = validate_sboms(args.root, args.cli)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"category": str(error), "verdict": "blocked"}, sort_keys=True))
        return 1
    print(json.dumps({"sboms": results, "verdict": "pass"}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
