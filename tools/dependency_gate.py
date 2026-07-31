"""Audit the installed runtime dependency closure and license metadata."""

from __future__ import annotations

import json
from importlib import metadata

from packaging.requirements import Requirement

ALLOWED_LICENSES = {
    "Apache-2.0",
    "BSD-3-Clause",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
}


def normalized(name: str) -> str:
    return name.casefold().replace("_", "-")


def main() -> int:
    pending = ["runa-sdk"]
    seen: set[str] = set()
    closure: list[dict[str, str]] = []
    while pending:
        name = normalized(pending.pop())
        if name in seen:
            continue
        seen.add(name)
        distribution = metadata.distribution(name)
        license_name = distribution.metadata.get("License-Expression")
        if not license_name:
            license_name = distribution.metadata.get("License", "").strip()
        if license_name not in ALLOWED_LICENSES:
            raise SystemExit(f"unapproved license metadata category for {name}")
        closure.append(
            {
                "license": license_name,
                "name": normalized(distribution.metadata["Name"]),
                "version": distribution.version,
            }
        )
        for raw in distribution.requires or ():
            requirement = Requirement(raw)
            if requirement.marker is None or requirement.marker.evaluate():
                pending.append(requirement.name)
    print(
        json.dumps(
            {"runtimeClosure": sorted(closure, key=lambda item: item["name"]), "verdict": "pass"},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
