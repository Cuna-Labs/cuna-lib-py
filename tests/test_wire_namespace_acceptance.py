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

from datetime import UTC, datetime, timedelta

import pytest

from runa import Runa
from runa._internal import security
from runa._internal.constraints import (
    CREDENTIAL_FAMILIES,
    EMITTED_TERMINAL_PROTOCOL,
    WIRE_BRANDS,
    branded_credential_prefixes,
)
from runa._internal.contract import decode_for_operation
from runa._internal.contract.bridge import DecodeFailure
from runa.models import TerminalConnectionCreateOptions

from .support import SyncRecorder, json_response, session_payload

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
    observed = datetime.now(UTC) - timedelta(seconds=1)

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
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
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
@pytest.mark.parametrize(
    "url",
    (
        "https://session.cuna.cloud/__runa/auth?t=x",
        "https://session.cunacode.io/__runa/auth?t=x",
        "https://a.session.cunacode.cloud/__runa/auth?t=x",
        "http://session.cunacode.cloud/__runa/auth?t=x",
        "https://session.cunacode.cloud:443/__runa/auth?t=x",
        "https://user@session.cunacode.cloud/__runa/auth?t=x",
        "https://session.cunacode.cloud/elsewhere?t=x",
        "https://session.cunacode.cloud/__runa/auth?t=",
        "https://session.cunacode.cloud/__runa/auth?t=x#fragment",
    ),
)
def test_open_capability_url_rejects_shapes_outside_one_zone_label(url: str) -> None:
    with pytest.raises(DecodeFailure):
        decode_for_operation("sessions.open", {"url": url})


@pytest.mark.contract
@pytest.mark.parametrize("brand", WIRE_BRANDS)
def test_session_runtime_url_accepts_every_runtime_zone(brand: str) -> None:
    url = f"https://session.{brand}code.cloud"
    decoded = decode_for_operation("sessions.get", session_payload() | {"url": url})
    assert decoded.url == url


@pytest.mark.contract
@pytest.mark.parametrize(
    "url",
    (
        "https://session.cuna.cloud",
        "https://a.session.cunacode.cloud",
        "https://session.cunacode.cloud/",
        "http://session.cunacode.cloud",
    ),
)
def test_session_runtime_url_rejects_shapes_outside_one_zone_label(url: str) -> None:
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


@pytest.mark.security
def test_widening_the_classifier_did_not_narrow_the_runtime_wire_guard() -> None:
    """`contains_denied` gates live responses and must still pass a real grant.

    It screens reserved upstream infrastructure, not credential prefixes. If the
    credential families were ever folded into it, a legitimate terminal grant --
    which carries a `_tc_` token by contract -- would be refused, and refusing it
    destroys the capability rather than deferring it. That is a narrowing, and
    this test exists to make it fail loudly.
    """

    from runa._internal.security import contains_denied

    assert contains_denied(grant_payload()) is False
    assert contains_denied(grant_payload(connect_token="cuna_tc_" + TOKEN_BODY)) is False
    assert (
        decode_for_operation(
            "agentSessions.createTerminalConnection",
            grant_payload(connect_token="cuna_tc_" + TOKEN_BODY),
        ).connect_token
        == "cuna_tc_" + TOKEN_BODY
    )
