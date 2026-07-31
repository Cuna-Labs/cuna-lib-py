"""Verify that governed Python SDK concepts have one intentional owner.

The ledger is a decision record, not evidence by itself.  This gate inspects the
current source tree and rejects semantic-owner drift or undocumented copies.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_LEDGER: Final = Path(".runa/duplicate-abstraction-ledger.json")
_AUDIT: Final = Path(".runa/duplicate-abstraction-audit.json")
_EXPECTED_DECISIONS: Final = {
    "public resource operation mapping": "EXTRACT_SHARED_KERNEL",
    "response sanitization and retained-content policy": "EXTRACT_SHARED_KERNEL",
    "file artifact SHA-256 evidence": "EXTRACT_SHARED_KERNEL",
    "synchronous and asynchronous managers/session handles": "SHARE_TEST_ORACLE_ONLY",
    "synchronous and asynchronous HTTP adapters": "STANDARDIZE_INTERFACE_ONLY",
}
_HASH_EXCEPTIONS: Final = {
    "tools/contract_gate.py",
    "tools/stage_contract_evidence.py",
}


@dataclass(frozen=True, slots=True)
class Finding:
    category: str
    path: str


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _python_files(root: Path, folder: str) -> list[Path]:
    base = root / folder
    return sorted(base.rglob("*.py")) if base.is_dir() else []


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())


def _defined_functions(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _defined_classes(path: Path) -> set[str]:
    return {node.name for node in ast.walk(_tree(path)) if isinstance(node, ast.ClassDef)}


def _hash_call_present(path: Path) -> bool:
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and function.attr == "sha256"
            and isinstance(function.value, ast.Name)
            and function.value.id == "hashlib"
        ):
            return True
        if isinstance(function, ast.Name) and function.id == "sha256":
            return True
    return False


def _ledger_findings(root: Path) -> list[Finding]:
    path = root / _LEDGER
    if not path.is_file():
        return [Finding("ledger_missing", _LEDGER.as_posix())]
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return [Finding("ledger_invalid", _LEDGER.as_posix())]
    candidates = ledger.get("candidates") if isinstance(ledger, dict) else None
    if not isinstance(candidates, list):
        return [Finding("ledger_invalid", _LEDGER.as_posix())]
    observed: dict[str, str] = {}
    findings: list[Finding] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            findings.append(Finding("ledger_candidate_invalid", _LEDGER.as_posix()))
            continue
        concept = candidate.get("concept")
        decision = candidate.get("decision")
        if not isinstance(concept, str) or not isinstance(decision, str) or concept in observed:
            findings.append(Finding("ledger_candidate_invalid", _LEDGER.as_posix()))
            continue
        observed[concept] = decision
        evidence = candidate.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            findings.append(Finding("ledger_evidence_missing", _LEDGER.as_posix()))
            continue
        for item in evidence:
            if not isinstance(item, str):
                findings.append(Finding("ledger_evidence_invalid", _LEDGER.as_posix()))
                continue
            evidence_path = item.split("::", 1)[0]
            if not (root / evidence_path).exists():
                findings.append(Finding("ledger_evidence_missing", evidence_path))
    if observed != _EXPECTED_DECISIONS:
        findings.append(Finding("ledger_decision_set_mismatch", _LEDGER.as_posix()))
    return findings


def evaluate(root: Path) -> dict[str, object]:
    """Return a deterministic, content-derived duplicate-abstraction verdict."""

    root = root.resolve()
    findings = _ledger_findings(root)
    source_files = _python_files(root, "src")
    tool_files = _python_files(root, "tools")

    uuid_owners = [
        _relative(path, root)
        for path in source_files
        if "[0-9a-f]{8}" in path.read_text(encoding="utf-8")
    ]
    if uuid_owners != ["src/runa/_internal/constraints.py"]:
        findings.append(Finding("uuid_owner_drift", ",".join(uuid_owners)))

    security_functions = {
        "contains_denied",
        "normalize_retained_text",
        "retained_content_category",
    }
    security_owners: dict[str, list[str]] = {name: [] for name in security_functions}
    for path in source_files:
        definitions = _defined_functions(path)
        for name in security_functions & definitions:
            security_owners[name].append(_relative(path, root))
    for name, owners in sorted(security_owners.items()):
        if owners != ["src/runa/_internal/security.py"]:
            findings.append(Finding(f"security_owner_drift:{name}", ",".join(owners)))

    hash_owners = [_relative(path, root) for path in tool_files if _hash_call_present(path)]
    unexpected_hashes = sorted(set(hash_owners) - _HASH_EXCEPTIONS - {"tools/_evidence_utils.py"})
    if unexpected_hashes:
        findings.extend(Finding("file_hash_owner_drift", path) for path in unexpected_hashes)
    evidence_utils = root / "tools/_evidence_utils.py"
    if (
        not evidence_utils.is_file()
        or "file_sha256" not in _defined_functions(evidence_utils)
        or not _hash_call_present(evidence_utils)
    ):
        findings.append(Finding("file_hash_owner_missing", "tools/_evidence_utils.py"))

    client_path = root / "src/runa/client.py"
    client_classes = _defined_classes(client_path) if client_path.is_file() else set()
    handle_classes = {
        "AsyncRecordsManager",
        "AsyncRuna",
        "AsyncSession",
        "AsyncSessionsManager",
        "RecordsManager",
        "Runa",
        "Session",
        "SessionsManager",
    }
    if not handle_classes.issubset(client_classes):
        findings.append(Finding("sync_async_handle_pair_incomplete", "src/runa/client.py"))
    parity_test = root / "tests/test_public_models_errors_config.py"
    if (
        not parity_test.is_file()
        or "test_sync_async_public_parameter_parity" not in _defined_functions(parity_test)
    ):
        findings.append(
            Finding(
                "sync_async_parity_oracle_missing",
                "tests/test_public_models_errors_config.py",
            )
        )

    transport_path = root / "src/runa/_internal/transport.py"
    transport_classes = _defined_classes(transport_path) if transport_path.is_file() else set()
    required_transport_types = {
        "AsyncHttpTransport",
        "PreparedRequest",
        "RawResponse",
        "RequestContext",
        "SyncHttpTransport",
    }
    if not required_transport_types.issubset(transport_classes):
        findings.append(
            Finding("transport_interface_incomplete", "src/runa/_internal/transport.py")
        )
    transport_test = root / "tests/test_contract_transport.py"
    if not transport_test.is_file():
        findings.append(Finding("transport_oracle_missing", "tests/test_contract_transport.py"))

    normalized = sorted(
        {(finding.category, finding.path) for finding in findings},
        key=lambda item: (item[0], item[1]),
    )
    return {
        "auditVersion": 2,
        "conceptCount": len(_EXPECTED_DECISIONS),
        "findings": [{"category": category, "path": path} for category, path in normalized],
        "ledger": _LEDGER.as_posix(),
        "verdict": "fail" if normalized else "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.root)
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    output = args.output
    if output is None and args.root.resolve() == Path(".").resolve():
        output = _AUDIT
    if output is not None:
        destination = output if output.is_absolute() else args.root / output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
