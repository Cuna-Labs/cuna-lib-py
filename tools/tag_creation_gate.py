"""Fail-closed preflight for the release workflow's tag-creation phase."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import tomllib

try:
    from release_handoff_gate import validate_handoff
except ModuleNotFoundError:
    from tools.release_handoff_gate import validate_handoff


EXPECTED_SOURCE_CONTROL = {
    "provider": "github",
    "releaseBranch": "main",
    "repository": "Runa-Laboratories/runa-lib-py",
    "repositoryUri": "https://github.com/Runa-Laboratories/runa-lib-py",
}
EXPECTED_TAG_SIGNATURE = {
    "certificateIdentity": (
        "https://github.com/Runa-Laboratories/runa-lib-py/.github/workflows/"
        "release.yml@refs/heads/main"
    ),
    "issuer": "https://token.actions.githubusercontent.com",
    "technology": "sigstore-keyless",
}


def validate_tag_candidate(
    tag: str, source: str, policy: object, version: str, *, tag_exists: bool
) -> str | None:
    if re.fullmatch(r"[0-9a-f]{40}", source) is None:
        return "immutable-source-identity-missing"
    if re.fullmatch(r"py-v\d+\.\d+\.\d+", tag) is None or tag != f"py-v{version}":
        return "tag-version-mismatch"
    if tag_exists:
        return "tag-already-exists"
    if not isinstance(policy, dict):
        return "release-policy-invalid"
    source_control = policy.get("sourceControl")
    configured_tag = policy.get("tag")
    if not isinstance(source_control, dict) or any(
        source_control.get(key) != value for key, value in EXPECTED_SOURCE_CONTROL.items()
    ):
        return "release-policy-source-control-mismatch"
    if (
        not isinstance(configured_tag, dict)
        or configured_tag.get("template") != "py-v${version}"
        or configured_tag.get("signature") != EXPECTED_TAG_SIGNATURE
    ):
        return "release-policy-tag-mismatch"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    git = shutil.which("git")
    if git is None:
        category = "git-verifier-missing"
    else:
        head = subprocess.run(
            [git, "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
        exists = subprocess.run(
            [git, "show-ref", "--verify", "--quiet", f"refs/tags/{args.tag}"],
            capture_output=True,
            check=False,
        )
        category = validate_tag_candidate(
            args.tag,
            args.source,
            policy,
            str(project["project"]["version"]),
            tag_exists=exists.returncode == 0,
        )
        if category is None and (head.returncode != 0 or head.stdout.strip() != args.source):
            category = "source-commit-mismatch"
    if category is None:
        category = validate_handoff(args.artifacts, args.source)
    if category is not None:
        print(
            json.dumps(
                {"category": category, "requirement": "R-095-01", "verdict": "blocked"},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print('{"requirement":"R-095-01","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
