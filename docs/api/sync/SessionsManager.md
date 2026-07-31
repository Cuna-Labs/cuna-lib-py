# `SessionsManager`

Stable synchronous session manager; obtain from :attr:`Runa.sessions`.

## Import

`from runa import SessionsManager`

## Signature

`SessionsManagerSessionsManager(client: Runa, token: object = None)`

## Public members and fields

| Name | Kind | Signature or annotation | Summary |
| --- | --- | --- | --- |
| `create` | Kind.FUNCTION | `create(name: str, options: SessionCreateOptions) -> Session` | Missing from candidate docstring. |
| `list` | Kind.FUNCTION | `list() -> list[Session]` | Missing from candidate docstring. |
| `get` | Kind.FUNCTION | `get(session_id: str) -> Session` | Missing from candidate docstring. |

## Sync/async pair

See [`AsyncSessionsManager`](../async/AsyncSessionsManager.md).

## Raises and examples

Raises information and safe examples must come from candidate-wheel docstrings.
