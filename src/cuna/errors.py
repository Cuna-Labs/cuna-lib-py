"""Closed, disclosure-safe Cuna SDK error hierarchy."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal

ErrorCode = Literal["config_error", "api_error", "malformed_response", "command_error"]

_MESSAGES: Final[dict[ErrorCode, str]] = {
    "config_error": "Cuna SDK configuration is invalid.",
    "api_error": "The Cuna API request failed.",
    "malformed_response": "The Cuna API returned an invalid response.",
    "command_error": "The session command failed.",
}


class ProblemAction(str, Enum):
    """Closed recovery action supplied by a Cuna API Problem response."""

    RETRY = "retry"
    SIGN_IN = "sign_in"
    OPEN_WEB = "open_web"
    CONTACT_SUPPORT = "contact_support"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class ApiProblem:
    """Validated RFC 9457-style Cuna API problem details."""

    type: str
    title: str
    status: int
    code: str
    request_id: str
    retryable: bool
    detail: str | None = None
    action: ProblemAction | None = None


WorkspaceSyncCapability = Literal[
    "atomic_generation_commit",
    "bounded_manifest_pages",
    "content_digest_verification",
    "explicit_reconciliation",
    "ordered_generation_changes",
    "policy_bound_admission",
]


@dataclass(frozen=True, slots=True)
class WorkspaceSyncProblem(ApiProblem):
    """Validated negotiated workspace-sync failure with protocol evidence."""

    selected_protocol: Literal[1, 2] | None = None
    capabilities: tuple[WorkspaceSyncCapability, ...] = ()


class CunaError(Exception, ABC):
    """Nonconstructible common base for normalized SDK errors.

    Attributes:
        code: Stable disclosure-safe error category.
        message: Stable disclosure-safe English message.
    Raises:
        TypeError: On direct construction.
    Examples:
        See ``REF-EX-CUNAERROR`` and ``TC-091-09``.
    """

    __slots__ = ("_code", "_message", "_sealed")
    _code: ErrorCode
    _message: str
    _sealed: bool

    def __new__(cls, *args: object, **kwargs: object) -> CunaError:
        del args, kwargs
        if cls is CunaError:
            raise TypeError("CunaError cannot be constructed directly.")
        return super().__new__(cls)

    def __init__(self, code: ErrorCode) -> None:
        object.__setattr__(self, "_code", code)
        object.__setattr__(self, "_message", _MESSAGES[code])
        Exception.__init__(self, _MESSAGES[code])
        object.__setattr__(self, "_sealed", True)

    @property
    def code(self) -> ErrorCode:
        """Return the stable error category.

        Returns:
            One accepted ``ErrorCode`` literal.
        Examples:
            See ``REF-EX-CUNAERROR`` and ``TC-091-09``.
        """
        return self._code

    @property
    def message(self) -> str:
        """Return the stable disclosure-safe message.

        Returns:
            The normalized English error message.
        Examples:
            See ``REF-EX-CUNAERROR`` and ``TC-091-09``.
        """
        return self._message

    def __setattr__(self, name: str, value: object) -> None:
        exception_runtime_attributes = {
            "__cause__",
            "__context__",
            "__notes__",
            "__suppress_context__",
            "__traceback__",
        }
        if getattr(self, "_sealed", False) and name not in exception_runtime_attributes:
            raise AttributeError(f"{type(self).__name__} is immutable")
        object.__setattr__(self, name, value)

    def __str__(self) -> str:
        return self._message


class ConfigError(CunaError):
    """Safe configuration or local-input failure.

    Examples:
        See ``REF-EX-CONFIGERROR`` and ``TC-091-09``.
    """

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("config_error")


class ApiError(CunaError):
    """Safe API or malformed-response failure.

    Args:
        status: HTTP status associated with the failure.
        code: ``api_error`` or ``malformed_response``.
        problem: Validated Problem body associated with this failure, when supplied.
    Raises:
        TypeError: If ``status`` is not exactly an integer.
    Examples:
        See ``REF-EX-APIERROR`` and ``TC-091-09``.
    """

    __slots__ = ("_problem", "_status")
    _status: int
    _problem: ApiProblem | WorkspaceSyncProblem | None

    def __init__(
        self,
        status: int,
        *,
        code: Literal["api_error", "malformed_response"] = "api_error",
        problem: ApiProblem | WorkspaceSyncProblem | None = None,
    ) -> None:
        if type(status) is not int:
            raise TypeError("status must be an integer")
        if problem is not None and (
            not isinstance(problem, ApiProblem) or problem.status != status or code != "api_error"
        ):
            raise TypeError("problem must match an api_error status")
        object.__setattr__(self, "_status", status)
        object.__setattr__(self, "_problem", problem)
        super().__init__(code)

    @property
    def status(self) -> int:
        """Return the associated HTTP status.

        Returns:
            The exact integer supplied by the SDK failure path.
        Examples:
            See ``REF-EX-APIERROR`` and ``TC-091-09``.
        """
        return self._status

    @property
    def problem(self) -> ApiProblem | WorkspaceSyncProblem | None:
        """Return a validated Problem body, when the service supplied one.

        Returns:
            The validated Problem body, or ``None`` when no body was supplied.
        Examples:
            See ``REF-EX-APIERROR`` and ``TC-091-09``.
        """

        return self._problem


class CommandError(CunaError):
    """Reserved compatibility type; no SDK v1 path constructs or raises it.

    Raises:
        TypeError: On every construction attempt.
    Examples:
        See ``REF-EX-COMMANDERROR`` and ``TC-091-09``.
    """

    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object) -> CommandError:
        del cls, args, kwargs
        raise TypeError("CommandError is reserved and cannot be constructed.")

    def __init__(self) -> None:
        super().__init__("command_error")


__all__ = (
    "ApiError",
    "ApiProblem",
    "CommandError",
    "ConfigError",
    "CunaError",
    "ProblemAction",
    "WorkspaceSyncProblem",
)
