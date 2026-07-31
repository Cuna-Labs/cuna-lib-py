# Exec

Use a text command or argument vector and optional `ExecOptions`, as shown by
[`examples/sync_exec.py`](../../examples/sync_exec.py) and
[`examples/async_exec.py`](../../examples/async_exec.py). The result is one buffered six-field
`ExecResult`: exit code, stdout, stderr, duration, and two truncation flags. It is not a stream;
non-zero exit does not by itself raise `CommandError`. See the [API reference](../api/README.md).
