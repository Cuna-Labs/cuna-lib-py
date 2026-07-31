"""Scan shipped and consumer-facing text for prohibited retained values."""

from __future__ import annotations

import re
from pathlib import Path

ROOTS = (Path("src"), Path("docs"), Path("examples"))
FILES = (Path("README.md"), Path("CONTRIBUTING.md"), Path("SECURITY.md"))
PROHIBITED_MARKER = bytes((114, 117, 110, 116, 97)).decode()
USABLE_KEY = re.compile(r"runa_sk_[A-Za-z0-9_-]{8,}")


def main() -> int:
    paths = list(FILES)
    for root in ROOTS:
        paths.extend(path for path in root.rglob("*") if path.is_file())
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="strict")
        if PROHIBITED_MARKER in text.casefold() or USABLE_KEY.search(text):
            raise SystemExit(f"safe-content violation category at {path.as_posix()}")
    print('{"requirement":"R-085-01","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
