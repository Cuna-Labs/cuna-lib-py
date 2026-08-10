from __future__ import annotations

import importlib
import json
from types import MappingProxyType

import pytest

from cuna import AsyncCuna, Cuna, TerminalConnectionGrant
from cuna._internal.config import EffectiveConfig, resolve_config
from cuna._internal.contract.bridge import decode_for_operation
from cuna._internal.transport import RawResponse, disposition
from cuna.errors import ApiError, CunaError


def test_cuna_is_the_implementation_and_not_an_alias() -> None:
    """``cuna`` owns the code. Literal oracles, so a re-inversion cannot pass.

    Asserting ``Cuna is Runa`` is what the previous shim did, and it stayed
    green in both directions. Spelling the module and symbol names out means a
    revert to a ``runa``-owned implementation fails here.
    """

    assert Cuna.__module__ == "cuna.client"
    assert AsyncCuna.__module__ == "cuna.client"
    assert CunaError.__module__ == "cuna.errors"
    assert Cuna.__name__ == "Cuna"
    assert AsyncCuna.__name__ == "AsyncCuna"
    assert CunaError.__name__ == "CunaError"
    assert Cuna.__init__.__module__ == "cuna.client"


def test_the_runa_import_namespace_no_longer_exists() -> None:
    for name in ("runa", "runa.errors", "runa.client", "runa.models"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(name)


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
