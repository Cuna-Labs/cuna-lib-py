"""One-shot immutable configuration resolution."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

Source = Literal["constructor", "environment", "file", "default"]
FailureCategory = Literal[
    "missing_api_key",
    "invalid_api_key",
    "invalid_base_url",
    "prohibited_base_url",
    "invalid_config_file",
]


@dataclass(frozen=True, slots=True, repr=False)
class EffectiveConfig:
    api_key: str
    base_url: str
    api_key_source: Source
    base_url_source: Source


@dataclass(frozen=True, slots=True)
class SafeConfigFailure:
    category: FailureCategory
    source: Source | None
    field: Literal["api_key", "base_url", "config_file"]


def _read_config_file(
    config_file: str | os.PathLike[str] | None,
) -> dict[str, str] | SafeConfigFailure:
    if config_file is None:
        return {}
    try:
        raw_path = os.fspath(config_file)
    except TypeError:
        return SafeConfigFailure("invalid_config_file", None, "config_file")
    if not isinstance(raw_path, str):
        return SafeConfigFailure("invalid_config_file", None, "config_file")
    try:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.is_file():
            return SafeConfigFailure("invalid_config_file", None, "config_file")
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return SafeConfigFailure("invalid_config_file", None, "config_file")
    if not isinstance(parsed, dict) or set(parsed) - {"api_key", "base_url"}:
        return SafeConfigFailure("invalid_config_file", None, "config_file")
    if any(not isinstance(value, str) for value in parsed.values()):
        return SafeConfigFailure("invalid_config_file", None, "config_file")
    return parsed


def _valid_key(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.startswith("runa_sk_")


def _normalize_origin(value: object) -> tuple[str | None, FailureCategory]:
    if not isinstance(value, str):
        return None, "invalid_base_url"
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        return None, "invalid_base_url"
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or parts.path not in ("", "/")
    ):
        return None, "invalid_base_url"
    hostname = parts.hostname.lower().removesuffix(".")
    if hostname != "api.runacode.io" or port is not None:
        return None, "prohibited_base_url"
    return "https://api.runacode.io", "invalid_base_url"


def resolve_config(
    *,
    api_key: str | None,
    base_url: str | None,
    config_file: str | os.PathLike[str] | None,
    environ: os._Environ[str] | dict[str, str] | None = None,
) -> EffectiveConfig | SafeConfigFailure:
    env = os.environ if environ is None else environ
    file_data = _read_config_file(config_file)
    if isinstance(file_data, SafeConfigFailure):
        return file_data

    key_candidates: tuple[tuple[Source, object | None, bool], ...] = (
        ("constructor", api_key, api_key is not None),
        ("environment", env.get("RUNA_API_KEY"), "RUNA_API_KEY" in env),
        ("file", file_data.get("api_key"), "api_key" in file_data),
    )
    selected_key: object | None = None
    selected_key_source: Source | None = None
    for source, value, present in key_candidates:
        if present:
            selected_key, selected_key_source = value, source
            break
    if selected_key_source is None or not _valid_key(selected_key):
        return SafeConfigFailure(
            "missing_api_key" if selected_key_source is None else "invalid_api_key",
            selected_key_source,
            "api_key",
        )

    url_candidates: tuple[tuple[Source, object | None, bool], ...] = (
        ("constructor", base_url, base_url is not None),
        ("environment", env.get("RUNA_BASE_URL"), "RUNA_BASE_URL" in env),
        ("file", file_data.get("base_url"), "base_url" in file_data),
        ("default", "https://api.runacode.io", True),
    )
    selected_url: object = "https://api.runacode.io"
    selected_url_source: Source = "default"
    for source, value, present in url_candidates:
        if present:
            selected_url, selected_url_source = value, source
            break

    normalized_url, failure_category = _normalize_origin(selected_url)
    if normalized_url is None:
        return SafeConfigFailure(failure_category, selected_url_source, "base_url")
    return EffectiveConfig(
        api_key=cast(str, selected_key),
        base_url=normalized_url,
        api_key_source=selected_key_source,
        base_url_source=selected_url_source,
    )
