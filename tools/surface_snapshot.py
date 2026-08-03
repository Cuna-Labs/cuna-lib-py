"""Snapshot the installed public surface from an exact candidate wheel."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _evidence_utils import file_sha256

PROBE = r"""
import dataclasses
import enum
import inspect
import json
import runa

symbols = {}
for name in runa.__all__:
    value = getattr(runa, name)
    record = {"kind": type(value).__name__}
    if inspect.isclass(value):
        record["signature"] = str(inspect.signature(value))
        record["members"] = sorted(
            member
            for member, owned in vars(value).items()
            if not member.startswith("_") and (callable(owned) or isinstance(owned, property))
        )
    if dataclasses.is_dataclass(value):
        record["fields"] = [
            {"name": field.name, "annotation": str(field.type)}
            for field in dataclasses.fields(value)
        ]
    if inspect.isclass(value) and issubclass(value, enum.Enum):
        record["values"] = [member.value for member in value]
    symbols[name] = record
print(json.dumps(
    {"root": list(runa.__all__), "symbols": symbols},
    sort_keys=True,
    separators=(",", ":"),
))
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    command = f"import sys;sys.path.insert(0,{str(wheel)!r});exec({PROBE!r})"
    result = subprocess.run(  # noqa: S603 - fixed interpreter probes a validated local wheel
        [sys.executable, "-I", "-c", command],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    snapshot = json.loads(result.stdout)
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            print('{"category":"public-surface-stale","verdict":"blocked"}')
            return 1
        receipt = {
            "artifactSha256": file_sha256(wheel),
            "schemaVersion": 1,
            "surfaceSha256": file_sha256(args.output),
        }
        (wheel.parent / ".public-surface-receipt.json").write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {"artifactSha256": file_sha256(wheel), "verdict": "pass"},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
