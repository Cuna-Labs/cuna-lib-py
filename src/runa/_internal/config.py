"""One-shot immutable configuration resolution."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from runa.errors import ConfigError

Source = Literal["constructor", "environment", "file", "default"]


@dataclass(frozen=True, slots=True, repr=False)
class EffectiveConfig:
    api_key: str
    base_url: str
    api_key_source: Source
    base_url_source: Source


def _read_config_file(config_file: str | os.PathLike[str] | None) -> dict[str, str]:
    if config_file is None:
        return {}
    try:
        raw_path = os.fspath(config_file)
    except TypeError:
        raise ConfigError() from None
    if not isinstance(raw_path, str):
        raise ConfigError() from None
    try:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.is_file():
            raise ConfigError()
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except ConfigError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ConfigError() from None
    if not isinstance(parsed, dict) or set(parsed) - {"api_key", "base_url"}:
        raise ConfigError() from None
    if any(not isinstance(value, str) for value in parsed.values()):
        raise ConfigError() from None
    return parsed


def _valid_key(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.startswith("runa_sk_")


def _normalize_origin(value: object) -> str:
    if not isinstance(value, str):
        raise ConfigError()
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise ConfigError() from None
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or parts.path not in ("", "/")
    ):
        raise ConfigError()
    hostname = parts.hostname.lower()
    if hostname in {"runta.com", "runta.dev"} or hostname.endswith((".runta.com", ".runta.dev")):
        raise ConfigError()
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"https://{host}" + (f":{port}" if port is not None else "")


def resolve_config(
    *,
    api_key: str | None,
    base_url: str | None,
    config_file: str | os.PathLike[str] | None,
    environ: os._Environ[str] | dict[str, str] | None = None,
) -> EffectiveConfig:
    env = os.environ if environ is None else environ
    file_data = _read_config_file(config_file)

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
        raise ConfigError() from None

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

    return EffectiveConfig(
        api_key=selected_key,
        base_url=_normalize_origin(selected_url),
        api_key_source=selected_key_source,
        base_url_source=selected_url_source,
    )
