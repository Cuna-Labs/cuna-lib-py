"""Every accepted wire identity must admit both brand spellings.

The failure being prevented is not hypothetical and not deferrable. The service
mints these values; this client compares them. On the day a spelling flips, a
single-brand comparison rejects a valid response -- and a rejected terminal
grant or open URL is a single-use 60-second capability destroyed, not retried.
Widening costs nothing while the old spelling is still minted, so it lands
before the flip, never after.

Every case is stated in all three directions on purpose: the new spelling
accepted, the old one still accepted, a malformed one still rejected. A test
that proved only the first would pass just as well against a validator that
accepts everything.
"""

from __future__ import annotations

import ast
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cuna import Cuna
from cuna._internal import security
from cuna._internal.config import (
    API_KEY_ENV_NAMES,
    BASE_URL_ENV_NAMES,
    DEFAULT_BASE_URL,
    LEGACY_BASE_URL,
    EffectiveConfig,
    SafeConfigFailure,
    resolve_config,
)
from cuna._internal.constraints import (
    CREDENTIAL_FAMILIES,
    EMITTED_TERMINAL_PROTOCOL,
    WIRE_BRANDS,
    branded_credential_prefixes,
    branded_env_names,
)
from cuna._internal.contract import decode_for_operation
from cuna._internal.contract.bridge import DecodeFailure
from cuna.models import TerminalConnectionCreateOptions

from .support import SyncRecorder, json_response, session_payload

REPOSITORY_ROOT = Path(__file__).parents[1]


