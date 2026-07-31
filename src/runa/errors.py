"""Closed, disclosure-safe Runa SDK error hierarchy."""

from __future__ import annotations

from abc import ABC
from typing import Final, Literal

ErrorCode = Literal["config_error", "api_error", "malformed_response", "command_error"]

_MESSAGES: Final[dict[ErrorCode, str]] = {
    "config_error": "Runa SDK configuration is invalid.",
    "api_error": "The Runa API request failed.",
    "malformed_response": "The Runa API returned an invalid response.",
    "command_error": "The session command failed.",
}


class RunaError(Exception, ABC):
    """Nonconstructible common base for normalized SDK errors.

    Attributes:
        code: Stable disclosure-safe error category.
        message: Stable disclosure-safe English message.
    Raises:
        TypeError: On direct construction.
    Examples:
        See ``REF-EX-RUNAERROR`` and ``TC-091-09``.
    """

    __slots__ = ("_code", "_message", "_sealed")
    _code: ErrorCode
    _message: str
    _sealed: bool

    def __new__(cls, *args: object, **kwargs: object) -> RunaError:
        del args, kwargs
        if cls is RunaError:
            raise TypeError("RunaError cannot be constructed directly.")
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
            See ``REF-EX-RUNAERROR`` and ``TC-091-09``.
        """
        return self._code

    @property
    def message(self) -> str:
        """Return the stable disclosure-safe message.

        Returns:
            The normalized English error message.
        Examples:
            See ``REF-EX-RUNAERROR`` and ``TC-091-09``.
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


class ConfigError(RunaError):
    """Safe configuration or local-input failure.

    Examples:
        See ``REF-EX-CONFIGERROR`` and ``TC-091-09``.
    """

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("config_error")


class ApiError(RunaError):
    """Safe API or malformed-response failure.

    Args:
        status: HTTP status associated with the failure.
        code: ``api_error`` or ``malformed_response``.
    Raises:
        TypeError: If ``status`` is not exactly an integer.
    Examples:
        See ``REF-EX-APIERROR`` and ``TC-091-09``.
    """

    __slots__ = ("_status",)
    _status: int

    def __init__(
        self,
        status: int,
        *,
        code: Literal["api_error", "malformed_response"] = "api_error",
    ) -> None:
        if type(status) is not int:
            raise TypeError("status must be an integer")
        object.__setattr__(self, "_status", status)
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


class CommandError(RunaError):
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


__all__ = ("ApiError", "CommandError", "ConfigError", "RunaError")
