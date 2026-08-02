"""Compare semantic SDK contract projections across local language repositories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from _evidence_utils import canonical_json_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import canonical_json_sha256


def canonical_projection(path: Path) -> bytes:
    value = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def compare_shared_oracles(local: Path, peers: list[Path]) -> dict[str, object]:
    expected = canonical_projection(local)
    expected_digest = canonical_json_sha256(json.loads(expected))
    observed: list[dict[str, str]] = []
    for peer in peers:
        actual = canonical_projection(peer)
        digest = canonical_json_sha256(json.loads(actual))
        if actual != expected:
            raise ValueError("shared-contract-semantic-drift")
        observed.append({"path": peer.as_posix(), "sha256": digest})
    return {
        "local": {"path": local.as_posix(), "sha256": expected_digest},
        "peers": observed,
        "scope": "shared-contract-oracle-only",
        "verdict": "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("local", type=Path)
    parser.add_argument("peers", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        report = compare_shared_oracles(args.local, args.peers)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        print('{"category":"shared-contract-semantic-drift","verdict":"blocked"}')
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
