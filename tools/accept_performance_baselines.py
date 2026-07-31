"""Convert a complete diagnostic matrix into owner-approved baseline records."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256

IDENTITY = (
    "https://github.com/PromptExecution/Runa/.github/workflows/"
    "performance-baseline.yml@refs/heads/main"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("proposals", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--approval-reference", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source) is None:
        raise SystemExit("baseline-source-invalid")
    expected = {
        (python, form, mode)
        for python in ("3.10", "3.11", "3.12", "3.13", "3.14")
        for form in ("wheel", "sdist")
        for mode in ("sync", "async")
    }
    observed: set[tuple[str, str, str]] = set()
    args.output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for path in sorted(args.proposals.rglob("budget-*.json")):
        match = re.fullmatch(r"budget-(3\.\d+)-(wheel|sdist)-(sync|async)\.json", path.name)
        if match is None:
            continue
        cell = (match.group(1), match.group(2), match.group(3))
        report = json.loads(path.read_text(encoding="utf-8"))
        proposal = report.get("baselineProposal")
        if (
            report.get("verdict") != "diagnostic-pass"
            or report.get("source") != args.source
            or not isinstance(proposal, dict)
            or proposal.get("status") != "proposal"
            or report.get("matrixTuple")
            != {
                "artifactForm": cell[1],
                "executionMode": cell[2],
                "operatingSystem": report.get("matrixTuple", {}).get("operatingSystem"),
                "python": cell[0],
            }
        ):
            raise SystemExit("baseline-proposal-invalid")
        baseline = {
            "approvalReference": args.approval_reference,
            "authority": {
                "certificateIdentity": IDENTITY,
                "issuer": "https://token.actions.githubusercontent.com",
            },
            "dependencyClosureDigest": report["dependencyClosureDigest"],
            "matrixTuple": report["matrixTuple"],
            "metrics": proposal["metrics"],
            "profile": report["profile"],
            "referenceArtifactSha256": report["artifactSha256"],
            "status": "accepted",
        }
        target = args.output / f"baseline-{cell[0]}-{cell[1]}-{cell[2]}.json"
        target.write_text(
            json.dumps(baseline, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        paths.append(target)
        observed.add(cell)
    if observed != expected:
        raise SystemExit("baseline-proposal-matrix-incomplete")
    index = {
        "baselines": [
            {"path": path.name, "sha256": file_sha256(path)} for path in sorted(paths)
        ],
        "schemaVersion": 1,
        "source": args.source,
    }
    (args.output / "baseline-index.json").write_text(
        json.dumps(index, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
