# `SessionStatus`

Session lifecycle state.

## Import

`from runa import SessionStatus`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Session lifecycle state.

Attributes:
    CREATING: Provisioning is in progress.
    RUNNING: The session is running.
    PAUSED: The session is paused.
    SUSPENDED: The service suspended the session.
    STOPPED: The session is stopped.
    DELETED: The session was deleted.
    ERROR: The session entered an error state.
Examples:
    See ``REF-EX-SESSIONSTATUS`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `CREATING` | `value` | Accepted `CREATING` value defined by the public contract. |
| `RUNNING` | `value` | Accepted `RUNNING` value defined by the public contract. |
| `PAUSED` | `value` | Accepted `PAUSED` value defined by the public contract. |
| `SUSPENDED` | `value` | Accepted `SUSPENDED` value defined by the public contract. |
| `STOPPED` | `value` | Accepted `STOPPED` value defined by the public contract. |
| `DELETED` | `value` | Accepted `DELETED` value defined by the public contract. |
| `ERROR` | `value` | Accepted `ERROR` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-SESSIONSTATUS`; `TC-091-09`

```python
def session_status() -> SessionStatus:
    return SessionStatus.RUNNING
```
