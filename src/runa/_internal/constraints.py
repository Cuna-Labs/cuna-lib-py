"""Private scalar constraints shared by request and response validation."""

from __future__ import annotations

import re

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def is_uuid(value: object) -> bool:
    """Return whether *value* is the canonical lowercase UUID wire form."""

    return isinstance(value, str) and UUID_PATTERN.fullmatch(value) is not None
