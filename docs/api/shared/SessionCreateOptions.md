# `SessionCreateOptions`

Omission-aware session creation options.

## Import

`from runa import SessionCreateOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`SessionCreateOptions(agent: SessionAgent | UnsetType = UNSET, vcpus: int | UnsetType = UNSET, memory_mib: int | UnsetType = UNSET, allowed_hosts: list[str] | UnsetType = UNSET, runtime_port: int | UnsetType = UNSET)`

## Artifact docstring

Omission-aware session creation options.

Attributes:
    agent: Agent or ``UNSET``.
    vcpus: Integer from 1 through 8 or ``UNSET``.
    memory_mib: Integer from 512 through 16384 or ``UNSET``.
    allowed_hosts: At most 128 non-empty hosts or ``UNSET``.
    runtime_port: Integer from 1 through 65535 or ``UNSET``.
Examples:
    See ``REF-EX-SESSIONCREATEOPTIONS`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `agent` | `SessionAgent | UnsetType` | Selected agent; `UNSET` means omitted and `None` means absent in a response. |
| `vcpus` | `int | UnsetType` | Virtual CPU count; create input accepts 1-8 or `UNSET`. |
| `memory_mib` | `int | UnsetType` | Memory in MiB; create input accepts 512-16384 or `UNSET`. |
| `allowed_hosts` | `list[str] | UnsetType` | Explicit allowlist of at most 128 non-empty hosts; `UNSET` means omitted. |
| `runtime_port` | `int | UnsetType` | Runtime port 1-65535; `UNSET` means omitted. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-SESSIONCREATEOPTIONS`; `TC-091-09`

```python
def session_create_options() -> SessionCreateOptions:
    return SessionCreateOptions(agent=SessionAgent.CODEX, memory_mib=2048)
```
