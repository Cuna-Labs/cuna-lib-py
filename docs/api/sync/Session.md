# `Session`

Client-owned synchronous session handle.

## Import

`from cuna import Session`

## Acquisition

Obtain handles from the matching sessions manager; direct construction is unsupported.

## Signature

`Session(manager: SessionsManager, snapshot: SessionSnapshot, token: object = None)`

## Artifact docstring

Client-owned synchronous session handle.

Obtain instances from ``Cuna.sessions``; direct construction raises ``TypeError``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`id`](#id) | `str` | Return the canonical session UUID. | `str` | None |

<a id="id"></a>
### `id`

Return the canonical session UUID.

- Exact shape: `str`
- Returns: `str`
- Raises: None

Return the canonical session UUID.

Returns:
    The immutable identifier from the current snapshot.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`snapshot`](#snapshot) | `SessionSnapshot` | Return the latest immutable snapshot. | `SessionSnapshot` | None |

<a id="snapshot"></a>
### `snapshot`

Return the latest immutable snapshot.

- Exact shape: `SessionSnapshot`
- Returns: `SessionSnapshot`
- Raises: None

Return the latest immutable snapshot.

Returns:
    The snapshot retained by this handle.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`refresh`](#refresh) | `refresh() -> Session` | Refresh this handle from the service. | `Session` | `ApiError` |

<a id="refresh"></a>
### `refresh`

Refresh this handle from the service.

- Exact shape: `refresh() -> Session`
- Returns: `Session`
- Raises: `ApiError`

Refresh this handle from the service.

Returns:
    This same handle after replacing its snapshot.
Raises:
    ApiError: If the request fails or the response ID is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`start`](#start) | `start() -> Session` | Start this session. | `Session` | `ApiError` |

<a id="start"></a>
### `start`

Start this session.

- Exact shape: `start() -> Session`
- Returns: `Session`
- Raises: `ApiError`

Start this session.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`pause`](#pause) | `pause() -> Session` | Pause this session. | `Session` | `ApiError` |

<a id="pause"></a>
### `pause`

Pause this session.

- Exact shape: `pause() -> Session`
- Returns: `Session`
- Raises: `ApiError`

Pause this session.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`resume`](#resume) | `resume() -> Session` | Resume this session. | `Session` | `ApiError` |

<a id="resume"></a>
### `resume`

Resume this session.

- Exact shape: `resume() -> Session`
- Returns: `Session`
- Raises: `ApiError`

Resume this session.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`stop`](#stop) | `stop() -> Session` | Stop this session. | `Session` | `ApiError` |

<a id="stop"></a>
### `stop`

Stop this session.

- Exact shape: `stop() -> Session`
- Returns: `Session`
- Raises: `ApiError`

Stop this session.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`delete`](#delete) | `delete() -> Acknowledgement` | Delete this session. | `Acknowledgement` | `ApiError` |

<a id="delete"></a>
### `delete`

Delete this session.

- Exact shape: `delete() -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ApiError`

Delete this session.

Returns:
    A successful acknowledgement.
Raises:
    ApiError: If deletion fails or the response is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`exec`](#exec) | `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult` | Execute a command in this session. | `ExecResult` | `ConfigError`, `ApiError` |

<a id="exec"></a>
### `exec`

Execute a command in this session.

- Exact shape: `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult`
- Returns: `ExecResult`
- Raises: `ConfigError`, `ApiError`

Execute a command in this session.

Args:
    command: Non-empty command string or non-empty argument sequence.
    options: Working directory and 1-600 second timeout options.
Returns:
    Captured exit status, output, truncation flags, and duration.
Raises:
    ConfigError: If the command or options violate the local contract.
    ApiError: If execution fails or the response is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`checkpoint`](#checkpoint) | `checkpoint(name: str) -> Acknowledgement` | Create a named checkpoint. | `Acknowledgement` | `ConfigError`, `ApiError` |

<a id="checkpoint"></a>
### `checkpoint`

Create a named checkpoint.

- Exact shape: `checkpoint(name: str) -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ConfigError`, `ApiError`

Create a named checkpoint.

Args:
    name: Human-readable checkpoint name of 1-80 characters.
Returns:
    A successful acknowledgement.
Raises:
    ConfigError: If ``name`` violates the local contract.
    ApiError: If the request fails or the response is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

| [`open`](#open) | `open() -> OpenSessionResult` | Request a new session capability URL. | `OpenSessionResult` | `ApiError` |

<a id="open"></a>
### `open`

Request a new session capability URL.

- Exact shape: `open() -> OpenSessionResult`
- Returns: `OpenSessionResult`
- Raises: `ApiError`

Request a new session capability URL.

Returns:
    A sensitive result that must be assigned and never logged or displayed.
Raises:
    ApiError: If the request fails or the response is malformed.
Examples:
    See ``REF-EX-SESSION`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`AsyncSession`](../async/AsyncSession.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-SESSION`; `TC-091-09`

```python
def session(handle: Session) -> None:
    refreshed = handle.refresh()
    result = handle.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    opened = handle.open()
    del refreshed, result, opened
```
