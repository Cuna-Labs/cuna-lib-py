"""Build and prove the deterministic API reference from a clean candidate wheel."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from importlib.metadata import version
from pathlib import Path
from typing import Any

import griffe

ERROR_MANIFEST = ("ApiError", "CommandError", "ConfigError", "RunaError")
ROOT_MANIFEST = (
    "Acknowledgement",
    "AssignedWorkspace",
    "AsyncRecordsManager",
    "AsyncRuna",
    "AsyncSession",
    "AsyncSessionsManager",
    "EstimatedUsage",
    "ExecOptions",
    "ExecResult",
    "Me",
    "OpenSessionResult",
    "Record",
    "RecordsManager",
    "Runa",
    "Session",
    "SessionAgent",
    "SessionCreateOptions",
    "SessionSnapshot",
    "SessionsManager",
    "SessionStatus",
    "UNSET",
    "UnassignedWorkspace",
    "UnsetType",
)
EXTENSIONS: list[str] = []
VALID_TEST_IDS = {f"TC-091-{number:02d}" for number in range(1, 12)}
SECTIONS = {
    "sync": ("Runa", "SessionsManager", "RecordsManager", "Session"),
    "async": ("AsyncRuna", "AsyncSessionsManager", "AsyncRecordsManager", "AsyncSession"),
    "shared": tuple(
        name
        for name in ROOT_MANIFEST
        if not name.startswith("Async")
        and name not in {"Runa", "SessionsManager", "RecordsManager", "Session"}
    ),
    "errors": ERROR_MANIFEST,
}
PAIRS = {
    "Runa": "AsyncRuna",
    "SessionsManager": "AsyncSessionsManager",
    "RecordsManager": "AsyncRecordsManager",
    "Session": "AsyncSession",
    "AsyncRuna": "Runa",
    "AsyncSessionsManager": "SessionsManager",
    "AsyncRecordsManager": "RecordsManager",
    "AsyncSession": "Session",
}
SUMMARIES = {
    "Runa": "Synchronous root client for an authenticated Runa workspace.",
    "AsyncRuna": "Asynchronous root client for an authenticated Runa workspace.",
    "SessionsManager": "Synchronous entry point for creating, listing, and retrieving sessions.",
    "AsyncSessionsManager": (
        "Asynchronous entry point for creating, listing, and retrieving sessions."
    ),
    "RecordsManager": "Synchronous entry point for listing workspace records.",
    "AsyncRecordsManager": "Asynchronous entry point for listing workspace records.",
    "Session": "Client-owned synchronous handle for one session.",
    "AsyncSession": "Client-owned asynchronous handle for one session.",
    "SessionSnapshot": "Immutable snapshot of one session returned by the service.",
    "SessionCreateOptions": "Optional, omission-aware inputs for session creation.",
    "ExecOptions": "Optional, omission-aware inputs for command execution.",
    "ExecResult": "Immutable result of a completed session command.",
    "Acknowledgement": "Immutable acknowledgement returned by accepted mutating operations.",
    "OpenSessionResult": "Capability-bearing result returned when opening a session.",
    "Record": "Immutable record visible to the authenticated workspace.",
    "EstimatedUsage": "Estimated workspace spend and remaining balance.",
    "AssignedWorkspace": "Workspace state for an assigned account.",
    "UnassignedWorkspace": "Workspace state for a waitlisted account.",
    "Me": "Authenticated account and workspace state.",
    "SessionStatus": "Closed set of session lifecycle states.",
    "SessionAgent": "Closed set of supported session agents.",
    "UnsetType": "Nonconstructible type of the sole omission marker.",
    "UNSET": "Sole public marker meaning that an optional field is omitted.",
    "RunaError": "Immutable nonconstructible base of normalized SDK errors.",
    "ConfigError": "Safe configuration or local-input failure.",
    "ApiError": "Safe API, transport, status, or malformed-response failure.",
    "CommandError": "Reserved nonconstructible compatibility error; v1 never raises it.",
}
MEMBER_MEANINGS = {
    "sessions": "Stable manager owned by this client.",
    "records": "Stable manager owned by this client.",
    "me": "Read the authenticated account and workspace state.",
    "close": "Close client-owned transport resources; repeated calls are safe.",
    "create": "Create one session from a 1-80 character name and explicit options.",
    "list": "List the resources visible to the authenticated workspace.",
    "get": "Retrieve one session by canonical UUID.",
    "id": "Canonical session UUID.",
    "snapshot": "Latest immutable snapshot retained by this handle.",
    "refresh": "Replace this handle's snapshot with the latest server state.",
    "start": "Start this session and refresh its snapshot.",
    "pause": "Pause this session and refresh its snapshot.",
    "resume": "Resume this session and refresh its snapshot.",
    "stop": "Stop this session and refresh its snapshot.",
    "delete": "Delete this session and return an acknowledgement.",
    "exec": "Execute a non-empty command with optional working directory and timeout.",
    "checkpoint": "Create a checkpoint with a 1-80 character name.",
    "open": "Request a new capability URL; assign the result and do not log or display it.",
    "code": "Stable disclosure-safe error category.",
    "message": "Stable disclosure-safe English error message.",
    "status": "HTTP status associated with this API failure.",
}
FIELD_MEANINGS = {
    "agent": "Selected agent; `UNSET` means omitted and `None` means absent in a response.",
    "allowed_hosts": "Explicit allowlist of at most 128 non-empty hosts; `UNSET` means omitted.",
    "assigned": "Discriminator for the workspace union.",
    "created_at": "Service timestamp encoded as an RFC 3339 string.",
    "cwd": "Command working directory; `UNSET` means omitted.",
    "detail": "Contract-defined record detail retained without hidden filtering.",
    "duration_ms": "Command duration in milliseconds.",
    "email": "Authenticated account email address.",
    "estimated_remaining_usd": "Estimated remaining USD balance.",
    "estimated_spend_usd": "Estimated USD spend.",
    "exit_code": "Process exit code.",
    "id": "Canonical identifier.",
    "kind": "Record kind discriminator.",
    "memory_mib": "Memory in MiB; create input accepts 512-16384 or `UNSET`.",
    "name": "Human-readable name.",
    "note": "Service-provided usage note.",
    "ok": "Literal `True` acknowledgement.",
    "running_seconds": "Accumulated running time in seconds.",
    "runtime_port": "Runtime port 1-65535; `UNSET` means omitted.",
    "session_id": "Canonical parent session UUID.",
    "slug": "Stable service slug.",
    "status": "Current lifecycle state.",
    "stderr": "Captured standard error.",
    "stderr_truncated": "Whether standard error was truncated.",
    "stdout": "Captured standard output.",
    "stdout_truncated": "Whether standard output was truncated.",
    "summary": "Disclosure-safe record summary.",
    "timeout_secs": "Execution timeout 1-600 seconds; `UNSET` means omitted.",
    "updated_at": "Service timestamp encoded as an RFC 3339 string.",
    "url": "Sensitive capability URL; never log, display, persist, or reuse.",
    "usage": "Estimated usage for an assigned workspace.",
    "user_id": "Canonical owner identifier.",
    "vcpus": "Virtual CPU count; create input accepts 1-8 or `UNSET`.",
    "waitlist_position": "Current one-based waitlist position.",
    "workspace": "Assigned or unassigned workspace state.",
}
EXPECTED_MEMBERS = {
    "Runa": ("sessions", "records", "me", "close"),
    "SessionsManager": ("create", "list", "get"),
    "RecordsManager": ("list",),
    "Session": (
        "id",
        "snapshot",
        "refresh",
        "start",
        "pause",
        "resume",
        "stop",
        "delete",
        "exec",
        "checkpoint",
        "open",
    ),
    "AsyncRuna": ("sessions", "records", "me", "close"),
    "AsyncSessionsManager": ("create", "list", "get"),
    "AsyncRecordsManager": ("list",),
    "AsyncSession": (
        "id",
        "snapshot",
        "refresh",
        "start",
        "pause",
        "resume",
        "stop",
        "delete",
        "exec",
        "checkpoint",
        "open",
    ),
    "RunaError": ("code", "message"),
    "ApiError": ("status",),
    "ConfigError": (),
    "CommandError": (),
    "Acknowledgement": ("ok",),
    "AssignedWorkspace": ("assigned", "usage"),
    "EstimatedUsage": ("estimated_spend_usd", "estimated_remaining_usd", "note"),
    "ExecOptions": ("cwd", "timeout_secs"),
    "ExecResult": (
        "exit_code",
        "stdout",
        "stderr",
        "duration_ms",
        "stdout_truncated",
        "stderr_truncated",
    ),
    "Me": ("id", "email", "workspace"),
    "OpenSessionResult": ("url",),
    "Record": ("id", "session_id", "kind", "summary", "detail", "created_at"),
    "SessionAgent": ("CLAUDE_CODE", "CODEX", "OPENCLAW"),
    "SessionCreateOptions": ("agent", "vcpus", "memory_mib", "allowed_hosts", "runtime_port"),
    "SessionSnapshot": (
        "id",
        "user_id",
        "slug",
        "name",
        "agent",
        "vcpus",
        "memory_mib",
        "status",
        "running_seconds",
        "created_at",
        "updated_at",
        "url",
    ),
    "SessionStatus": (
        "CREATING",
        "RUNNING",
        "PAUSED",
        "SUSPENDED",
        "STOPPED",
        "DELETED",
        "ERROR",
    ),
    "UNSET": (),
    "UnassignedWorkspace": ("assigned", "waitlist_position"),
    "UnsetType": (),
}
RAISES = {
    "Runa": ("ConfigError",),
    "AsyncRuna": ("ConfigError",),
    "SessionsManager.create": ("ConfigError", "ApiError"),
    "AsyncSessionsManager.create": ("ConfigError", "ApiError", "CancelledError"),
    "SessionsManager.get": ("ConfigError", "ApiError"),
    "AsyncSessionsManager.get": ("ConfigError", "ApiError", "CancelledError"),
    "Session.exec": ("ConfigError", "ApiError"),
    "AsyncSession.exec": ("ConfigError", "ApiError", "CancelledError"),
    "Session.checkpoint": ("ConfigError", "ApiError"),
    "AsyncSession.checkpoint": ("ConfigError", "ApiError", "CancelledError"),
}
EXPECTED_SIGNATURES = {
    "Runa": (
        "Runa(*, api_key: str | None = None, base_url: str | None = None, "
        "config_file: str | os.PathLike[str] | None = None, "
        "transport: SyncTransport | None = None, diagnostic_sink: object | None = None, "
        "trace_sink: object | None = None)"
    ),
    "AsyncRuna": (
        "AsyncRuna(*, api_key: str | None = None, base_url: str | None = None, "
        "config_file: str | os.PathLike[str] | None = None, "
        "diagnostic_sink: object | None = None, trace_sink: object | None = None)"
    ),
    "SessionsManager.create": "create(name: str, options: SessionCreateOptions) -> Session",
    "SessionsManager.list": "list() -> list[Session]",
    "SessionsManager.get": "get(session_id: str) -> Session",
    "RecordsManager.list": "list() -> list[Record]",
    "Session.exec": (
        "exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult"
    ),
    "Session.checkpoint": "checkpoint(name: str) -> Acknowledgement",
    "Session.open": "open() -> OpenSessionResult",
    "AsyncSessionsManager.create": (
        "create(name: str, options: SessionCreateOptions) -> AsyncSession"
    ),
    "AsyncSessionsManager.list": "list() -> list[AsyncSession]",
    "AsyncSessionsManager.get": "get(session_id: str) -> AsyncSession",
    "AsyncRecordsManager.list": "list() -> list[Record]",
    "AsyncSession.exec": (
        "exec(command: str | Sequence[str], options: ExecOptions = ExecOptions()) -> ExecResult"
    ),
    "AsyncSession.checkpoint": "checkpoint(name: str) -> Acknowledgement",
    "AsyncSession.open": "open() -> OpenSessionResult",
    "Acknowledgement": "Acknowledgement(ok: Literal[True])",
    "AssignedWorkspace": "AssignedWorkspace(assigned: Literal[True], usage: EstimatedUsage)",
    "EstimatedUsage": (
        "EstimatedUsage(estimated_spend_usd: int | float, "
        "estimated_remaining_usd: int | float, note: str)"
    ),
    "ExecOptions": (
        "ExecOptions(cwd: str | UnsetType = UNSET, "
        "timeout_secs: int | UnsetType = UNSET)"
    ),
    "ExecResult": (
        "ExecResult(exit_code: int, stdout: str, stderr: str, duration_ms: int, "
        "stdout_truncated: bool, stderr_truncated: bool)"
    ),
    "Me": "Me(id: str, email: str, workspace: AssignedWorkspace | UnassignedWorkspace)",
    "OpenSessionResult": "OpenSessionResult(url: str)",
    "Record": (
        "Record(id: str, session_id: str, kind: str, summary: str, detail: object, "
        "created_at: str)"
    ),
    "SessionAgent": "",
    "SessionCreateOptions": (
        "SessionCreateOptions(agent: SessionAgent | UnsetType = UNSET, "
        "vcpus: int | UnsetType = UNSET, memory_mib: int | UnsetType = UNSET, "
        "allowed_hosts: list[str] | UnsetType = UNSET, "
        "runtime_port: int | UnsetType = UNSET)"
    ),
    "SessionSnapshot": (
        "SessionSnapshot(id: str, user_id: str, slug: str, name: str, "
        "agent: SessionAgent | None, vcpus: int, memory_mib: int, "
        "status: SessionStatus, running_seconds: int, created_at: str, "
        "updated_at: str, url: str)"
    ),
    "SessionStatus": "",
    "UNSET": "None",
    "UnassignedWorkspace": (
        "UnassignedWorkspace(assigned: Literal[False], waitlist_position: int)"
    ),
    "UnsetType": "",
    "ApiError": (
        "ApiError(status: int, *, code: Literal['api_error', 'malformed_response'] = "
        "'api_error')"
    ),
    "CommandError": "CommandError()",
    "ConfigError": "ConfigError()",
    "RunaError": "RunaError(code: ErrorCode)",
}


def _all(tree: ast.Module) -> tuple[str, ...]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
    return ()


def _target(obj: Any) -> Any:
    try:
        return obj.final_target
    except (AttributeError, ValueError):
        return obj


def _detail(obj: Any) -> str:
    signature = getattr(obj, "signature", None)
    if callable(signature):
        return str(signature())
    annotation = getattr(obj, "annotation", None)
    return str(annotation) if annotation is not None else "value"


def _raises(owner: str, member: str) -> tuple[str, ...]:
    exact = RAISES.get(f"{owner}.{member}")
    if exact is not None:
        return exact
    if member in {"id", "snapshot", "sessions", "records", "close", "code", "message", "status"}:
        return ()
    if owner.startswith("Async"):
        return ("ApiError", "CancelledError")
    return ("ApiError",)


def _example_name(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower().replace("u_n_s_e_t", "unset")


def _examples(path: Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"print", "breakpoint", "eval", "exec", "open"}
    result: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id in forbidden
            ):
                raise ValueError("unsafe-example-call")
            if isinstance(child, ast.Attribute) and child.attr == "url":
                raise ValueError("capability-url-used")
        segment = ast.get_source_segment(source, node)
        if segment is None:
            raise ValueError("example-source-missing")
        compile(segment + "\n", path.as_posix(), "exec")
        result[node.name] = segment
    return result


def _public_members(obj: Any) -> tuple[str, ...]:
    return tuple(name for name in obj.members if not name.startswith("_"))


def _render_page(
    name: str, section: str, obj: Any, example: str
) -> tuple[str, list[dict[str, object]]]:
    target = _target(obj)
    import_path = (
        f"from runa.errors import {name}" if section == "errors" else f"from runa import {name}"
    )
    lines = [
        f"# `{name}`",
        "",
        SUMMARIES[name],
        "",
        "## Import",
        "",
        f"`{import_path}`",
        "",
        "## Acquisition",
        "",
    ]
    if name in {"SessionsManager", "RecordsManager"}:
        lines.append(
            f"Obtain this stable instance from `Runa.{name.removesuffix('Manager').lower()}`."
        )
    elif name in {"AsyncSessionsManager", "AsyncRecordsManager"}:
        base = name.removeprefix("Async").removesuffix("Manager").lower()
        lines.append(f"Obtain this stable instance from `AsyncRuna.{base}`.")
    elif name in {"Session", "AsyncSession"}:
        lines.append(
            "Obtain handles from the matching sessions manager; direct construction is unsupported."
        )
    elif section == "errors":
        lines.append(
            "Catch this type from `runa.errors`; root-module re-export is intentionally forbidden."
        )
    else:
        lines.append("Import the canonical value from the root module as shown above.")
    lines.extend(["", "## Signature", "", f"`{_detail(target)}`", ""])
    claims: list[dict[str, object]] = []
    expected = EXPECTED_MEMBERS.get(name)
    members = _public_members(target)
    if expected is not None:
        if set(members) != set(expected):
            raise ValueError(f"{name}-member-manifest-mismatch")
        members = expected
    if members:
        lines.extend(
            [
                "## Public members",
                "",
                "| Member | Signature or annotation | Meaning | Returns | Raises |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for member_name in members:
            member = _target(target.members[member_name])
            detail = _detail(member)
            meaning = MEMBER_MEANINGS.get(member_name, FIELD_MEANINGS.get(member_name))
            if meaning is None:
                meaning = f"Accepted `{member_name}` value defined by the public contract."
            returns = detail.rsplit(" -> ", 1)[-1] if " -> " in detail else detail
            raises = ", ".join(f"`{item}`" for item in _raises(name, member_name)) or "None"
            lines.append(
                f"| [`{member_name}`](#{member_name}) | `{detail}` | {meaning} | "
                f"`{returns}` | {raises} |"
            )
            lines.extend(
                [
                    "",
                    f'<a id="{member_name}"></a>',
                    f"### `{member_name}`",
                    "",
                    meaning,
                    "",
                    f"- Exact shape: `{detail}`",
                    f"- Returns: `{returns}`",
                    f"- Raises: {raises}",
                    "",
                ]
            )
            test_ids = ["TC-091-04", "TC-091-05"]
            if _raises(name, member_name):
                test_ids.append("TC-091-06")
            claims.append(
                {
                    "claimId": f"REF-{name.upper()}-{member_name.upper()}",
                    "member": member_name,
                    "testIds": test_ids,
                }
            )
    elif hasattr(target, "members"):
        fields = _public_members(target)
        if fields:
            lines.extend(
                [
                    "## Fields and values",
                    "",
                    "| Name | Annotation | Optionality and meaning |",
                    "| --- | --- | --- |",
                ]
            )
            for field in fields:
                member = _target(target.members[field])
                meaning = FIELD_MEANINGS.get(
                    field, f"Accepted `{field}` value defined by the public contract."
                )
                lines.append(f"| `{field}` | `{_detail(member)}` | {meaning} |")
                claims.append(
                    {
                        "claimId": f"REF-{name.upper()}-{field.upper()}",
                        "member": field,
                        "testIds": ["TC-091-04", "TC-091-05"],
                    }
                )
            lines.append("")
    if name in PAIRS:
        pair = PAIRS[name]
        pair_section = "async" if pair.startswith("Async") else "sync"
        lines.extend(
            [
                "## Sync/async pair",
                "",
                f"See the behaviorally equivalent [`{pair}`](../{pair_section}/{pair}.md).",
                "",
            ]
        )
    example_id = f"REF-EX-{name.upper()}"
    lines.extend(
        [
            "## Safe executable example",
            "",
            f"Source: [`examples/reference.py`](../../../examples/reference.py) · `{example_id}` · "
            f"`TC-091-09`",
            "",
            "```python",
            example,
            "```",
            "",
        ]
    )
    claims.append({"claimId": example_id, "member": "<example>", "testIds": ["TC-091-09"]})
    return "\n".join(lines), claims


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _validate_links(root: Path) -> None:
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)#]+\.md)(?:#[^)]+)?\)", text):
            if not (path.parent / link).resolve().is_file():
                raise ValueError(f"broken-link:{path.name}:{link}")


def generate(wheel: Path, output: Path, examples_path: Path) -> dict[str, object]:
    if version("griffe") != "2.1.0" or EXTENSIONS:
        raise ValueError("documentation-tool-configuration-mismatch")
    examples = _examples(examples_path)
    with tempfile.TemporaryDirectory() as room_name:
        room = Path(room_name)
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(room)
        root_names = _all(ast.parse((room / "runa" / "__init__.py").read_text(encoding="utf-8")))
        error_names = _all(ast.parse((room / "runa" / "errors.py").read_text(encoding="utf-8")))
        if root_names != ROOT_MANIFEST:
            raise ValueError("candidate-root-manifest-mismatch")
        if error_names != ERROR_MANIFEST or set(error_names) & set(root_names):
            raise ValueError("accepted-errors-manifest-mismatch")
        module = griffe.load("runa", search_paths=[room], extensions=EXTENSIONS)
        errors_module = griffe.load("runa.errors", search_paths=[room], extensions=EXTENSIONS)
    for key, expected in EXPECTED_SIGNATURES.items():
        owner, _, member = key.partition(".")
        source = errors_module.members[owner] if owner in ERROR_MANIFEST else module.members[owner]
        obj = _target(source)
        if member:
            obj = _target(obj.members[member])
        if _detail(obj) != expected:
            raise ValueError(f"signature-mismatch:{key}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    index = ["# Python API reference", "", "Generated only from an extracted candidate wheel.", ""]
    registry: list[dict[str, object]] = []
    page_count = 0
    for section, names in SECTIONS.items():
        directory = output / section
        directory.mkdir()
        section_index = [f"# {section.title()}", ""]
        index.append(f"- [{section.title()}]({section}/README.md)")
        for name in names:
            source = errors_module.members[name] if section == "errors" else module.members[name]
            example_name = _example_name(name)
            if example_name not in examples:
                raise ValueError(f"example-missing:{name}")
            page, claims = _render_page(name, section, source, examples[example_name])
            (directory / f"{name}.md").write_text(page, encoding="utf-8", newline="\n")
            section_index.append(f"- [`{name}`]({name}.md)")
            registry.append(
                {
                    "claims": claims,
                    "import": (
                        f"from runa.errors import {name}"
                        if section == "errors"
                        else f"from runa import {name}"
                    ),
                    "page": f"{section}/{name}.md",
                    "symbol": name,
                }
            )
            page_count += 1
        (directory / "README.md").write_text(
            "\n".join(section_index) + "\n", encoding="utf-8", newline="\n"
        )
    (output / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8", newline="\n")
    (output / "claims.json").write_text(
        json.dumps(
            {"generator": "griffe==2.1.0", "pages": registry, "schemaVersion": 1},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    observed_test_ids = {
        test_id
        for page in registry
        for claim in page["claims"]
        for test_id in claim["testIds"]
    }
    if not observed_test_ids <= VALID_TEST_IDS:
        raise ValueError("unknown-prd-test-id")
    _validate_links(output)
    return {
        "byteDeterministic": True,
        "claimRegistry": "docs/api/claims.json",
        "digest": _tree_digest(output),
        "examples": len(examples),
        "extensions": EXTENSIONS,
        "pages": page_count,
        "privatePages": 0,
        "requirement": "R-091-20",
        "tool": "griffe==2.1.0",
        "verdict": "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/api"))
    parser.add_argument("--examples", type=Path, default=Path("examples/reference.py"))
    args = parser.parse_args()
    try:
        first = generate(args.wheel, args.output, args.examples)
        with tempfile.TemporaryDirectory() as second_name:
            second = generate(args.wheel, Path(second_name) / "api", args.examples)
        if first["digest"] != second["digest"]:
            raise ValueError("byte-determinism-failure")
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"category": str(exc), "requirement": "R-091-20", "verdict": "blocked"}))
        return 1
    print(json.dumps(first, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
