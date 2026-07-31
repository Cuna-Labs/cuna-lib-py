# `SessionSnapshot`

Immutable session state.

## Import

`from runa import SessionSnapshot`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`SessionSnapshot(id: str, user_id: str, slug: str, name: str, agent: SessionAgent | None, vcpus: int, memory_mib: int, status: SessionStatus, running_seconds: int, created_at: str, updated_at: str, url: str)`

## Artifact docstring

Immutable session state.

Attributes:
    id: Canonical session UUID.
    user_id: Canonical owner identifier.
    slug: Stable service slug.
    name: Human-readable session name.
    agent: Selected agent or ``None``.
    vcpus: Allocated virtual CPUs.
    memory_mib: Allocated memory in MiB.
    status: Current lifecycle state.
    running_seconds: Accumulated running time.
    created_at: RFC 3339 creation timestamp.
    updated_at: RFC 3339 update timestamp.
    url: Sensitive capability URL; never log, display, persist, or reuse.
Examples:
    See ``REF-EX-SESSIONSNAPSHOT`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `id` | `str` | Canonical identifier. |
| `user_id` | `str` | Canonical owner identifier. |
| `slug` | `str` | Stable service slug. |
| `name` | `str` | Human-readable name. |
| `agent` | `SessionAgent | None` | Selected agent; `UNSET` means omitted and `None` means absent in a response. |
| `vcpus` | `int` | Virtual CPU count; create input accepts 1-8 or `UNSET`. |
| `memory_mib` | `int` | Memory in MiB; create input accepts 512-16384 or `UNSET`. |
| `status` | `SessionStatus` | Current lifecycle state. |
| `running_seconds` | `int` | Accumulated running time in seconds. |
| `created_at` | `str` | Service timestamp encoded as an RFC 3339 string. |
| `updated_at` | `str` | Service timestamp encoded as an RFC 3339 string. |
| `url` | `str` | Sensitive capability URL; never log, display, persist, or reuse. |

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-SESSIONSNAPSHOT` · `TC-091-09`

```python
def session_snapshot(value: SessionSnapshot) -> SessionStatus:
    return value.status
```
