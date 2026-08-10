"""Private scalar constraints shared by request and response validation."""

from __future__ import annotations

import re
from typing import Final

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def is_uuid(value: object) -> bool:
    """Return whether *value* is the canonical lowercase UUID wire form."""

    return isinstance(value, str) and UUID_PATTERN.fullmatch(value) is not None


# --- Wire identity brands ---------------------------------------------------
#
# The one place this SDK decides which brand spellings of a wire identity it
# accepts, and the one place it records which spelling it emits. Local
# configuration names are governed here too -- see ``branded_env_names``.
#
# The defect this closes is structural. A namespace is *minted* by the service
# and *accepted* by the client, and every accepting surface used to carry its
# own independently written copy of the minted spelling: one regular expression
# per token grammar, one string literal per protocol, one host pattern per URL.
# The day the producer flips a spelling, all of those independent comparisons
# reject a valid response at the same moment, and a rejected terminal grant or
# open URL is a single-use 60-second capability destroyed, not deferred.
# Deriving them all from ``WIRE_BRANDS`` makes that one edit instead of many.
#
# ``WIRE_BRANDS`` is an ACCEPT list. It may only ever GROW: removing a spelling
# starts rejecting responses that are accepted today, which is exactly the
# failure this exists to prevent.
#
# Accepting is not emitting. The service is the authority on the minted
# spelling; ``EMITTED_TERMINAL_PROTOCOL`` records what this client sends, is
# deliberately one value, and widening the accept sets must never change it.

WIRE_BRANDS: Final[tuple[str, ...]] = ("cuna", "runa")

#: Credential families the product mints, mirroring the CLI namespace authority:
#: sk secret key, at access token, rt refresh token, ct continuation,
#: tc terminal connect, se/sc session credentials, cb browser callback nonce,
#: cr continuation resume handle.
#:
#: This tuple is detector vocabulary, not an accept set. Nothing that accepts a
#: wire value reads it: the runtime validators call ``branded_credential_pattern``
#: with one family at a time, and the only readers of the whole tuple are
#: ``security._CREDENTIAL_FAMILIES`` (a by-value copy, bound by test) and the
#: tests themselves. It may therefore only ever GROW -- a family removed here
#: silently stops being recognised as credential material by the repository
#: scan, while adding one can never narrow what the SDK accepts.
CREDENTIAL_FAMILIES: Final[tuple[str, ...]] = (
    "sk",
    "at",
    "rt",
    "ct",
    "tc",
    "se",
    "sc",
    "cb",
    "cr",
)

#: ``(?:cuna|runa)`` -- the brand alternation, for embedding in a validator.
BRAND_ALTERNATION: Final[str] = "(?:" + "|".join(WIRE_BRANDS) + ")"

#: ``(?:cunacode|runacode)`` -- the second-level label of a runtime zone.
ZONE_ALTERNATION: Final[str] = "(?:" + "|".join(f"{brand}code" for brand in WIRE_BRANDS) + ")"


def branded_protocols(suffix: str) -> frozenset[str]:
    """Return both brand spellings of one dotted protocol identity."""

    return frozenset(f"{brand}.{suffix}" for brand in WIRE_BRANDS)


def branded_credential_prefixes(family: str) -> tuple[str, ...]:
    """Return both brand spellings of one credential prefix, e.g. ``cuna_tc_``."""

    return tuple(f"{brand}_{family}_" for brand in WIRE_BRANDS)


def branded_credential_pattern(family: str, body: str) -> re.Pattern[str]:
    """Return a credential-token grammar accepting both brand spellings."""

    return re.compile(f"^{BRAND_ALTERNATION}_{family}_{body}$")


def branded_env_names(suffix: str) -> tuple[str, ...]:
    """Return every brand spelling of one environment variable, canonical first.

    ``branded_env_names("BASE_URL")`` is ``("CUNA_BASE_URL", "RUNA_BASE_URL")``.

    The order is the tuple order of ``WIRE_BRANDS``, and callers resolve by
    taking the first *present* name. Because ``WIRE_BRANDS`` is append-only, the
    canonical brand stays first no matter how the list grows, so precedence can
    never silently invert.

    Environment variables are not wire identities, but they are the same
    namespace and they fail the same way. ``CUNA_BASE_URL`` was minted by the
    Cuna-branded documentation and accepted nowhere: a user who exported it got
    no error and no warning, only the default origin. Deriving the names here
    means a brand added to ``WIRE_BRANDS`` widens the credential *and* the
    endpoint variable together, instead of one of them being forgotten again.
    """

    return tuple(f"{brand.upper()}_{suffix}" for brand in WIRE_BRANDS)


def branded_zone_pattern(path_and_query: str = "") -> re.Pattern[str]:
    """Return a runtime-zone URL grammar, anchored to exactly one host label."""

    return re.compile(
        r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        rf"\.{ZONE_ALTERNATION}\.cloud{path_and_query}$"
    )


#: The terminal-stream protocol this client sends when it requests a grant. One
#: value, not a set: the service owns the minted spelling and this is not the
#: place to change it.
EMITTED_TERMINAL_PROTOCOL: Final[str] = "runa.terminal.v1"
