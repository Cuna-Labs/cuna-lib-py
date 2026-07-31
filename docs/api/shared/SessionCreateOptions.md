# `SessionCreateOptions`

Optional, omission-aware inputs for session creation.

## Import

`from runa import SessionCreateOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`SessionCreateOptions(agent: SessionAgent | UnsetType = UNSET, vcpus: int | UnsetType = UNSET, memory_mib: int | UnsetType = UNSET, allowed_hosts: list[str] | UnsetType = UNSET, runtime_port: int | UnsetType = UNSET)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`agent`](#agent) | `SessionAgent | UnsetType` | Selected agent; `UNSET` means omitted and `None` means absent in a response. | `SessionAgent | UnsetType` | `ApiError` |

<a id="agent"></a>
### `agent`

Selected agent; `UNSET` means omitted and `None` means absent in a response.

- Exact shape: `SessionAgent | UnsetType`
- Returns: `SessionAgent | UnsetType`
- Raises: `ApiError`

| [`vcpus`](#vcpus) | `int | UnsetType` | Virtual CPU count; create input accepts 1-8 or `UNSET`. | `int | UnsetType` | `ApiError` |

<a id="vcpus"></a>
### `vcpus`

Virtual CPU count; create input accepts 1-8 or `UNSET`.

- Exact shape: `int | UnsetType`
- Returns: `int | UnsetType`
- Raises: `ApiError`

| [`memory_mib`](#memory_mib) | `int | UnsetType` | Memory in MiB; create input accepts 512-16384 or `UNSET`. | `int | UnsetType` | `ApiError` |

<a id="memory_mib"></a>
### `memory_mib`

Memory in MiB; create input accepts 512-16384 or `UNSET`.

- Exact shape: `int | UnsetType`
- Returns: `int | UnsetType`
- Raises: `ApiError`

| [`allowed_hosts`](#allowed_hosts) | `list[str] | UnsetType` | Explicit allowlist of at most 128 non-empty hosts; `UNSET` means omitted. | `list[str] | UnsetType` | `ApiError` |

<a id="allowed_hosts"></a>
### `allowed_hosts`

Explicit allowlist of at most 128 non-empty hosts; `UNSET` means omitted.

- Exact shape: `list[str] | UnsetType`
- Returns: `list[str] | UnsetType`
- Raises: `ApiError`

| [`runtime_port`](#runtime_port) | `int | UnsetType` | Runtime port 1-65535; `UNSET` means omitted. | `int | UnsetType` | `ApiError` |

<a id="runtime_port"></a>
### `runtime_port`

Runtime port 1-65535; `UNSET` means omitted.

- Exact shape: `int | UnsetType`
- Returns: `int | UnsetType`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-SESSIONCREATEOPTIONS` · `TC-091-09`

```python
def session_create_options() -> SessionCreateOptions:
    return SessionCreateOptions(agent=SessionAgent.CODEX, memory_mib=2048)
```
