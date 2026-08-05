# `SessionCreateOptions`

Omission-aware session creation options.

## Import

`from runa import SessionCreateOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`SessionCreateOptions(agent: SessionAgent | UnsetType = UNSET, background: bool | UnsetType = UNSET, vcpus: int | UnsetType = UNSET, memory_mib: int | UnsetType = UNSET, allowed_hosts: list[str] | UnsetType = UNSET, outbound_policy: OutboundPolicy | UnsetType = UNSET, runtime_port: int | UnsetType = UNSET)`

## Artifact docstring

Omission-aware session creation options.

Attributes:
    agent: Agent or ``UNSET``.
    background: Whether creation may return while provisioning is still in progress. It
        defaults to ``True`` for interactive Claude Code and Codex sessions; pass
        ``False`` to request the legacy synchronous create behavior.
    vcpus: Integer from 1 through 8 or ``UNSET``.
    memory_mib: Integer from 512 through 16384 or ``UNSET``.
    allowed_hosts: Legacy allow list or ``UNSET``.
    outbound_policy: Explicit allow-list or deny-list policy or ``UNSET``.
    runtime_port: Integer from 1 through 65535 or ``UNSET``.
Examples:
    See ``REF-EX-SESSIONCREATEOPTIONS`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `agent` | `SessionAgent | UnsetType` | Selected agent; `UNSET` means omitted and `None` means absent in a response. |
| `background` | `bool | UnsetType` | Whether creation may return during provisioning; `UNSET` applies the interactive-agent default. |
| `vcpus` | `int | UnsetType` | Virtual CPU count; create input accepts 1-8 or `UNSET`. |
| `memory_mib` | `int | UnsetType` | Memory in MiB; create input accepts 512-16384 or `UNSET`. |
| `allowed_hosts` | `list[str] | UnsetType` | Explicit allowlist of at most 128 non-empty hosts; `UNSET` means omitted. |
| `outbound_policy` | `OutboundPolicy | UnsetType` | Accepted `outbound_policy` value defined by the public contract. |
| `runtime_port` | `int | UnsetType` | Runtime port 1-65535; `UNSET` means omitted. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-SESSIONCREATEOPTIONS`; `TC-091-09`

```python
def session_create_options() -> SessionCreateOptions:
    return SessionCreateOptions(
        agent=SessionAgent.CODEX,
        background=True,
        memory_mib=2048,
    )
```
