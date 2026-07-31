# `SessionSnapshot`

Immutable snapshot of one session returned by the service.

## Import

`from runa import SessionSnapshot`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`SessionSnapshot(id: str, user_id: str, slug: str, name: str, agent: SessionAgent | None, vcpus: int, memory_mib: int, status: SessionStatus, running_seconds: int, created_at: str, updated_at: str, url: str)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`id`](#id) | `str` | Canonical session UUID. | `str` | None |

<a id="id"></a>
### `id`

Canonical session UUID.

- Exact shape: `str`
- Returns: `str`
- Raises: None

| [`user_id`](#user_id) | `str` | Canonical owner identifier. | `str` | `ApiError` |

<a id="user_id"></a>
### `user_id`

Canonical owner identifier.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`slug`](#slug) | `str` | Stable service slug. | `str` | `ApiError` |

<a id="slug"></a>
### `slug`

Stable service slug.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`name`](#name) | `str` | Human-readable name. | `str` | `ApiError` |

<a id="name"></a>
### `name`

Human-readable name.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`agent`](#agent) | `SessionAgent | None` | Selected agent; `UNSET` means omitted and `None` means absent in a response. | `SessionAgent | None` | `ApiError` |

<a id="agent"></a>
### `agent`

Selected agent; `UNSET` means omitted and `None` means absent in a response.

- Exact shape: `SessionAgent | None`
- Returns: `SessionAgent | None`
- Raises: `ApiError`

| [`vcpus`](#vcpus) | `int` | Virtual CPU count; create input accepts 1-8 or `UNSET`. | `int` | `ApiError` |

<a id="vcpus"></a>
### `vcpus`

Virtual CPU count; create input accepts 1-8 or `UNSET`.

- Exact shape: `int`
- Returns: `int`
- Raises: `ApiError`

| [`memory_mib`](#memory_mib) | `int` | Memory in MiB; create input accepts 512-16384 or `UNSET`. | `int` | `ApiError` |

<a id="memory_mib"></a>
### `memory_mib`

Memory in MiB; create input accepts 512-16384 or `UNSET`.

- Exact shape: `int`
- Returns: `int`
- Raises: `ApiError`

| [`status`](#status) | `SessionStatus` | HTTP status associated with this API failure. | `SessionStatus` | None |

<a id="status"></a>
### `status`

HTTP status associated with this API failure.

- Exact shape: `SessionStatus`
- Returns: `SessionStatus`
- Raises: None

| [`running_seconds`](#running_seconds) | `int` | Accumulated running time in seconds. | `int` | `ApiError` |

<a id="running_seconds"></a>
### `running_seconds`

Accumulated running time in seconds.

- Exact shape: `int`
- Returns: `int`
- Raises: `ApiError`

| [`created_at`](#created_at) | `str` | Service timestamp encoded as an RFC 3339 string. | `str` | `ApiError` |

<a id="created_at"></a>
### `created_at`

Service timestamp encoded as an RFC 3339 string.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`updated_at`](#updated_at) | `str` | Service timestamp encoded as an RFC 3339 string. | `str` | `ApiError` |

<a id="updated_at"></a>
### `updated_at`

Service timestamp encoded as an RFC 3339 string.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`url`](#url) | `str` | Sensitive capability URL; never log, display, persist, or reuse. | `str` | `ApiError` |

<a id="url"></a>
### `url`

Sensitive capability URL; never log, display, persist, or reuse.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-SESSIONSNAPSHOT` · `TC-091-09`

```python
def session_snapshot(value: SessionSnapshot) -> SessionStatus:
    return value.status
```
