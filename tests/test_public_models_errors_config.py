from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError

import pytest

import runa
import runa.client as client_module
from runa import (
    UNSET,
    Acknowledgement,
    AssignedWorkspace,
    AsyncCapabilitiesManager,
    AsyncRecordsManager,
    AsyncRuna,
    AsyncSession,
    AsyncSessionsManager,
    CapabilitiesManager,
    Capability,
    CapabilityAvailability,
    CapabilityInteraction,
    CapabilityMutationClass,
    CapabilityScope,
    CapabilitySnapshot,
    CapabilitySurface,
    EstimatedUsage,
    ExecResult,
    Me,
    OpenSessionResult,
    OutboundPolicy,
    OutboundPolicyMode,
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
from runa._internal.config import (
    EffectiveConfig,
    SafeConfigFailure,
    _read_config_file,
    resolve_config,
)
from runa.errors import ApiError, CommandError, ConfigError, RunaError

EXPECTED_EXPORTS = (
    "Acknowledgement",
    "AgentSession",
    "AgentSessionAuth",
    "AgentSessionAuthEvidenceClass",
    "AgentSessionAuthMode",
    "AgentSessionAuthState",
    "AgentSessionCreateOptions",
    "AgentSessionDesiredState",
    "AgentSessionListOptions",
    "AgentSessionPage",
    "AgentSessionProcessState",
    "AgentSessionRequestState",
    "AgentSessionsManager",
    "AssignedWorkspace",
    "AsyncAgentSessionsManager",
    "AsyncCapabilitiesManager",
    "AsyncRecordsManager",
    "AsyncMachineCreatesManager",
    "AsyncRuna",
    "AsyncSession",
    "AsyncSessionsManager",
    "AsyncWorkspaceSyncManager",
    "AsyncWorkspaceBindingsManager",
    "CapabilitiesManager",
    "Capability",
    "CapabilityAvailability",
    "CapabilityInteraction",
    "CapabilityMutationClass",
    "CapabilityScope",
    "CapabilitySnapshot",
    "CapabilitySurface",
    "EstimatedUsage",
    "ExecOptions",
    "ExecResult",
    "Me",
    "MachineCreateRequest",
    "MachineCreatesManager",
    "OpenSessionResult",
    "OutboundPolicy",
    "OutboundPolicyMode",
    "Record",
    "RecordsManager",
    "Runa",
    "Session",
    "SessionAgent",
    "SessionCreateOptions",
    "SessionSnapshot",
    "SessionsManager",
    "SessionStatus",
    "TerminalConnectionAvailability",
    "TerminalConnectionCapability",
    "TerminalConnectionCapabilityName",
    "TerminalConnectionCreateOptions",
    "TerminalConnectionGrant",
    "UNSET",
    "UnassignedWorkspace",
    "UnsetType",
    "WorkspaceSyncBeginRequest",
    "WorkspaceBinding",
    "WorkspaceBindingCreateRequest",
    "WorkspaceBindingLookup",
    "WorkspaceBindingsManager",
    "WorkspaceSyncCapability",
    "WorkspaceSyncChangeItem",
    "WorkspaceSyncChangePage",
    "WorkspaceSyncChangeOptions",
    "WorkspaceSyncChunkReceipt",
    "WorkspaceSyncChunkRef",
    "WorkspaceSyncCommitRequest",
    "WorkspaceSyncCommitReceipt",
    "WorkspaceSyncEnvelope",
    "WorkspaceSyncManager",
    "WorkspaceSyncManifestEntry",
    "WorkspaceSyncManifestReceipt",
    "WorkspaceSyncManifestPageRequest",
    "WorkspaceSyncProtocolRange",
    "WorkspaceSyncReconcileReceipt",
    "WorkspaceSyncReconcileRequest",
    "WorkspaceSyncSession",
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
    assert [member.value for member in OutboundPolicyMode] == ["allowlist", "denylist"]
    assert [member.value for member in CapabilityScope] == [
        "account",
        "machine",
        "agent_session",
    ]
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
    capability = Capability(
        "account.read",
        CapabilityAvailability.SUPPORTED,
        (CapabilitySurface.SDK,),
        CapabilityInteraction.READ_ONLY,
        CapabilityMutationClass.NONE,
        ("account:read",),
    )
    snapshot = CapabilitySnapshot(
        "1.0",
        CapabilityScope.ACCOUNT,
        None,
        "2026-08-08T12:00:00Z",
        "2026-08-08T12:00:30Z",
        "a" * 64,
        (capability,),
    )
    assert snapshot.capabilities == (capability,)
    assert OutboundPolicy(OutboundPolicyMode.ALLOWLIST, []).hosts == []
    usage = EstimatedUsage(1, 2, "estimate")
    assert AssignedWorkspace(True, "77777777-7777-4777-8777-777777777777", usage).usage is usage
    assert UnassignedWorkspace(False, 7).waitlist_position == 7
    assert Me(
        "id",
        "email",
        AssignedWorkspace(True, "77777777-7777-4777-8777-777777777777", usage),
    ).workspace.usage is usage
    assert ExecResult(7, "o", "e", 1, False, False).exit_code == 7


@pytest.mark.hermetic
def test_factory_only_types_reject_direct_construction() -> None:
    for factory in (
        CapabilitiesManager,
        SessionsManager,
        RecordsManager,
        Session,
        AsyncSessionsManager,
        AsyncCapabilitiesManager,
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
def test_sync_async_public_parameter_parity() -> None:
    pairs = (
        (Runa.close, AsyncRuna.close),
        (Runa.me, AsyncRuna.me),
        (CapabilitiesManager.get, AsyncCapabilitiesManager.get),
        (SessionsManager.create, AsyncSessionsManager.create),
        (SessionsManager.list, AsyncSessionsManager.list),
        (SessionsManager.get, AsyncSessionsManager.get),
        (RecordsManager.list, AsyncRecordsManager.list),
        (
            client_module.AgentSessionsManager.create_terminal_connection,
            client_module.AsyncAgentSessionsManager.create_terminal_connection,
        ),
        (Session.refresh, AsyncSession.refresh),
        (Session.start, AsyncSession.start),
        (Session.pause, AsyncSession.pause),
        (Session.resume, AsyncSession.resume),
        (Session.stop, AsyncSession.stop),
        (Session.delete, AsyncSession.delete),
        (Session.exec, AsyncSession.exec),
        (Session.checkpoint, AsyncSession.checkpoint),
        (Session.open, AsyncSession.open),
    )
    for synchronous, asynchronous in pairs:
        sync_parameters = tuple(inspect.signature(synchronous).parameters)
        async_parameters = tuple(inspect.signature(asynchronous).parameters)
        assert sync_parameters == async_parameters
        assert inspect.iscoroutinefunction(synchronous) is False
        assert inspect.iscoroutinefunction(asynchronous) is True


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
    with pytest.raises(TypeError):
        CommandError()
    with pytest.raises(AttributeError):
        api._status = 500  # type: ignore[misc]
    assert api.__cause__ is None
    assert api.__context__ is None


@pytest.mark.hermetic
def test_config_precedence_and_present_invalid_no_fallback(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "runa.json"
    config_path.write_text(
        json.dumps({"api_key": "runa_sk_file", "base_url": "https://api.runacode.io"}),
        encoding="utf-8",
    )
    env = {
        "CUNA_API_KEY": "cuna_sk_env",
        "RUNA_API_KEY": "runa_sk_legacy",
        "RUNA_BASE_URL": "https://api.runacode.io/",
    }
    result = resolve_config(
        api_key="runa_sk_constructor",
        base_url="https://api.runacode.io/",
        config_file=config_path,
        environ=env,
    )
    assert isinstance(result, EffectiveConfig)
    assert result.api_key == "runa_sk_constructor"
    assert result.base_url == "https://api.runacode.io"
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
    assert relative.base_url == "https://api.runacode.io"


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
@pytest.mark.parametrize(
    "base_url",
    [
        "https://example.com",
        "https://api.runacode.io:443",
        "https://api.runacode.io.",
        "https://[2001:db8::1]:8443/",
    ],
)
def test_non_runa_origins_are_prohibited_before_dispatch(base_url: str) -> None:
    result = resolve_config(
        api_key="runa_sk_value",
        base_url=base_url,
        config_file=None,
        environ={},
    )
    assert result == SafeConfigFailure("prohibited_base_url", "constructor", "base_url")


@pytest.mark.hermetic
@pytest.mark.parametrize("source", ["constructor", "environment", "file"])
def test_every_base_url_source_rejects_non_runa_origin_before_transport_creation(
    source: str, tmp_path, monkeypatch
) -> None:
    created: list[str] = []
    monkeypatch.setattr(
        client_module,
        "SyncHttpTransport",
        lambda origin: created.append(origin),
    )
    kwargs: dict[str, object] = {
        "api_key": "runa_sk_value",
        "base_url": None,
        "config_file": None,
    }
    if source == "constructor":
        kwargs["base_url"] = "https://example.com"
    elif source == "environment":
        monkeypatch.setenv("RUNA_BASE_URL", "https://example.com")
    else:
        config = tmp_path / "runa.json"
        config.write_text('{"base_url":"https://example.com"}', encoding="utf-8")
        kwargs["config_file"] = config
    with pytest.raises(ConfigError):
        Runa(**kwargs)  # type: ignore[arg-type]
    assert created == []


@pytest.mark.hermetic
def test_config_file_and_origin_edge_cases_are_closed(tmp_path) -> None:
    assert _read_config_file(object()) == SafeConfigFailure(
        "invalid_config_file", None, "config_file"
    )
    assert _read_config_file(b"bytes-path") == SafeConfigFailure(
        "invalid_config_file", None, "config_file"
    )
    assert _read_config_file(tmp_path / "missing") == SafeConfigFailure(
        "invalid_config_file", None, "config_file"
    )
    for index, content in enumerate(
        (
            "{",
            "[]",
            '{"extra":"value"}',
            '{"api_key":7}',
        )
    ):
        path = tmp_path / f"bad-{index}.json"
        path.write_text(content, encoding="utf-8")
        assert _read_config_file(path) == SafeConfigFailure(
            "invalid_config_file", None, "config_file"
        )
    binary = tmp_path / "binary.json"
    binary.write_bytes(b"\xff")
    assert _read_config_file(binary) == SafeConfigFailure(
        "invalid_config_file", None, "config_file"
    )
    invalid_port = resolve_config(
        api_key="runa_sk_value",
        base_url="https://example.com:99999",
        config_file=None,
        environ={},
    )
    assert invalid_port == SafeConfigFailure("invalid_base_url", "constructor", "base_url")


@pytest.mark.hermetic
def test_environment_and_default_config_sources() -> None:
    environment = resolve_config(
        api_key=None,
        base_url=None,
        config_file=None,
        environ={"CUNA_API_KEY": "cuna_sk_environment"},
    )
    assert isinstance(environment, EffectiveConfig)
    assert environment.api_key_source == "environment"
    assert environment.base_url_source == "default"
    assert environment.base_url == "https://api.getcuna.com"

    legacy = resolve_config(
        api_key=None,
        base_url=None,
        config_file=None,
        environ={"RUNA_API_KEY": "runa_sk_environment"},
    )
    assert isinstance(legacy, EffectiveConfig)
    assert legacy.api_key == "runa_sk_environment"

    invalid_canonical = resolve_config(
        api_key=None,
        base_url=None,
        config_file=None,
        environ={"CUNA_API_KEY": "invalid", "RUNA_API_KEY": "runa_sk_environment"},
    )
    assert invalid_canonical == SafeConfigFailure("invalid_api_key", "environment", "api_key")


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
