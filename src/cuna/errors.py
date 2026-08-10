"""Cuna error imports backed by the stable Runa wire contract."""

from runa.errors import (
    ApiError,
    ApiProblem,
    CommandError,
    ConfigError,
    ProblemAction,
    RunaError,
    WorkspaceSyncProblem,
)

CunaError = RunaError

__all__ = (
    "ApiError",
    "ApiProblem",
    "CommandError",
    "ConfigError",
    "CunaError",
    "ProblemAction",
    "RunaError",
    "WorkspaceSyncProblem",
)
