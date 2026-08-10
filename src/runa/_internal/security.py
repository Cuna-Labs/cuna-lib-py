"""One private disclosure policy for runtime sanitization and repository scans."""

from __future__ import annotations

import json
import re
from urllib.parse import unquote

_DENIED_FRAGMENTS = tuple(
    bytes(values).decode("ascii")
    for values in (
        (114, 117, 110, 116, 97),
        (114, 117, 110, 116, 97, 46, 99, 111, 109),
        (114, 117, 110, 116, 97, 46, 100, 101, 118),
        (114, 117, 110, 116, 105, 109, 101, 95, 105, 100),
        (114, 117, 110, 116, 105, 109, 101, 105, 100),
        (115, 101, 99, 114, 101, 116, 95, 115, 116, 117, 98),
        (115, 101, 99, 114, 101, 116, 115, 116, 117, 98),
        (116, 101, 110, 97, 110, 116, 95, 105, 100),
        (116, 101, 110, 97, 110, 116, 105, 100),
        (116, 101, 110, 97, 110, 116, 95, 99, 114, 101, 100, 101, 110, 116, 105, 97, 108),
        (116, 101, 110, 97, 110, 116, 99, 114, 101, 100, 101, 110, 116, 105, 97, 108),
    )
)
# Every brand and every credential family the product has ever minted. This is
# a denylist, so it may only ever GROW: a name removed from it silently starts
# admitting material that is blocked today.
#
# It was `sk` alone, in two brands. A committed access token, refresh token,
# continuation secret, terminal-connect token, session credential or browser
# callback nonce passed this classifier without a word -- and this classifier is
# not only a repository gate, it is the runtime disclosure policy. The families
# mirror the CLI namespace authority: sk secret key, at access token, rt refresh
# token, ct continuation, tc terminal connect, se/sc session credentials, cb
# browser callback nonce, cr continuation resume handle.
#
# `cr` was the ninth family and nothing detected it. `app-website` mints
# `cuna_cr_<43>` as a bearer capability that keys `localStorage`, names a
# `BroadcastChannel` and rides in a URL fragment; this classifier returned
# `False` for it, as did every other detector the product owns.
#
# These lists are duplicated on purpose. `_internal/constraints.py` owns the same
# two brands and nine families for the wire validators, but this module must
# stay importable *by path alone* -- `tools/safety_scan.py` loads it with
# `spec_from_file_location` so a repository scan never executes the runtime
# package -- so it can hold no relative import. `test_shared_brand_authority_is_
# single_sourced` binds the two lists so they cannot drift apart in silence.
_BRANDS = ("cuna", "runa")
_CREDENTIAL_FAMILIES = ("sk", "at", "rt", "ct", "tc", "se", "sc", "cb", "cr")
_KEY_PREFIXES = tuple(f"{brand}_{family}_" for brand in _BRANDS for family in _CREDENTIAL_FAMILIES)
_BEARER = bytes((97, 117, 116, 104, 111, 114, 105, 122, 97, 116, 105, 111, 110)).decode("ascii")
_PRIVATE_KEY = bytes(
    (
        45,
        45,
        45,
        45,
        45,
        98,
        101,
        103,
        105,
        110,
        32,
        112,
        114,
        105,
        118,
        97,
        116,
        101,
        32,
        107,
        101,
        121,
    )
).decode("ascii")
_USABLE_KEY = re.compile(
    "(?:" + "|".join(re.escape(prefix) for prefix in _KEY_PREFIXES) + r")[A-Za-z0-9_-]{8,}"
)
_AUTHORIZATION = re.compile(re.escape(_BEARER) + r"\s*:\s*bearer\s+\S+", re.IGNORECASE)
_CAPABILITY_URL = re.compile(
    r"https://[^\s?#]+(?:\?[^\s#]*(?:token|secret|key|t)=\S+)", re.IGNORECASE
)


def normalize_retained_text(value: str) -> str:
    """Decode common escaping layers before applying the disclosure policy."""

    decoded = value
    for _ in range(2):
        changed = unquote(decoded)
        if changed == decoded:
            break
        decoded = changed
    try:
        escaped = decoded.replace('"', '\\"')
        decoded = json.loads(f'"{escaped}"')
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return decoded.casefold()


def retained_content_category(value: object) -> str | None:
    """Return the first forbidden retained-content category, recursively."""

    if isinstance(value, str):
        normalized = normalize_retained_text(value)
        if any(fragment in normalized for fragment in _DENIED_FRAGMENTS):
            return "reserved-infrastructure"
        if _USABLE_KEY.search(normalized):
            return "usable-api-key"
        if _AUTHORIZATION.search(normalized):
            return "authorization-header"
        if _PRIVATE_KEY in normalized:
            return "private-key"
        if _CAPABILITY_URL.search(normalized):
            return "capability-url"
        return None
    if isinstance(value, list | tuple):
        for item in value:
            category = retained_content_category(item)
            if category is not None:
                return category
    elif isinstance(value, dict):
        for key, item in value.items():
            category = retained_content_category(key) or retained_content_category(item)
            if category is not None:
                return category
    return None


def contains_denied(value: object) -> bool:
    """Return whether a response value exposes reserved infrastructure metadata.

    Capability values returned by ``sessions.open`` are deliberately deliverable to
    the caller; the broader retained-content policy still forbids persisting them in
    repository artifacts, logs, diagnostics, or traces.
    """

    if isinstance(value, str):
        normalized = normalize_retained_text(value)
        return any(fragment in normalized for fragment in _DENIED_FRAGMENTS)
    if isinstance(value, list | tuple):
        return any(contains_denied(item) for item in value)
    if isinstance(value, dict):
        return any(contains_denied(key) or contains_denied(item) for key, item in value.items())
    return False
