"""Validate completeness and conservative statuses of the trace ledger."""

from __future__ import annotations

import json
from pathlib import Path

ALLOWED = {
    "blocked_contract_provenance",
    "blocked_dependency_conflict",
    "blocked_external_evidence",
    "implemented_local_evidence",
    "implemented_not_release_admitted",
    "not_run_exact_acceptance",
    "not_run_shared_gate",
}


def main() -> int:
    ledger = json.loads(Path(".runa/requirement-evidence.json").read_text(encoding="utf-8"))
    requirements = ledger.get("requirements")
    acceptance = ledger.get("acceptanceTests")
    if not isinstance(requirements, list) or len(requirements) < 1000:
        raise SystemExit("requirement evidence is incomplete")
    if not isinstance(acceptance, list) or len(acceptance) != 558:
        raise SystemExit("acceptance-test evidence is incomplete")
    if any(item.get("status") not in ALLOWED for item in requirements + acceptance):
        raise SystemExit("evidence contains an unapproved verdict")
    print(
        json.dumps(
            {
                "acceptanceTests": len(acceptance),
                "requirements": len(requirements),
                "verdict": "complete-with-explicit-nonpass-states",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
