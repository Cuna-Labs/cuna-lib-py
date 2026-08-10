# `AsyncSession`

Client-owned asynchronous session handle.

## Import

`from cuna import AsyncSession`

## Acquisition

Obtain handles from the matching sessions manager; direct construction is unsupported.

## Signature

`AsyncSession(manager: AsyncSessionsManager, snapshot: SessionSnapshot, token: object = None)`

## Artifact docstring

Client-owned asynchronous session handle.

Obtain instances from ``AsyncCuna.sessions``; direct construction raises ``TypeError``.

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
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

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
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`refresh`](#refresh) | `refresh() -> AsyncSession` | Refresh this handle asynchronously. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="refresh"></a>
### `refresh`

Refresh this handle asynchronously.

- Exact shape: `refresh() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

Refresh this handle asynchronously.

Returns:
    This same handle after replacing its snapshot.
Raises:
    ApiError: If the request fails or the response ID is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`start`](#start) | `start() -> AsyncSession` | Start this session asynchronously. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="start"></a>
### `start`

Start this session asynchronously.

- Exact shape: `start() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

Start this session asynchronously.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`pause`](#pause) | `pause() -> AsyncSession` | Pause this session asynchronously. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="pause"></a>
### `pause`

Pause this session asynchronously.

- Exact shape: `pause() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

Pause this session asynchronously.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`resume`](#resume) | `resume() -> AsyncSession` | Resume this session asynchronously. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="resume"></a>
### `resume`

Resume this session asynchronously.

- Exact shape: `resume() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

Resume this session asynchronously.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`stop`](#stop) | `stop() -> AsyncSession` | Stop this session asynchronously. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="stop"></a>
### `stop`

Stop this session asynchronously.

- Exact shape: `stop() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

Stop this session asynchronously.

Returns:
    This handle with the returned snapshot.
Raises:
    ApiError: If the lifecycle request fails or is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`delete`](#delete) | `delete() -> Acknowledgement` | Delete this session asynchronously. | `Acknowledgement` | `ApiError`, `CancelledError` |

<a id="delete"></a>
### `delete`

Delete this session asynchronously.

- Exact shape: `delete() -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ApiError`, `CancelledError`

Delete this session asynchronously.

Returns:
    A successful acknowledgement.
Raises:
    ApiError: If deletion fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`exec`](#exec) | `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult` | Execute a command asynchronously. | `ExecResult` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="exec"></a>
### `exec`

Execute a command asynchronously.

- Exact shape: `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult`
- Returns: `ExecResult`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Execute a command asynchronously.

Args:
    command: Non-empty command string or non-empty argument sequence.
    options: Working directory and 1-600 second timeout options.
Returns:
    Captured exit status, output, truncation flags, and duration.
Raises:
    ConfigError: If the command or options violate the local contract.
    ApiError: If execution fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`checkpoint`](#checkpoint) | `checkpoint(name: str) -> Acknowledgement` | Create a named checkpoint asynchronously. | `Acknowledgement` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="checkpoint"></a>
### `checkpoint`

Create a named checkpoint asynchronously.

- Exact shape: `checkpoint(name: str) -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Create a named checkpoint asynchronously.

Args:
    name: Human-readable checkpoint name of 1-80 characters.
Returns:
    A successful acknowledgement.
Raises:
    ConfigError: If ``name`` violates the local contract.
    ApiError: If the request fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

| [`open`](#open) | `open() -> OpenSessionResult` | Request a new session capability URL asynchronously. | `OpenSessionResult` | `ApiError`, `CancelledError` |

<a id="open"></a>
### `open`

Request a new session capability URL asynchronously.

- Exact shape: `open() -> OpenSessionResult`
- Returns: `OpenSessionResult`
- Raises: `ApiError`, `CancelledError`

Request a new session capability URL asynchronously.

Returns:
    A sensitive result that must be assigned and never logged or displayed.
Raises:
    ApiError: If the request fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`Session`](../sync/Session.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCSESSION`; `TC-091-09`

```python
async def async_session(handle: AsyncSession) -> None:
    refreshed = await handle.refresh()
    result = await handle.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    opened = await handle.open()
    del refreshed, result, opened
```