def _executable_string_constants(path: Path) -> list[str]:
    """Return every string literal a module *evaluates*, docstrings excluded.

    Scanning raw text cannot do this. Prose that names ``CUNA_BASE_URL`` inside
    a docstring is exactly what the fix wants more of; a string constant the
    module evaluates is the hard-coded second list the fix removes. Only the
    parse tree separates the two.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    documentation: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            documentation.add(id(first.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in documentation
    ]


AGENT_SESSION_ID = "22222222-2222-4222-8222-222222222222"
TERMINAL_SESSION_ID = "44444444-4444-4444-8444-444444444444"
RESUME_HANDLE = "55555555-5555-4555-8555-555555555555"
OBSERVATION_ID = "99999999-9999-4999-8999-999999999999"
PROCESS_EPOCH = "33333333-3333-4333-8333-333333333333"
TOKEN_BODY = "a" * 43


def grant_payload(**overrides: object) -> dict[str, object]:
    return {
        "terminal_session_id": TERMINAL_SESSION_ID,
        "resume_handle": RESUME_HANDLE,
        "connect_url": (
            f"wss://api.getcuna.com/v1/terminal-connections/{TERMINAL_SESSION_ID}/stream"
        ),
        "connect_token": "runa_tc_" + TOKEN_BODY,
        "protocol": "runa.terminal.v1",
        "capabilities": [
            {"name": "acknowledgement", "availability": "supported"},
            {"name": "heartbeat", "availability": "supported"},
            {"name": "live_resize", "availability": "unknown"},
            {"name": "resume", "availability": "supported"},
            {"name": "signals", "availability": "unsupported"},
        ],
        "expires_at": "2026-08-08T12:00:30Z",
        **overrides,
    }


def auth_payload(**overrides: object) -> dict[str, object]:
    observed = datetime.now(timezone.utc) - timedelta(seconds=1)

    def iso(value: datetime) -> str:
        return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    return {
        "observation_id": OBSERVATION_ID,
        "agent_session_id": AGENT_SESSION_ID,
        "process_epoch": PROCESS_EPOCH,
        "auth_mode": "interactive_login",
        "agent_version": "2.1.42",
        "adapter_version": "runa.agent-auth.v1",
        "evidence_class": "provider_cli_login_status",
        "observed_at": iso(observed),
        "valid_until": iso(observed + timedelta(seconds=20)),
        "state": "authenticated",
        **overrides,
    }


# --- S-1: terminal connect tokens -------------------------------------------


@pytest.mark.contract
@pytest.mark.parametrize("brand", WIRE_BRANDS)
def test_terminal_connect_token_accepts_every_brand(brand: str) -> None:
    token = f"{brand}_tc_" + TOKEN_BODY
    grant = decode_for_operation(
        "agentSessions.createTerminalConnection", grant_payload(connect_token=token)
    )
    assert grant.connect_token == token


@pytest.mark.contract
@pytest.mark.parametrize(
    "token",
    (
        "nuna_tc_" + TOKEN_BODY,
        "cuna_tc_" + "a" * 42,
        "cuna_tc_" + "a" * 44,
        "cuna_sk_" + TOKEN_BODY,
        "cuna_tc_" + "a" * 42 + "!",
        "cuna_tc_",
    ),
)
def test_terminal_connect_token_rejects_wrong_brand_or_length(token: str) -> None:
    with pytest.raises(DecodeFailure):
        decode_for_operation(
            "agentSessions.createTerminalConnection", grant_payload(connect_token=token)
        )


# --- S-3: protocol literals --------------------------------------------------


@pytest.mark.contract
@pytest.mark.parametrize("brand", WIRE_BRANDS)
def test_terminal_protocol_accepts_every_brand_and_echoes_it(brand: str) -> None:
    protocol = f"{brand}.terminal.v1"
    grant = decode_for_operation(
        "agentSessions.createTerminalConnection", grant_payload(protocol=protocol)
    )
    assert grant.protocol == protocol


@pytest.mark.contract
@pytest.mark.parametrize(
    "protocol",
    ("nuna.terminal.v1", "cuna.terminal.v2", "terminal.v1", "cuna.terminal", ""),
)
def test_terminal_protocol_rejects_unknown_brand_or_version(protocol: str) -> None:
    with pytest.raises(DecodeFailure):
        decode_for_operation(
            "agentSessions.createTerminalConnection", grant_payload(protocol=protocol)
        )


@pytest.mark.contract
@pytest.mark.parametrize("brand", WIRE_BRANDS)
def test_agent_auth_adapter_accepts_every_brand_and_echoes_it(brand: str) -> None:
    adapter = f"{brand}.agent-auth.v1"
    decoded = decode_for_operation("agentSessions.agentAuth", auth_payload(adapter_version=adapter))
    assert decoded.adapter_version == adapter


@pytest.mark.contract
@pytest.mark.parametrize(
    "adapter",
    ("nuna.agent-auth.v1", "cuna.agent-auth.v2", "agent-auth.v1", ""),
)
def test_agent_auth_adapter_rejects_unknown_brand_or_version(adapter: str) -> None:
    with pytest.raises(DecodeFailure):
        decode_for_operation("agentSessions.agentAuth", auth_payload(adapter_version=adapter))


@pytest.mark.contract
def test_widened_acceptance_does_not_change_what_the_client_emits() -> None:
    """The service owns the minted spelling; only what we accept moved."""

    recorder = SyncRecorder(lambda _request, _context: json_response(201, grant_payload()))
    client = Cuna(api_key="runa_sk_synthetic", transport=recorder)
    client.agent_sessions.create_terminal_connection(
        AGENT_SESSION_ID,
        TerminalConnectionCreateOptions(
            idempotency_key="terminal-connect-1",
            client_instance_id="python-sdk.test:1",
        ),
    )
    client.close()
    body = dict(recorder.calls[0][0].body or {})
    assert body["protocol"] == "runa.terminal.v1"
    assert EMITTED_TERMINAL_PROTOCOL == "runa.terminal.v1"


# --- S-2: runtime and open-capability URL zones ------------------------------


@pytest.mark.contract
@pytest.mark.parametrize("brand", WIRE_BRANDS)
def test_open_capability_url_accepts_every_runtime_zone(brand: str) -> None:
    url = f"https://session.{brand}code.cloud/__runa/auth?t=synthetic"
    assert decode_for_operation("sessions.open", {"url": url}).url == url


@pytest.mark.security
@pytest.mark.parametrize("brand", WIRE_BRANDS)
@pytest.mark.parametrize(
    "template",
    (
        "https://session.{brand}.cloud/__runa/auth?t=x",
        "https://session.{brand}code.io/__runa/auth?t=x",
        "https://a.session.{brand}code.cloud/__runa/auth?t=x",
        "https://session.{brand}code.cloud.evil.test/__runa/auth?t=x",
        "https://session-{brand}code.cloud/__runa/auth?t=x",
        "http://session.{brand}code.cloud/__runa/auth?t=x",
        "https://session.{brand}code.cloud:443/__runa/auth?t=x",
        "https://user@session.{brand}code.cloud/__runa/auth?t=x",
        "https://session.{brand}code.cloud/elsewhere?t=x",
        "https://session.{brand}code.cloud/__runa/auth?t=",
        "https://session.{brand}code.cloud/__runa/auth?t=x#fragment",
    ),
)
def test_open_capability_url_rejects_shapes_outside_one_zone_label(
    brand: str, template: str
) -> None:
    url = template.format(brand=brand)
    with pytest.raises(DecodeFailure):
        decode_for_operation("sessions.open", {"url": url})


@pytest.mark.contract
@pytest.mark.parametrize("brand", WIRE_BRANDS)
def test_session_runtime_url_accepts_every_runtime_zone(brand: str) -> None:
    url = f"https://session.{brand}code.cloud"
    decoded = decode_for_operation("sessions.get", session_payload() | {"url": url})
    assert decoded.url == url


@pytest.mark.security
@pytest.mark.parametrize("brand", WIRE_BRANDS)
@pytest.mark.parametrize(
    "template",
    (
        "https://session.{brand}.cloud",
        "https://a.session.{brand}code.cloud",
        "https://session.{brand}code.cloud.evil.test",
        "https://session-{brand}code.cloud",
        "https://session.{brand}code.cloud/",
        "https://session.{brand}code.cloud:443",
        "https://user@session.{brand}code.cloud",
        "http://session.{brand}code.cloud",
    ),
)
def test_session_runtime_url_rejects_shapes_outside_one_zone_label(
    brand: str, template: str
) -> None:
    url = template.format(brand=brand)
    with pytest.raises(DecodeFailure):
        decode_for_operation("sessions.get", session_payload() | {"url": url})


# --- S-5: the disclosure classifier knows every credential family ------------


@pytest.mark.security
def test_retained_content_policy_detects_every_brand_and_family() -> None:
    """Every brand x family combination is detected -- at the CI gate only.

    Do not read this as runtime coverage. Measured reachability:
    `security._KEY_PREFIXES` is read by `_USABLE_KEY` and nothing else,
    `_USABLE_KEY` is read inside `retained_content_category` and nothing else,
    and the sole non-test caller of `retained_content_category` is
    `tools/safety_scan.py`, run by `quality.yml` and `static-security.yml`. A
    family added to the tuple is therefore detected when a repository artifact
    is scanned, and never on a live response.

    The live-response guard is `contains_denied`, which consults
    `_DENIED_FRAGMENTS` alone and is deliberately left that way -- see
    `test_widening_the_classifier_did_not_narrow_the_runtime_wire_guard` and the
    coverage-limit note at the `_KEY_PREFIXES` definition in `security.py`.
    """

    combinations = [
        f"{brand}_{family}_" + "abcdefgh" for brand in WIRE_BRANDS for family in CREDENTIAL_FAMILIES
    ]
    # Derived, never a literal. A hardcoded count turns every new family into an
    # edit of this line, and the family that gets added without one is the family
    # nothing detects -- which is exactly how `cr` stayed invisible.
    assert len(combinations) == len(WIRE_BRANDS) * len(CREDENTIAL_FAMILIES)
    # `cr` names itself here so the ninth family cannot be dropped in silence.
    assert "cuna_cr_abcdefgh" in combinations
    for value in combinations:
        assert security.retained_content_category(value) == "usable-api-key", value
    # Nested positions reach the same classifier.
    assert (
        security.retained_content_category({"body": ["safe", combinations[-1]]}) == "usable-api-key"
    )
    # Neither a foreign brand nor a truncated body is credential material.
    assert security.retained_content_category("nuna_tc_abcdefgh") is None
    assert security.retained_content_category("cuna_tc_abc") is None
    assert security.retained_content_category("cuna_xx_abcdefgh") is None


@pytest.mark.security
def test_shared_brand_authority_is_single_sourced() -> None:
    """`security` duplicates the brand and family lists; nothing may drift.

    It cannot import them: `tools/safety_scan.py` loads that module by path so a
    repository scan never executes the runtime package, which forbids a relative
    import there. This test is the binding that keeps the copies identical.
    """

    assert security._BRANDS == WIRE_BRANDS
    assert security._CREDENTIAL_FAMILIES == CREDENTIAL_FAMILIES
    assert set(security._KEY_PREFIXES) == {
        prefix for family in CREDENTIAL_FAMILIES for prefix in branded_credential_prefixes(family)
    }
    assert len(security._KEY_PREFIXES) == len(WIRE_BRANDS) * len(CREDENTIAL_FAMILIES)


# --- S-6: local configuration names ------------------------------------------
#
# The credential pair was widened to dual-accept and the endpoint pair in the
# same config block was not, because they were two independent literal lists and
# nobody compared them. `CUNA_BASE_URL` was minted by the Cuna-branded docs and
# read nowhere: exporting it produced no error, no warning, and the *production*
# origin. Silence is the whole defect, so every case below also asserts that a
# rejected value is rejected rather than replaced by the default.
#
# These cases parametrize over the BRAND AUTHORITY, never over the resolver's own
# `config.*_ENV_NAMES`. Measured, not assumed: parametrizing over the resolver's
# list made the pre-fix source pass, because narrowing the list also narrowed the
# parametrization and the missing case simply stopped existing. A test whose
# inputs come from the thing under test cannot detect that thing shrinking.
# `test_configuration_env_names_derive_from_the_shared_brand_authority` is the
# one place the two lists are compared.

BASE_URL_ENV = branded_env_names("BASE_URL")
API_KEY_ENV = branded_env_names("API_KEY")


@pytest.mark.contract
@pytest.mark.parametrize("name", BASE_URL_ENV)
def test_base_url_environment_accepts_every_brand_spelling(name: str) -> None:
    resolved = resolve_config(
        api_key="cuna_sk_value",
        base_url=None,
        config_file=None,
        environ={name: LEGACY_BASE_URL + "/"},
    )
    assert isinstance(resolved, EffectiveConfig)
    # The legacy origin, never the default: proves the variable was actually read
    # instead of falling through, which is exactly what used to happen.
    assert resolved.base_url == LEGACY_BASE_URL
    assert resolved.base_url_source == "environment"


@pytest.mark.contract
@pytest.mark.parametrize("name", API_KEY_ENV)
def test_api_key_environment_accepts_every_brand_spelling(name: str) -> None:
    resolved = resolve_config(
        api_key=None,
        base_url=None,
        config_file=None,
        environ={name: "cuna_sk_value"},
    )
    assert isinstance(resolved, EffectiveConfig)
    assert resolved.api_key_source == "environment"


@pytest.mark.contract
def test_base_url_environment_prefers_the_canonical_brand_when_both_are_set() -> None:
    """Both names set: the canonical one wins, and it wins by *presence*.

    Rejecting the ambiguity was the alternative and it was refused. It would
    narrow an accepting surface -- a migrating deployment that exports the new
    name while the old one is still in an org-level environment would stop
    booting -- and `ConfigError` here carries no detail, so the rejection would
    be undiagnosable. Preferring the legacy name was refused too: the config
    block would then prefer `CUNA_` for the key and `RUNA_` for the origin, and
    a user could only adopt the canonical name by *unsetting* the old one.
    """

    # Spelled out, on purpose. Everything else here is derived, so reversing the
    # brand order would reverse the expectation with it and this test would keep
    # passing while the decision silently flipped. Measured: it did. An oracle
    # needs one value the implementation cannot move.
    assert BASE_URL_ENV[0] == "CUNA_BASE_URL"
    assert API_KEY_ENV[0] == "CUNA_API_KEY"

    both = {BASE_URL_ENV[0]: DEFAULT_BASE_URL, BASE_URL_ENV[-1]: LEGACY_BASE_URL}
    resolved = resolve_config(
        api_key="cuna_sk_value", base_url=None, config_file=None, environ=both
    )
    assert isinstance(resolved, EffectiveConfig)
    assert resolved.base_url == DEFAULT_BASE_URL
    # Same shape as the credential pair, which is the point of one derivation.
    keys = {API_KEY_ENV[0]: "cuna_sk_canonical", API_KEY_ENV[-1]: "runa_sk_legacy"}
    key_resolved = resolve_config(api_key=None, base_url=None, config_file=None, environ=keys)
    assert isinstance(key_resolved, EffectiveConfig)
    assert key_resolved.api_key == "cuna_sk_canonical"


@pytest.mark.security
@pytest.mark.parametrize("name", BASE_URL_ENV)
@pytest.mark.parametrize(
    ("value", "category"),
    (
        ("https://example.com", "prohibited_base_url"),
        ("http://api.getcuna.com", "invalid_base_url"),
        ("https://api.getcuna.com:443", "prohibited_base_url"),
        ("", "invalid_base_url"),
    ),
)
def test_base_url_environment_rejects_a_malformed_value_under_every_brand(
    name: str, value: str, category: str
) -> None:
    resolved = resolve_config(
        api_key="cuna_sk_value", base_url=None, config_file=None, environ={name: value}
    )
    # Rejected, not replaced. A test that only proved acceptance would pass
    # against a resolver that silently swallowed every bad value.
    assert resolved == SafeConfigFailure(category, "environment", "base_url")  # type: ignore[arg-type]


@pytest.mark.security
def test_present_invalid_canonical_base_url_never_falls_back_to_the_legacy_name() -> None:
    """Presence decides, not validity -- the rule the key layer already states."""

    resolved = resolve_config(
        api_key="cuna_sk_value",
        base_url=None,
        config_file=None,
        environ={BASE_URL_ENV[0]: "https://example.com", BASE_URL_ENV[-1]: LEGACY_BASE_URL},
    )
    assert resolved == SafeConfigFailure("prohibited_base_url", "environment", "base_url")


@pytest.mark.security
def test_configuration_env_names_derive_from_the_shared_brand_authority() -> None:
    """No second literal list. `src/` may not name a branded variable at all.

    The defect being closed is not the missing variable, it is the two
    independent lists. If a future edit hard-codes an env name anywhere in the
    shipped package, this fires -- because that edit is the first half of the
    next divergence.
    """

    assert branded_env_names("API_KEY") == API_KEY_ENV_NAMES
    assert branded_env_names("BASE_URL") == BASE_URL_ENV_NAMES
    assert len(API_KEY_ENV_NAMES) == len(BASE_URL_ENV_NAMES) == len(WIRE_BRANDS)
    assert BASE_URL_ENV_NAMES[0].startswith(WIRE_BRANDS[0].upper())

    alternation = "|".join(brand.upper() for brand in WIRE_BRANDS)
    branded = re.compile(rf"(?:{alternation})_[A-Z0-9_]+")
    generated = REPOSITORY_ROOT / "src/cuna/_internal/contract/generated"
    offenders = sorted(
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
        if generated not in path.parents
        and any(branded.fullmatch(value) for value in _executable_string_constants(path))
    )
    assert offenders == []


@pytest.mark.contract
def test_documentation_states_the_environment_precedence_it_implements() -> None:
    """Both-set behaviour must be findable without reading source.

    The sentences are derived from the same tuples the resolver walks, so a
    brand appended to `WIRE_BRANDS` fails here until the shipped documentation
    names it. `README.md` is `project.readme`, so it is the page a user reads on
    the index; the guide is where a user goes once the origin looks wrong.
    """

    order = {
        name: " then ".join(f"`{n}`" for n in names)
        for name, names in (
            ("key", API_KEY_ENV_NAMES),
            ("url", BASE_URL_ENV_NAMES),
        )
    }
    assert order["url"] == "`CUNA_BASE_URL` then `RUNA_BASE_URL`"
    for relative in ("README.md", "docs/guides/troubleshooting.md"):
        text = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
        assert order["key"] in text, relative
        assert order["url"] in text, relative


@pytest.mark.security
def test_widening_the_classifier_did_not_narrow_the_runtime_wire_guard() -> None:
    """`contains_denied` gates live responses and must still pass a real grant.

    It screens reserved upstream infrastructure, not credential prefixes. If the
    credential families were ever folded into it, a legitimate terminal grant --
    which carries a `_tc_` token by contract -- would be refused, and refusing it
    destroys the capability rather than deferring it. That is a narrowing, and
    this test exists to make it fail loudly.
    """

    from cuna._internal.security import contains_denied

    assert contains_denied(grant_payload()) is False
    assert contains_denied(grant_payload(connect_token="cuna_tc_" + TOKEN_BODY)) is False
    assert (
        decode_for_operation(
            "agentSessions.createTerminalConnection",
            grant_payload(connect_token="cuna_tc_" + TOKEN_BODY),
        ).connect_token
        == "cuna_tc_" + TOKEN_BODY
    )
