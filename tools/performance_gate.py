"""Run the fixed PRD-017 Python artifact budgets with synthetic transport."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import subprocess
import sys
import tarfile
import threading
import time
import tracemalloc
import zipfile
from collections import deque
from email import message_from_bytes
from email.message import Message
from importlib import metadata
from pathlib import Path
from platform import system
from typing import Any, ClassVar

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    from _evidence_utils import canonical_json_sha256, file_sha256
except ModuleNotFoundError:  # imported as tools.performance_gate by mutation tests
    from tools._evidence_utils import canonical_json_sha256, file_sha256

from runa import AsyncRuna, Runa
from runa import client as client_module
from runa._internal.resilience import _open_sync_dispatch_threads
from runa._internal.transport import PreparedRequest, RawResponse, RequestContext

ME_BODY = (
    b'{"id":"00000000-0000-0000-0000-000000000000","email":"person@example.com",'
    b'"workspace":{"assigned":false,"waitlist_position":0}}'
)


def response() -> RawResponse:
    return RawResponse(200, {"content-type": "application/json"}, ME_BODY)


def p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=100, method="inclusive")[94]


class SyncDefaultTransport:
    """Controlled replacement for the SDK-owned default sync adapter."""

    instances: ClassVar[list[SyncDefaultTransport]] = []

    def __init__(self, origin: str) -> None:
        self.origin = origin
        self.establishments = 0
        self.requests = 0
        self.open = False
        self.closed = False
        self.last_allocation_bytes = 0
        self.last_entry_ns = 0
        self.origin_matches = True
        self.instances.append(self)

    def __call__(self, request: PreparedRequest, _context: RequestContext) -> RawResponse:
        self.last_entry_ns = time.perf_counter_ns()
        self.last_allocation_bytes = (
            tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        )
        if not self.open:
            self.establishments += 1
            self.open = True
        self.origin_matches = self.origin_matches and request.origin == self.origin
        self.requests += 1
        return response()

    def close(self) -> None:
        self.open = False
        self.closed = True


class AsyncDefaultTransport:
    """Controlled replacement for the SDK-owned default async adapter."""

    instances: ClassVar[list[AsyncDefaultTransport]] = []

    def __init__(self, origin: str) -> None:
        self.origin = origin
        self.establishments = 0
        self.requests = 0
        self.open = False
        self.closed = False
        self.last_allocation_bytes = 0
        self.last_entry_ns = 0
        self.origin_matches = True
        self.instances.append(self)

    async def __call__(self, request: PreparedRequest, _context: RequestContext) -> RawResponse:
        self.last_entry_ns = time.perf_counter_ns()
        self.last_allocation_bytes = (
            tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        )
        if not self.open:
            self.establishments += 1
            self.open = True
        self.origin_matches = self.origin_matches and request.origin == self.origin
        self.requests += 1
        return response()

    async def close(self) -> None:
        self.open = False
        self.closed = True


def _resource_counters(client: Any, transport: Any) -> dict[str, int]:
    """Derive retained resource counts from the closed SDK and controlled transport."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    scheduled = (
        sum(not handle.cancelled() for handle in getattr(loop, "_scheduled", ()))
        if loop is not None
        else 0
    )
    async_tasks = (
        sum(
            task is not asyncio.current_task() and not task.done()
            for task in asyncio.all_tasks(loop)
        )
        if loop is not None
        else 0
    )
    return {
        "callbackRegistrations": int(client._diagnostic_sink is not None)
        + int(client._trace_sink is not None)
        + scheduled,
        "asyncTasks": async_tasks,
        "lifecycleRegistrations": int(client._admitted)
        + int(getattr(client, "_close_active", False)),
        "openConnections": int(transport.open),
        "openThreads": _open_sync_dispatch_threads(),
        "poolEntries": int(transport.open and transport.establishments > 0),
        "timers": sum(
            isinstance(thread, threading.Timer) and thread.is_alive()
            for thread in threading.enumerate()
        ),
    }


