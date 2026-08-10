from __future__ import annotations

import json
from types import MappingProxyType

import pytest

from cuna import AsyncCuna, AsyncRuna, Cuna, Runa
from cuna.errors import CunaError, RunaError
from runa import TerminalConnectionGrant
from runa._internal.config import EffectiveConfig, resolve_config
from runa._internal.contract.bridge import decode_for_operation
from runa._internal.transport import RawResponse, disposition
from runa.errors import ApiError


def test_cuna_names_alias_the_stable_runa_api() -> None:
    assert Cuna is Runa
    assert AsyncCuna is AsyncRuna
    assert CunaError is RunaError


def test_legacy_runa_namespace_remains_importable() -> None:
    from runa import Runa as LegacyRuna

    assert LegacyRuna is Cuna


def test_getcuna_is_default_and_runacode_remains_a_legacy_origin() -> None:
    default = resolve_config(
        api_key="runa_sk_compatibility",
        base_url=None,
        config_file=None,
        environ={},
    )
    legacy = resolve_config(
        api_key="runa_sk_compatibility",
        base_url="https://api.runacode.io/",
        config_file=None,
        environ={},
    )
    assert isinstance(default, EffectiveConfig)
    assert isinstance(legacy, EffectiveConfig)
    assert default.base_url == "https://api.getcuna.com"
    assert legacy.base_url == "https://api.runacode.io"


def test_getcuna_problem_and_terminal_origins_are_accepted() -> None:
    problem = {
        "type": "https://api.getcuna.com/problems/request_failed",
        "title": "Request failed",
        "status": 400,
        "code": "request_failed",
        "request_id": "00000000-0000-4000-8000-000000000000",
        "retryable": False,
    }
    with pytest.raises(ApiError) as error:
        disposition(
            RawResponse(
                400,
                MappingProxyType({"content-type": "application/problem+json"}),
                json.dumps(problem).encode(),
            ),
            200,
        )
    assert error.value.problem is not None
    assert error.value.problem.type == problem["type"]

    terminal_session_id = "11111111-1111-4111-8111-111111111111"
    decoded = decode_for_operation(
        "agentSessions.createTerminalConnection",
        {
            "terminal_session_id": terminal_session_id,
            "resume_handle": "22222222-2222-4222-8222-222222222222",
            "connect_url": (
                f"wss://api.getcuna.com/v1/terminal-connections/{terminal_session_id}/stream"
            ),
            "connect_token": "runa_tc_" + "A" * 43,
            "protocol": "runa.terminal.v1",
            "capabilities": [
                {"name": name, "availability": "supported"}
                for name in (
                    "acknowledgement",
                    "heartbeat",
                    "live_resize",
                    "resume",
                    "signals",
                )
            ],
            "expires_at": "2026-08-09T12:00:00Z",
        },
    )
    assert isinstance(decoded, TerminalConnectionGrant)
    assert decoded.connect_url == (
        f"wss://api.getcuna.com/v1/terminal-connections/{terminal_session_id}/stream"
    )
