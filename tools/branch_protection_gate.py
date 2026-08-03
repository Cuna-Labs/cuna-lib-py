"""Validate the exact single-author protection contract for Python main."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_CHECKS = ["py-quality-gates", "release-admission"]


def validate_python_protection(value: object) -> dict[str, object]:
    """Return normalized protection evidence or fail closed on any policy drift."""

    if not isinstance(value, dict):
        raise ValueError("branch-protection-invalid")
    checks = value.get("required_status_checks")
    contexts = checks.get("contexts") if isinstance(checks, dict) else None
    reviews = value.get("required_pull_request_reviews")
    if (
        not isinstance(contexts, list)
        or not all(isinstance(item, str) for item in contexts)
        or sorted(contexts) != REQUIRED_CHECKS
        or not isinstance(reviews, dict)
        or type(reviews.get("required_approving_review_count")) is not int
        or reviews["required_approving_review_count"] != 0
        or reviews.get("dismiss_stale_reviews") is not True
        or reviews.get("require_code_owner_reviews") is not False
        or not isinstance(value.get("enforce_admins"), dict)
        or value["enforce_admins"].get("enabled") is not True
        or not isinstance(value.get("allow_force_pushes"), dict)
        or value["allow_force_pushes"].get("enabled") is not False
        or not isinstance(value.get("allow_deletions"), dict)
        or value["allow_deletions"].get("enabled") is not False
    ):
        raise ValueError("branch-protection-invalid")
    return {
        "administratorsEnforced": True,
        "deletionsAllowed": False,
        "dismissStaleReviews": True,
        "forcePushesAllowed": False,
        "pullRequestRequired": True,
        "requiredApprovingReviews": 0,
        "requiredCodeOwnerReviews": False,
        "requiredStatusChecks": REQUIRED_CHECKS,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("protection", type=Path)
    args = parser.parse_args()
    try:
        document: Any = json.loads(args.protection.read_text(encoding="utf-8"))
        result = validate_python_protection(document)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"category": str(error), "verdict": "blocked"}, sort_keys=True))
        return 1
    print(json.dumps({**result, "verdict": "pass"}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