def import_p95() -> float:
    observed: list[float] = []
    probe = (
        "import time;"
        "started=time.perf_counter_ns();"
        "import runa;"
        "print((time.perf_counter_ns()-started)/1000000)"
    )
    for _ in range(20):
        result = subprocess.run(  # noqa: S603 - fixed interpreter and static import probe
            [sys.executable, "-I", "-c", probe],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        observed.append(float(result.stdout))
    return p95(observed)


def _artifact_metadata(artifact: Path) -> Message:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as archive:
            names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ValueError("artifact-metadata-missing")
            return message_from_bytes(archive.read(names[0]))
    with tarfile.open(artifact, "r:gz") as archive:
        members = [item for item in archive.getmembers() if item.name.endswith("/PKG-INFO")]
        if len(members) != 1:
            raise ValueError("artifact-metadata-missing")
        stream = archive.extractfile(members[0])
        if stream is None:
            raise ValueError("artifact-metadata-missing")
        return message_from_bytes(stream.read())


def _active_requirements(values: list[str] | None) -> list[Requirement]:
    result: list[Requirement] = []
    for value in values or []:
        requirement = Requirement(value)
        if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
            result.append(requirement)
    return result


def dependency_evidence(
    artifact: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    """Resolve the runtime closure from the exact candidate's declared metadata."""

    artifact_metadata = _artifact_metadata(artifact)
    artifact_name = canonicalize_name(str(artifact_metadata["Name"]))
    direct_requirements = _active_requirements(artifact_metadata.get_all("Requires-Dist"))
    paths = {artifact_name: "artifact"}
    queue: deque[tuple[str, str]] = deque()
    for requirement in direct_requirements:
        name = canonicalize_name(requirement.name)
        paths[name] = f"{artifact_name} -> {name}"
        queue.append((name, paths[name]))
    while queue:
        name, parent_path = queue.popleft()
        distribution = metadata.distribution(name)
        for requirement in _active_requirements(distribution.requires):
            child = canonicalize_name(requirement.name)
            if child in paths:
                continue
            paths[child] = f"{parent_path} -> {child}"
            queue.append((child, paths[child]))
    direct_names = {canonicalize_name(item.name) for item in direct_requirements}
    closure = [
        {
            "name": name,
            "path": paths[name],
            "role": (
                "artifact"
                if name == artifact_name
                else "direct"
                if name in direct_names
                else "transitive"
            ),
            "version": (
                str(artifact_metadata["Version"])
                if name == artifact_name
                else metadata.version(name)
            ),
        }
        for name in sorted(paths)
    ]
    accepted_reasons = {
        "httpx": "HTTP transport, TLS policy, streaming, and timeout primitives",
    }
    ledger = [
        {"name": name, "reason": accepted_reasons.get(name, "UNAPPROVED_DIRECT_DEPENDENCY")}
        for name in sorted(direct_names)
    ]
    return closure, ledger, canonical_json_sha256(closure)


def sync_metrics() -> tuple[float, int, float, float, int, int, int, dict[str, int], bool, bool]:
    original = client_module.SyncHttpTransport
    SyncDefaultTransport.instances.clear()
    client_module.SyncHttpTransport = SyncDefaultTransport  # type: ignore[assignment]
    try:
        constructions: list[float] = []
        for _ in range(20):
            started = time.perf_counter_ns()
            constructed = Runa(api_key="runa_sk_performance")
            constructions.append((time.perf_counter_ns() - started) / 1_000_000)
            constructed.close()
        client = Runa(api_key="runa_sk_performance")
        measured_transport = SyncDefaultTransport.instances[-1]
        durations: list[float] = []
        allocations: list[int] = []
        for _ in range(20):
            tracemalloc.start()
            before = tracemalloc.get_traced_memory()[0]
            started = time.perf_counter_ns()
            client.me()
            durations.append((measured_transport.last_entry_ns - started) / 1_000_000)
            allocations.append(max(0, measured_transport.last_allocation_bytes - before))
            tracemalloc.stop()
        client.close()
        reuse_client = Runa(api_key="runa_sk_performance")
        reuse = SyncDefaultTransport.instances[-1]
        for _ in range(10):
            reuse_client.me()
        reuse_client.close()
        resources = _resource_counters(reuse_client, reuse)
        retained: list[float] = []
        lifecycle_start = sum(item.requests for item in SyncDefaultTransport.instances)
        for _ in range(5):
            tracemalloc.start()
            before = tracemalloc.get_traced_memory()[0]
            for _ in range(100):
                cycle = Runa(api_key="runa_sk_performance")
                cycle.me()
                cycle.close()
            del cycle
            time.sleep(0)
            retained.append(float(max(0, tracemalloc.get_traced_memory()[0] - before)))
            tracemalloc.stop()
        lifecycle_calls = (
            sum(item.requests for item in SyncDefaultTransport.instances) - lifecycle_start
        )
        isolation = Runa(
            api_key="runa_sk_performance",
            base_url="https://api.runacode.io",
        )
        isolation.me()
        isolation.close()
        return (
            p95(durations),
            max(allocations),
            p95(constructions),
            p95(retained),
            lifecycle_calls,
            reuse.establishments,
            reuse.requests,
            resources,
            all(item.closed for item in SyncDefaultTransport.instances),
            all(item.origin_matches for item in SyncDefaultTransport.instances),
        )
    finally:
        client_module.SyncHttpTransport = original


async def async_metrics() -> tuple[
    float, int, float, float, int, int, int, dict[str, int], bool, bool
]:
    original = client_module.AsyncHttpTransport
    AsyncDefaultTransport.instances.clear()
    client_module.AsyncHttpTransport = AsyncDefaultTransport  # type: ignore[assignment]
    try:
        constructions: list[float] = []
        for _ in range(20):
            started = time.perf_counter_ns()
            constructed = AsyncRuna(api_key="runa_sk_performance")
            constructions.append((time.perf_counter_ns() - started) / 1_000_000)
            await constructed.close()
        client = AsyncRuna(api_key="runa_sk_performance")
        measured_transport = AsyncDefaultTransport.instances[-1]
        durations: list[float] = []
        allocations: list[int] = []
        for _ in range(20):
            tracemalloc.start()
            before = tracemalloc.get_traced_memory()[0]
            started = time.perf_counter_ns()
            await client.me()
            durations.append((measured_transport.last_entry_ns - started) / 1_000_000)
            allocations.append(max(0, measured_transport.last_allocation_bytes - before))
            tracemalloc.stop()
        await client.close()
        reuse_client = AsyncRuna(api_key="runa_sk_performance")
        reuse = AsyncDefaultTransport.instances[-1]
        for _ in range(10):
            await reuse_client.me()
        await reuse_client.close()
        resources = _resource_counters(reuse_client, reuse)
        retained: list[float] = []
        lifecycle_start = sum(item.requests for item in AsyncDefaultTransport.instances)
        for _ in range(5):
            tracemalloc.start()
            before = tracemalloc.get_traced_memory()[0]
            for _ in range(100):
                cycle = AsyncRuna(api_key="runa_sk_performance")
                await cycle.me()
                await cycle.close()
            del cycle
            await asyncio.sleep(0)
            retained.append(float(max(0, tracemalloc.get_traced_memory()[0] - before)))
            tracemalloc.stop()
        lifecycle_calls = (
            sum(item.requests for item in AsyncDefaultTransport.instances) - lifecycle_start
        )
        isolation = AsyncRuna(
            api_key="runa_sk_performance",
            base_url="https://api.runacode.io",
        )
        await isolation.me()
        await isolation.close()
        return (
            p95(durations),
            max(allocations),
            p95(constructions),
            p95(retained),
            lifecycle_calls,
            reuse.establishments,
            reuse.requests,
            resources,
            all(item.closed for item in AsyncDefaultTransport.instances),
            all(item.origin_matches for item in AsyncDefaultTransport.instances),
        )
    finally:
        client_module.AsyncHttpTransport = original


def evaluate_caps(report: dict[str, Any], payload_cap: int) -> bool:
    """Evaluate candidate caps independently of baseline authority."""

    resources = report.get("resourceCounters")
    required_profile_fields = {
        "benchmarkCommand",
        "caps",
        "dependencyClosure",
        "dependencyClosureDigest",
        "directDependencyReasons",
        "fixtureIds",
        "matrixTuple",
        "profile",
        "profileVersion",
        "statistics",
        "toolVersions",
    }
    closure = report.get("dependencyClosure")
    ledger = report.get("directDependencyReasons")
    dependency_policy_passed = (
        isinstance(closure, list)
        and isinstance(ledger, list)
        and {
            item.get("name")
            for item in closure
            if isinstance(item, dict) and item.get("role") == "direct"
        }
        == {item.get("name") for item in ledger if isinstance(item, dict)}
        and all(
            isinstance(item, dict) and item.get("reason") != "UNAPPROVED_DIRECT_DEPENDENCY"
            for item in ledger
        )
    )
    return bool(
        required_profile_fields.issubset(report)
        and dependency_policy_passed
        and report.get("artifactBytes", payload_cap + 1) <= payload_cap
        and report.get("requestMillisecondsP95", 21) <= 20
        and report.get("importMillisecondsP95", 501) <= 500
        and report.get("constructionMillisecondsP95", 101) <= 100
        and report.get("allocationBytesMax", 1_048_577) <= 1_048_576
        and report.get("retainedBytesP95", 8_388_609) <= 8_388_608
        and report.get("lifecycleRequestCount") == 500
        and report.get("defaultTransportOwnershipClosed") is True
        and report.get("originIsolationVerified") is True
        and report.get("connectionEstablishments", 2) <= 1
        and report.get("reuseRequestCount") == 10
        and isinstance(resources, dict)
        and all(type(value) is int and value == 0 for value in resources.values())
    )


def evaluate_budget(report: dict[str, Any], payload_cap: int) -> bool:
    """Require passing caps and an authority-accepted non-regressing baseline."""

    baseline = report.get("baseline")
    if (
        not evaluate_caps(report, payload_cap)
        or not isinstance(baseline, dict)
        or baseline.get("status") != "accepted"
        or not isinstance(baseline.get("approvalReference"), str)
        or not baseline["approvalReference"]
        or baseline.get("profile") != report.get("profile")
        or baseline.get("dependencyClosureDigest") != report.get("dependencyClosureDigest")
        or baseline.get("matrixTuple") != report.get("matrixTuple")
        or re.fullmatch(r"[0-9a-f]{64}", str(baseline.get("referenceArtifactSha256", ""))) is None
        or baseline.get("authority")
        != {
            "certificateIdentity": (
                "https://github.com/Runa-Laboratories/runa-lib-py/.github/workflows/"
                "performance-baseline.yml@refs/heads/main"
            ),
            "issuer": "https://token.actions.githubusercontent.com",
        }
        or not isinstance(baseline.get("metrics"), dict)
    ):
        return False
    metrics = baseline["metrics"]
    regression_fields = (
        "allocationBytesMax",
        "artifactBytes",
        "connectionEstablishments",
        "constructionMillisecondsP95",
        "importMillisecondsP95",
        "requestMillisecondsP95",
        "retainedBytesP95",
    )
    return all(
        isinstance(metrics.get(field), int | float) and report[field] <= metrics[field]
        for field in regression_fields
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--mode", choices=("sync", "async"), required=True)
    parser.add_argument("--local-diagnostic", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    form = "sdist" if args.artifact.name.endswith(".tar.gz") else "wheel"
    if not args.local_diagnostic and args.source is None:
        raise SystemExit("R-094-18: immutable source identity is required")
    payload_cap = 1_572_864 if form == "sdist" else 1_048_576
    (
        request_ms,
        allocation_bytes,
        construction_ms,
        retained_bytes,
        lifecycle_calls,
        establishments,
        reuse_requests,
        resources,
        ownership_closed,
        origin_isolated,
    ) = sync_metrics() if args.mode == "sync" else asyncio.run(async_metrics())
    import_ms = import_p95()
    catalog_profile = f"P-017-PY-{form.upper()}-{args.mode.upper()}-V1"
    matrix = {
        "artifactForm": form,
        "executionMode": args.mode,
        "operatingSystem": system().lower(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    profile = f"{catalog_profile}-py{matrix['python']}-{matrix['operatingSystem']}"
    closure, reason_ledger, closure_digest = dependency_evidence(args.artifact)
    caps = {
        "allocationBytesMax": 1_048_576,
        "artifactBytes": payload_cap,
        "connectionEstablishments": 1,
        "constructionMillisecondsP95": 100,
        "importMillisecondsP95": 500,
        "lifecycleCyclesPerBatch": 100,
        "requestMillisecondsP95": 20,
        "retainedBytesP95": 8_388_608,
        "reuseRequestCount": 10,
        "resourceCounterMaximum": 0,
    }
    report = {
        "allocationBytesMax": allocation_bytes,
        "artifactForm": form,
        "artifactBytes": args.artifact.stat().st_size,
        "artifactSha256": file_sha256(args.artifact),
        "benchmarkCommand": (
            "python tools/performance_gate.py <exact-artifact> "
            f"--mode {args.mode} --source <immutable-sha>"
        ),
        "caps": caps,
        "dependencyClosure": closure,
        "dependencyClosureDigest": closure_digest,
        "directDependencyReasons": reason_ledger,
        "constructionMillisecondsP95": round(construction_ms, 6),
        "fixtureIds": [
            "startup-no-dispatch-v1",
            "request-entry-to-transport-seam-v1",
            "default-reuse-origin-isolation-v1",
            "lifecycle-request-cleanup-100-v1",
        ],
        "importMillisecondsP95": round(import_ms, 6),
        "connectionEstablishments": establishments,
        "defaultTransportOwnershipClosed": ownership_closed,
        "lifecycleRequestCount": lifecycle_calls,
        "mode": args.mode,
        "matrixTuple": matrix,
        "originIsolationVerified": origin_isolated,
        "profile": profile,
        "profileVersion": "V1",
        "requestMillisecondsP95": round(request_ms, 6),
        "retainedBytesP95": round(retained_bytes),
        "resourceCounters": resources,
        "reuseRequestCount": reuse_requests,
        "source": args.source if args.source is not None else "local-diagnostic",
        "statistics": {
            "allocation": "maximum-of-20",
            "construction": "p95-of-20",
            "import": "p95-of-20-isolated-processes",
            "request": "entry-to-transport-seam-p95-of-20",
            "retained": "p95-of-5-drained-100-cycle-batches",
        },
        "toolVersions": {
            "harness": "python-1",
            "python": sys.version.split()[0],
            "tracemalloc": "stdlib",
        },
    }
    baseline_proposal = {
        "artifactSha256": report["artifactSha256"],
        "dependencyClosureDigest": closure_digest,
        "metrics": {
            key: report[key]
            for key in (
                "allocationBytesMax",
                "artifactBytes",
                "connectionEstablishments",
                "constructionMillisecondsP95",
                "importMillisecondsP95",
                "requestMillisecondsP95",
                "retainedBytesP95",
                "reuseRequestCount",
            )
        },
        "profile": profile,
        "reference": "bootstrap-v1",
        "status": "proposal",
    }
    report["baselineProposal"] = baseline_proposal
    report["baselineProposalDigest"] = canonical_json_sha256(baseline_proposal)
    if args.baseline is not None:
        report["baseline"] = json.loads(args.baseline.read_text(encoding="utf-8"))
        report["baselineDigest"] = file_sha256(args.baseline)
    caps_passed = evaluate_caps(report, payload_cap)
    passed = evaluate_budget(report, payload_cap)
    if args.local_diagnostic:
        report["verdict"] = "diagnostic-pass" if caps_passed else "diagnostic-fail"
    elif args.baseline is None and caps_passed:
        report["verdict"] = "blocked-bootstrap-approval"
    else:
        report["verdict"] = "pass" if passed else "fail"
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if (caps_passed if args.local_diagnostic else passed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
