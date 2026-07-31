# `AsyncSession`

Client-owned asynchronous handle for one session.

## Import

`from runa import AsyncSession`

## Acquisition

Obtain handles from the matching sessions manager; direct construction is unsupported.

## Signature

`AsyncSession(manager: AsyncSessionsManager, snapshot: SessionSnapshot, token: object = None)`

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

| [`snapshot`](#snapshot) | `SessionSnapshot` | Latest immutable snapshot retained by this handle. | `SessionSnapshot` | None |

<a id="snapshot"></a>
### `snapshot`

Latest immutable snapshot retained by this handle.

- Exact shape: `SessionSnapshot`
- Returns: `SessionSnapshot`
- Raises: None

| [`refresh`](#refresh) | `refresh() -> AsyncSession` | Replace this handle's snapshot with the latest server state. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="refresh"></a>
### `refresh`

Replace this handle's snapshot with the latest server state.

- Exact shape: `refresh() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

| [`start`](#start) | `start() -> AsyncSession` | Start this session and refresh its snapshot. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="start"></a>
### `start`

Start this session and refresh its snapshot.

- Exact shape: `start() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

| [`pause`](#pause) | `pause() -> AsyncSession` | Pause this session and refresh its snapshot. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="pause"></a>
### `pause`

Pause this session and refresh its snapshot.

- Exact shape: `pause() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

| [`resume`](#resume) | `resume() -> AsyncSession` | Resume this session and refresh its snapshot. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="resume"></a>
### `resume`

Resume this session and refresh its snapshot.

- Exact shape: `resume() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

| [`stop`](#stop) | `stop() -> AsyncSession` | Stop this session and refresh its snapshot. | `AsyncSession` | `ApiError`, `CancelledError` |

<a id="stop"></a>
### `stop`

Stop this session and refresh its snapshot.

- Exact shape: `stop() -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ApiError`, `CancelledError`

| [`delete`](#delete) | `delete() -> Acknowledgement` | Delete this session and return an acknowledgement. | `Acknowledgement` | `ApiError`, `CancelledError` |

<a id="delete"></a>
### `delete`

Delete this session and return an acknowledgement.

- Exact shape: `delete() -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ApiError`, `CancelledError`

| [`exec`](#exec) | `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult` | Execute a non-empty command with optional working directory and timeout. | `ExecResult` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="exec"></a>
### `exec`

Execute a non-empty command with optional working directory and timeout.

- Exact shape: `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult`
- Returns: `ExecResult`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

| [`checkpoint`](#checkpoint) | `checkpoint(name: str) -> Acknowledgement` | Create a checkpoint with a 1-80 character name. | `Acknowledgement` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="checkpoint"></a>
### `checkpoint`

Create a checkpoint with a 1-80 character name.

- Exact shape: `checkpoint(name: str) -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

| [`open`](#open) | `open() -> OpenSessionResult` | Request a new capability URL; assign the result and do not log or display it. | `OpenSessionResult` | `ApiError`, `CancelledError` |

<a id="open"></a>
### `open`

Request a new capability URL; assign the result and do not log or display it.

- Exact shape: `open() -> OpenSessionResult`
- Returns: `OpenSessionResult`
- Raises: `ApiError`, `CancelledError`

## Sync/async pair

See the behaviorally equivalent [`Session`](../sync/Session.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ASYNCSESSION` · `TC-091-09`

```python
async def async_session(handle: AsyncSession) -> None:
    refreshed = await handle.refresh()
    result = await handle.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    opened = await handle.open()
    del refreshed, result, opened
```
