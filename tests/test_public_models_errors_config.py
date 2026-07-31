from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError

import pytest

import runa
from runa import (
    UNSET,
    Acknowledgement,
    AssignedWorkspace,
    AsyncRecordsManager,
    AsyncRuna,
    AsyncSession,
    AsyncSessionsManager,
    EstimatedUsage,
    ExecResult,
    Me,
    OpenSessionResult,
    Record,
    RecordsManager,
    Runa,
    Session,
    SessionAgent,
    SessionsManager,
    SessionStatus,
    UnassignedWorkspace,
    UnsetType,
)
from runa._internal.config import EffectiveConfig, SafeConfigFailure, resolve_config
from runa.errors import ApiError, CommandError, ConfigError, RunaError

EXPECTED_EXPORTS = (
    "Acknowledgement",
    "AssignedWorkspace",
    "AsyncRecordsManager",
    "AsyncRuna",
    "AsyncSession",
    "AsyncSessionsManager",
    "EstimatedUsage",
    "ExecOptions",
    "ExecResult",
    "Me",
    "OpenSessionResult",
    "Record",
    "RecordsManager",
    "Runa",
    "Session",
    "SessionAgent",
    "SessionCreateOptions",
    "SessionSnapshot",
    "SessionsManager",
    "SessionStatus",
    "UNSET",
    "UnassignedWorkspace",
    "UnsetType",
)


@pytest.mark.hermetic
def test_exact_public_exports_and_marker() -> None:
    assert runa.__all__ == EXPECTED_EXPORTS
    assert all(getattr(runa, name) is not None for name in EXPECTED_EXPORTS)
    marker = __import__("pathlib").Path(runa.__file__).with_name("py.typed")
    assert marker.read_bytes() == b""


@pytest.mark.hermetic
def test_enums_and_unset_are_closed() -> None:
    assert [member.value for member in SessionStatus] == [
        "creating",
        "running",
        "paused",
        "suspended",
        "stopped",
        "deleted",
        "error",
    ]
    assert [member.value for member in SessionAgent] == ["claude-code", "codex", "openclaw"]
    assert repr(UNSET) == "UNSET"
    with pytest.raises(TypeError):
        UnsetType()


@pytest.mark.hermetic
def test_supported_models_are_frozen_and_preserve_opaque_values() -> None:
    opaque = {"nested": [object()]}
    record = Record(1, 2, "kind", "summary", opaque, None)
    assert record.detail is opaque
    with pytest.raises(FrozenInstanceError):
        record.kind = "other"  # type: ignore[misc]
    assert Acknowledgement(True).ok is True
    assert OpenSessionResult("value").url == "value"
    usage = EstimatedUsage(1, 2, "estimate")
    assert AssignedWorkspace(True, usage).usage is usage
    assert UnassignedWorkspace(False, 7).waitlist_position == 7
    assert Me("id", "email", AssignedWorkspace(True, usage)).workspace.usage is usage
    assert ExecResult(7, "o", "e", 1, False, False).exit_code == 7


@pytest.mark.hermetic
def test_factory_only_types_reject_direct_construction() -> None:
    for factory in (
        SessionsManager,
        RecordsManager,
        Session,
        AsyncSessionsManager,
        AsyncRecordsManager,
        AsyncSession,
    ):
        with pytest.raises(TypeError):
            factory(None)  # type: ignore[call-arg]
        assert "_TOKEN" not in vars(factory)
        for bypass in (None, object(), getattr(factory, "_TOKEN", object())):
            with pytest.raises(TypeError):
                factory(None, bypass)  # type: ignore[call-arg]


@pytest.mark.hermetic
def test_error_hierarchy_is_closed_immutable_and_safe() -> None:
    with pytest.raises(TypeError):
        RunaError()  # type: ignore[abstract]
    config = ConfigError()
    assert type(config).__base__ is RunaError
    assert (config.code, config.message, str(config), config.args) == (
        "config_error",
        "Runa SDK configuration is invalid.",
        "Runa SDK configuration is invalid.",
        ("Runa SDK configuration is invalid.",),
    )
    api = ApiError(422)
    assert (api.code, api.status, str(api)) == (
        "api_error",
        422,
        "The Runa API request failed.",
    )
    malformed = ApiError(200, code="malformed_response")
    assert str(malformed) == "The Runa API returned an invalid response."
    assert CommandError.__base__ is RunaError
    with pytest.raises(AttributeError):
        api._status = 500  # type: ignore[misc]
    assert api.__cause__ is None
    assert api.__context__ is None


@pytest.mark.hermetic
def test_config_precedence_and_present_invalid_no_fallback(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "runa.json"
    config_path.write_text(
        json.dumps({"api_key": "runa_sk_file", "base_url": "https://file.example"}),
        encoding="utf-8",
    )
    env = {"RUNA_API_KEY": "runa_sk_env", "RUNA_BASE_URL": "https://env.example/"}
    result = resolve_config(
        api_key="runa_sk_constructor",
        base_url="https://constructor.example/",
        config_file=config_path,
        environ=env,
    )
    assert isinstance(result, EffectiveConfig)
    assert result.api_key == "runa_sk_constructor"
    assert result.base_url == "https://constructor.example"
    assert result.api_key_source == result.base_url_source == "constructor"

    bad = resolve_config(
        api_key="bad",
        base_url=None,
        config_file=config_path,
        environ=env,
    )
    assert bad == SafeConfigFailure("invalid_api_key", "constructor", "api_key")

    monkeypatch.chdir(tmp_path)
    relative = resolve_config(
        api_key=None,
        base_url=None,
        config_file="runa.json",
        environ={},
    )
    assert isinstance(relative, EffectiveConfig)
    assert relative.base_url == "https://file.example"


@pytest.mark.hermetic
@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "wrong",
        123,
    ],
)
def test_config_missing_or_invalid_key_is_safe(value: object) -> None:
    result = resolve_config(
        api_key=value if value is not None else None,  # type: ignore[arg-type]
        base_url=None,
        config_file=None,
        environ={},
    )
    assert isinstance(result, SafeConfigFailure)
    assert not hasattr(result, "value")


@pytest.mark.hermetic
@pytest.mark.parametrize(
    "base_url",
    [
        "http://example.com",
        "https://user@example.com",
        "https://example.com/path",
        "https://example.com?x=1",
        "https://example.com#fragment",
    ],
)
def test_invalid_origins_fail_closed(base_url: str) -> None:
    result = resolve_config(
        api_key="runa_sk_value",
        base_url=base_url,
        config_file=None,
        environ={},
    )
    assert result == SafeConfigFailure("invalid_base_url", "constructor", "base_url")


@pytest.mark.hermetic
def test_constructor_signatures_are_keyword_only() -> None:
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for name, parameter in inspect.signature(Runa).parameters.items()
        if name != "self"
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for name, parameter in inspect.signature(AsyncRuna).parameters.items()
        if name != "self"
    )
