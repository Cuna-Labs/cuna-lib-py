# `AsyncSession`

Documentation summary is missing from the candidate wheel.

## Import

`from runa import AsyncSession`

## Signature

`AsyncSessionAsyncSession(manager: AsyncSessionsManager, snapshot: SessionSnapshot, token: object = None)`

## Public members and fields

| Name | Kind | Signature or annotation | Summary |
| --- | --- | --- | --- |
| `id` | Kind.ATTRIBUTE | `str` | Missing from candidate docstring. |
| `snapshot` | Kind.ATTRIBUTE | `SessionSnapshot` | Missing from candidate docstring. |
| `refresh` | Kind.FUNCTION | `refresh() -> AsyncSession` | Missing from candidate docstring. |
| `start` | Kind.FUNCTION | `start() -> AsyncSession` | Missing from candidate docstring. |
| `pause` | Kind.FUNCTION | `pause() -> AsyncSession` | Missing from candidate docstring. |
| `resume` | Kind.FUNCTION | `resume() -> AsyncSession` | Missing from candidate docstring. |
| `stop` | Kind.FUNCTION | `stop() -> AsyncSession` | Missing from candidate docstring. |
| `delete` | Kind.FUNCTION | `delete() -> Acknowledgement` | Missing from candidate docstring. |
| `exec` | Kind.FUNCTION | `exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult` | Missing from candidate docstring. |
| `checkpoint` | Kind.FUNCTION | `checkpoint(name: str) -> Acknowledgement` | Missing from candidate docstring. |
| `open` | Kind.FUNCTION | `open() -> OpenSessionResult` | Missing from candidate docstring. |

## Sync/async pair

See [`Session`](../sync/Session.md).

## Raises and examples

Raises information and safe examples must come from candidate-wheel docstrings.
