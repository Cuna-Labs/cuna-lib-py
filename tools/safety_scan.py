"""Scan shipped and consumer-facing text for prohibited retained values."""

from __future__ import annotations

from collections.abc import Callable
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SECURITY_POLICY = REPOSITORY_ROOT / "src/runa/_internal/security.py"


def _load_classifier() -> Callable[[object], str | None]:
    """Load the policy module without executing the runtime package initializer."""

    spec = spec_from_file_location("_runa_safety_policy", SECURITY_POLICY)
    if spec is None or spec.loader is None:
        raise RuntimeError("retained-content-policy-unavailable")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    classifier = getattr(module, "retained_content_category", None)
    if not callable(classifier):
        raise RuntimeError("retained-content-classifier-unavailable")
    return cast(Callable[[object], str | None], classifier)


retained_content_category = _load_classifier()

ROOTS = (Path("src"), Path("docs"), Path("examples"))
FILES = (Path("README.md"), Path("CONTRIBUTING.md"), Path("SECURITY.md"))
TEXT_SUFFIXES = {".md", ".py", ".txt", ".typed"}
GENERATED_CONTRACT_ROOT = Path("src/runa/_internal/contract/generated")


def main() -> int:
    paths = list(FILES)
    for root in ROOTS:
        paths.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in TEXT_SUFFIXES
            and "__pycache__" not in path.parts
            # Canonical byte-exact outputs contain URL regexes such as ``?t=``. Their
            # full file set and digests are independently enforced by contract_gate.
            and GENERATED_CONTRACT_ROOT not in path.parents
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
