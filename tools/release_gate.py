"""Fail-closed release admission for the fixed Python release identity."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import tomllib

EXPECTED_REPOSITORY = "Runa-Laboratories/runa-lib-py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    if policy["sourceControl"]["repository"] != EXPECTED_REPOSITORY:
        raise SystemExit("R-095-01: safe policy mismatch")
    if re.fullmatch(r"py-v\d+\.\d+\.\d+", args.tag) is None:
        raise SystemExit("R-095-01: safe tag-shape mismatch")
    if args.tag != f"py-v{version}":
        raise SystemExit("R-095-02: safe tag/version mismatch")
    evidence = Path(".runa/external-release-evidence.json")
    if not evidence.is_file():
        print(
            '{"requirement":"R-095-10","verdict":"blocked","category":"external-evidence-missing"}'
        )
        return 1
    print(
        '{"requirement":"R-095-10","verdict":"blocked","category":"external-verification-required"}'
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
