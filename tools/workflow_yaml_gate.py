"""Strictly parse every GitHub Actions workflow as YAML 1.2."""

from __future__ import annotations

import json
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


def validate_workflows(root: Path) -> list[str]:
    yaml = YAML(typ="safe", pure=True)
    yaml.version = (1, 2)
    yaml.allow_duplicate_keys = False
    paths = sorted((*root.glob("*.yml"), *root.glob("*.yaml")))
    if not paths:
        raise ValueError("workflow-set-empty")
    validated = []
    for path in paths:
        document = yaml.load(path.read_text(encoding="utf-8"))
        if (
            not isinstance(document, dict)
            or not isinstance(document.get("on"), dict)
            or not isinstance(document.get("jobs"), dict)
            or not document["jobs"]
        ):
            raise ValueError(f"workflow-document-invalid:{path.name}")
        validated.append(path.name)
    return validated


def main() -> int:
    try:
        workflows = validate_workflows(Path(".github/workflows"))
    except (OSError, UnicodeError, ValueError, YAMLError) as error:
        print(json.dumps({"category": str(error), "verdict": "blocked"}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {"count": len(workflows), "verdict": "pass", "workflows": workflows},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
