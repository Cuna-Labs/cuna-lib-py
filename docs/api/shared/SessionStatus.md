# `SessionStatus`

Closed set of session lifecycle states.

## Import

`from runa import SessionStatus`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`CREATING`](#CREATING) | `value` | Accepted `CREATING` value defined by the public contract. | `value` | `ApiError` |

<a id="CREATING"></a>
### `CREATING`

Accepted `CREATING` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`RUNNING`](#RUNNING) | `value` | Accepted `RUNNING` value defined by the public contract. | `value` | `ApiError` |

<a id="RUNNING"></a>
### `RUNNING`

Accepted `RUNNING` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`PAUSED`](#PAUSED) | `value` | Accepted `PAUSED` value defined by the public contract. | `value` | `ApiError` |

<a id="PAUSED"></a>
### `PAUSED`

Accepted `PAUSED` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`SUSPENDED`](#SUSPENDED) | `value` | Accepted `SUSPENDED` value defined by the public contract. | `value` | `ApiError` |

<a id="SUSPENDED"></a>
### `SUSPENDED`

Accepted `SUSPENDED` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`STOPPED`](#STOPPED) | `value` | Accepted `STOPPED` value defined by the public contract. | `value` | `ApiError` |

<a id="STOPPED"></a>
### `STOPPED`

Accepted `STOPPED` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`DELETED`](#DELETED) | `value` | Accepted `DELETED` value defined by the public contract. | `value` | `ApiError` |

<a id="DELETED"></a>
### `DELETED`

Accepted `DELETED` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`ERROR`](#ERROR) | `value` | Accepted `ERROR` value defined by the public contract. | `value` | `ApiError` |

<a id="ERROR"></a>
### `ERROR`

Accepted `ERROR` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-SESSIONSTATUS` · `TC-091-09`

```python
def session_status() -> SessionStatus:
    return SessionStatus.RUNNING
```
