# `Session`

Client-owned synchronous session handle.

## Import

`from runa import Session`

## Signature

`SessionSession(manager: SessionsManager, snapshot: SessionSnapshot, token: object = None)`

## Public members and fields

| Name | Kind | Signature or annotation | Summary |
| --- | --- | --- | --- |
| `id` | Kind.ATTRIBUTE | `str` | Missing from candidate docstring. |
| `snapshot` | Kind.ATTRIBUTE | `SessionSnapshot` | Missing from candidate docstring. |
| `refresh` | Kind.FUNCTION | `refresh() -> Session` | Missing from candidate docstring. |
| `start` | Kind.FUNCTION | `start() -> Session` | Missing from candidate docstring. |
| `pause` | Kind.FUNCTION | `pause() -> Session` | Missing from candidate docstring. |
| `resume` | Kind.FUNCTION | `resume() -> Session` | Missing from candidate docstring. |
| `stop` | Kind.FUNCTION | `stop() -> Session` | Missing from candidate docstring. |
| `delete` | Kind.FUNCTION | `delete() -> Acknowledgement` | Missing from candidate docstring. |
| `exec` | Kind.FUNCTION | `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult` | Missing from candidate docstring. |
| `checkpoint` | Kind.FUNCTION | `checkpoint(name: str) -> Acknowledgement` | Missing from candidate docstring. |
| `open` | Kind.FUNCTION | `open() -> OpenSessionResult` | Missing from candidate docstring. |

## Sync/async pair

See [`AsyncSession`](../async/AsyncSession.md).

## Raises and examples

Raises information and safe examples must come from candidate-wheel docstrings.
