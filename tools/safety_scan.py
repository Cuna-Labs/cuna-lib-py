"""Scan shipped and consumer-facing text for prohibited retained values."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runa._internal.security import retained_content_category

ROOTS = (Path("src"), Path("docs"), Path("examples"))
FILES = (Path("README.md"), Path("CONTRIBUTING.md"), Path("SECURITY.md"))
TEXT_SUFFIXES = {".md", ".py", ".txt", ".typed"}


def main() -> int:
    paths = list(FILES)
    for root in ROOTS:
        paths.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix in TEXT_SUFFIXES and "__pycache__" not in path.parts
        )
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="strict")
        category = retained_content_category(text)
        if category is not None:
            raise SystemExit(f"safe-content violation {category} at {path.as_posix()}")
    print('{"requirement":"R-085-01","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
