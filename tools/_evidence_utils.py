"""Small deterministic primitives shared by standalone evidence gates."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    """Hash a file without retaining its full contents."""

    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    """Hash the repository's canonical compact JSON representation."""

    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def file_set_sha256(paths: Iterable[Path]) -> str:
    """Hash a named file set without retaining aggregate file contents."""

    value = hashlib.sha256()
    for path in sorted(
        (item for item in paths if item.is_file()),
        key=lambda item: item.as_posix(),
    ):
        value.update(path.as_posix().encode())
        value.update(b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                value.update(chunk)
        value.update(b"\0")
    return value.hexdigest()
