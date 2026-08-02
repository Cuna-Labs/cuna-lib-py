"""Create a deterministic Python PRD requirement-to-evidence ledger."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from release_readiness import source_digest
except ModuleNotFoundError:
    from tools.release_readiness import source_digest

EVIDENCE = {
    range(55, 86): [
        "src/runa",
        "tests/test_contract_transport.py",
        "tests/test_public_models_errors_config.py",
        "tests/test_resilience_observability_security.py",
        "tests/test_resources_sync_async.py",
    ],
    range(86, 91): ["tests"],
    range(91, 92): ["tools/generate_api_reference.py", "docs/api/README.md"],
    range(92, 93): ["docs/guides", "examples"],
    range(93, 94): ["tools/package_gate.py", "tools/installed_artifact_gate.py"],
    range(94, 95): [".github/workflows/quality.yml"],
    range(95, 96): [
        ".github/workflows/release.yml",
        ".github/workflows/release-evidence.yml",
        ".github/workflows/publication-recovery.yml",
        "tools/release_gate.py",
        "tools/tag_creation_gate.py",
        "tools/tag_handoff.py",
        "tools/pypi_absence_gate.py",
    ],
    range(96, 97): ["tools/installed_artifact_gate.py"],
}
REQUIREMENT_ROW = re.compile(r"^\|\s*(R-\d{3}-\d{2})\s*\|", re.MULTILINE)
ACCEPTANCE_ROW = re.compile(r"^\|\s*(TC-\d{3}-\d{2})\s*\|", re.MULTILINE)


def table_ids(text: str, pattern: re.Pattern[str], number: int) -> list[str]:
    """Extract owned table-row identifiers, excluding prose cross-references."""
    prefix = "R" if pattern is REQUIREMENT_ROW else "TC"
    expected = f"{prefix}-{number:03d}-"
    return sorted({value for value in pattern.findall(text) if value.startswith(expected)})


def status(number: int) -> str:
    if number == 56:
        return "blocked_contract_provenance"
    if number == 91:
        return "blocked_dependency_conflict"
    if number in {95, 96}:
        return "blocked_external_evidence"
    if number >= 92:
        return "implemented_not_release_admitted"
    return "implemented_local_evidence"


def missing_evidence(number: int, family: str) -> list[str]:
    if family == "shared":
        return ["cross-repository acceptance result", "immutable shared provenance"]
    if number == 56:
        return ["canonical shared-contract repository", "approval reference"]
    if number == 91:
        return ["accepted root-error manifest amendment", "candidate-wheel reference result"]
    if number == 94:
        return ["owner-approved runner", "complete CPython 3.10-3.14 CI result"]
    if number == 95:
        return ["signed immutable tag", "external PyPI trusted-publisher record"]
    if number == 96:
        return ["PRD-095 exact-artifact evidence", "complete installed-artifact smoke matrix"]
    return ["immutable candidate-bound acceptance record"]


def local_acceptance_receipts() -> dict[str, dict[str, object]]:
    path = Path(".runa/local-acceptance-receipts.json")
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    digest = source_digest()
    receipts = document.get("receipts") if isinstance(document, dict) else None
    if (
        document.get("schemaVersion") != 1
        or document.get("sourceDigest") != digest
        or not isinstance(receipts, list)
    ):
        return {}
    result: dict[str, dict[str, object]] = {}
    for receipt in receipts:
        if (
            isinstance(receipt, dict)
            and re.fullmatch(r"TC-\d{3}-\d{2}", str(receipt.get("testId", "")))
            and receipt.get("sourceDigest") == digest
            and receipt.get("verdict") == "pass"
            and receipt.get("evidenceClass") == "implemented_local_evidence"
            and isinstance(receipt.get("nodeids"), list)
            and receipt["nodeids"]
        ):
            result[str(receipt["testId"])] = receipt
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prd_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    local_receipts = local_acceptance_receipts()
    entries: list[dict[str, object]] = []
    acceptance: list[dict[str, object]] = []
    roots = (
        (args.prd_root / "shared", "shared")
        if (args.prd_root / "shared").is_dir()
        else (args.prd_root, "python")
    )
    root_pairs = [roots, (args.prd_root / "python", "python")] if roots[1] == "shared" else [roots]
    for root, family in root_pairs:
        for path in sorted(root.glob("PRD-0*.md")):
            match = re.match(r"PRD-(\d{3})-", path.name)
            if match is None:
                continue
            number = int(match.group(1))
            if family == "python" and not 55 <= number <= 96:
                continue
            text = path.read_text(encoding="utf-8")
            requirements = table_ids(text, REQUIREMENT_ROW, number)
            test_cases = table_ids(text, ACCEPTANCE_ROW, number)
            evidence = (
                next(values for numbers, values in EVIDENCE.items() if number in numbers)
                if family == "python"
                else [".runa/contract-decisions.json", ".runa/release-readiness.json"]
            )
            requirement_status = status(number) if family == "python" else "not_run_shared_gate"
            entries.extend(
                {
                    "evidence": evidence,
                    "family": family,
                    "missing_evidence": missing_evidence(number, family),
                    "prd": path.name,
                    "requirement": requirement,
                    "status": requirement_status,
                }
                for requirement in requirements
            )
            for test_case in test_cases:
                receipt = local_receipts.get(test_case)
                acceptance.append(
                    {
                        "acceptance_test": test_case,
                        "evidence": (
                            [".runa/local-acceptance-receipts.json", *receipt["nodeids"]]
                            if receipt is not None
                            else evidence
                        ),
                        "family": family,
                        "missing_evidence": (
                            ["external immutable candidate-bound acceptance record"]
                            if receipt is not None
                            else missing_evidence(number, family)
                        ),
                        "prd": path.name,
                        "status": (
                            "implemented_local_evidence"
                            if receipt is not None
                            else "not_run_exact_acceptance"
                        ),
                    }
                )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {"acceptanceTests": acceptance, "requirements": entries},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
