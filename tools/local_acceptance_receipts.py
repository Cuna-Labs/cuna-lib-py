"""Run selected exact local acceptance mappings and emit source-bound receipts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    from release_readiness import source_digest
except ModuleNotFoundError:
    from tools.release_readiness import source_digest


MAPPINGS = {
    "TC-001-11": [
        "tests/test_public_models_errors_config.py::test_every_base_url_source_rejects_non_cuna_origin_before_transport_creation",
        "tests/test_resources_sync_async.py::test_sync_client_guard_blocks_mutated_request_before_injected_dispatch",
        "tests/test_resources_sync_async.py::test_async_client_guard_blocks_mutated_request_before_injected_dispatch",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output", type=Path, default=Path(".cuna/local-acceptance-receipts.json"), nargs="?"
    )
    args = parser.parse_args()
    digest = source_digest()
    receipts = []
    for test_id, nodeids in MAPPINGS.items():
        command = [sys.executable, "-m", "pytest", "-q", *nodeids]
        completed = subprocess.run(command, check=False)  # noqa: S603
        if completed.returncode != 0:
            raise SystemExit(f"local-acceptance-failed:{test_id}")
        receipts.append(
            {
                "evidenceClass": "implemented_local_evidence",
                "nodeids": nodeids,
                "sourceDigest": digest,
                "testId": test_id,
                "verdict": "pass",
            }
        )
    document = {"receipts": receipts, "schemaVersion": 1, "sourceDigest": digest}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
