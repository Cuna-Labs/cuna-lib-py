"""Emit a normalized, safe admission verdict."""

from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-success", nargs="+", required=True)
    args = parser.parse_args()
    passed = all(value == "success" for value in args.require_success)
    report = {
        "gates": [
            {"gate": f"required-{index}", "verdict": value}
            for index, value in enumerate(args.require_success, 1)
        ],
        "verdict": "pass" if passed else "blocked",
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
