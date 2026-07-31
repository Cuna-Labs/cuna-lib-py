# `Session`

Client-owned synchronous handle for one session.

## Import

`from runa import Session`

## Acquisition

Obtain handles from the matching sessions manager; direct construction is unsupported.

## Signature

`Session(manager: SessionsManager, snapshot: SessionSnapshot, token: object = None)`

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

| [`refresh`](#refresh) | `refresh() -> Session` | Replace this handle's snapshot with the latest server state. | `Session` | `ApiError` |

<a id="refresh"></a>
### `refresh`

Replace this handle's snapshot with the latest server state.

- Exact shape: `refresh() -> Session`
- Returns: `Session`
- Raises: `ApiError`

| [`start`](#start) | `start() -> Session` | Start this session and refresh its snapshot. | `Session` | `ApiError` |

<a id="start"></a>
### `start`

Start this session and refresh its snapshot.

- Exact shape: `start() -> Session`
- Returns: `Session`
- Raises: `ApiError`

| [`pause`](#pause) | `pause() -> Session` | Pause this session and refresh its snapshot. | `Session` | `ApiError` |

<a id="pause"></a>
### `pause`

Pause this session and refresh its snapshot.

- Exact shape: `pause() -> Session`
- Returns: `Session`
- Raises: `ApiError`

| [`resume`](#resume) | `resume() -> Session` | Resume this session and refresh its snapshot. | `Session` | `ApiError` |

<a id="resume"></a>
### `resume`

Resume this session and refresh its snapshot.

- Exact shape: `resume() -> Session`
- Returns: `Session`
- Raises: `ApiError`

| [`stop`](#stop) | `stop() -> Session` | Stop this session and refresh its snapshot. | `Session` | `ApiError` |

<a id="stop"></a>
### `stop`

Stop this session and refresh its snapshot.

- Exact shape: `stop() -> Session`
- Returns: `Session`
- Raises: `ApiError`

| [`delete`](#delete) | `delete() -> Acknowledgement` | Delete this session and return an acknowledgement. | `Acknowledgement` | `ApiError` |

<a id="delete"></a>
### `delete`

Delete this session and return an acknowledgement.

- Exact shape: `delete() -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ApiError`

| [`exec`](#exec) | `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult` | Execute a non-empty command with optional working directory and timeout. | `ExecResult` | `ConfigError`, `ApiError` |

<a id="exec"></a>
### `exec`

Execute a non-empty command with optional working directory and timeout.

- Exact shape: `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult`
- Returns: `ExecResult`
- Raises: `ConfigError`, `ApiError`

| [`checkpoint`](#checkpoint) | `checkpoint(name: str) -> Acknowledgement` | Create a checkpoint with a 1-80 character name. | `Acknowledgement` | `ConfigError`, `ApiError` |

<a id="checkpoint"></a>
### `checkpoint`

Create a checkpoint with a 1-80 character name.

- Exact shape: `checkpoint(name: str) -> Acknowledgement`
- Returns: `Acknowledgement`
- Raises: `ConfigError`, `ApiError`

| [`open`](#open) | `open() -> OpenSessionResult` | Request a new capability URL; assign the result and do not log or display it. | `OpenSessionResult` | `ApiError` |

<a id="open"></a>
### `open`

Request a new capability URL; assign the result and do not log or display it.

- Exact shape: `open() -> OpenSessionResult`
- Returns: `OpenSessionResult`
- Raises: `ApiError`

## Sync/async pair

See the behaviorally equivalent [`AsyncSession`](../async/AsyncSession.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-SESSION` · `TC-091-09`

```python
def session(handle: Session) -> None:
    refreshed = handle.refresh()
    result = handle.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    opened = handle.open()
    del refreshed, result, opened
```
