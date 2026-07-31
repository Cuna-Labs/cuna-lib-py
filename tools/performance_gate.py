"""Run the fixed PRD-017 Python artifact budgets with synthetic transport."""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Any

from _evidence_utils import file_sha256

from runa import AsyncRuna, Runa
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


class SyncReuseTransport:
    """Controlled one-connection transport used only by the budget oracle."""

    def __init__(self) -> None:
        self.establishments = 0
        self.requests = 0
        self.open = False

    def __call__(self, _request: PreparedRequest, _context: RequestContext) -> RawResponse:
        if not self.open:
            self.establishments += 1
            self.open = True
        self.requests += 1
        return response()

    def close(self) -> None:
        self.open = False


class AsyncReuseTransport:
    """Async counterpart of the controlled connection-reuse oracle."""

    def __init__(self) -> None:
        self.establishments = 0
        self.requests = 0
        self.open = False

    async def __call__(self, _request: PreparedRequest, _context: RequestContext) -> RawResponse:
        if not self.open:
            self.establishments += 1
            self.open = True
        self.requests += 1
        return response()

    async def close(self) -> None:
        self.open = False


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


def sync_metrics() -> tuple[float, int, float, float, int, int, int, dict[str, int]]:
    calls = 0

    def transport(_request: PreparedRequest, _context: RequestContext) -> RawResponse:
        nonlocal calls
        calls += 1
        return response()

    constructions: list[float] = []
    for _ in range(20):
        started = time.perf_counter_ns()
        constructed = Runa(api_key="runa_sk_performance", transport=transport)
        constructions.append((time.perf_counter_ns() - started) / 1_000_000)
        constructed.close()
    client = Runa(api_key="runa_sk_performance", transport=transport)
    durations: list[float] = []
    allocations: list[int] = []
    for _ in range(20):
        tracemalloc.start()
        before = tracemalloc.get_traced_memory()[0]
        started = time.perf_counter_ns()
        client.me()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
        allocations.append(max(0, tracemalloc.get_traced_memory()[0] - before))
        tracemalloc.stop()
    client.close()
    reuse = SyncReuseTransport()
    reuse_client = Runa(api_key="runa_sk_performance", transport=reuse)
    for _ in range(10):
        reuse_client.me()
    reuse_client.close()
    reuse.close()
    resources = _resource_counters(reuse_client, reuse)
    retained: list[float] = []
    for _ in range(5):
        tracemalloc.start()
        gc.collect()
        before = tracemalloc.get_traced_memory()[0]
        for _ in range(100):
            cycle = Runa(api_key="runa_sk_performance", transport=transport)
            cycle.me()
            cycle.close()
        del cycle
        gc.collect()
        retained.append(float(max(0, tracemalloc.get_traced_memory()[0] - before)))
        tracemalloc.stop()
    return (
        p95(durations),
        max(allocations),
        p95(constructions),
        p95(retained),
        calls,
        reuse.establishments,
        reuse.requests,
        resources,
    )


async def async_metrics() -> tuple[float, int, float, float, int, int, int, dict[str, int]]:
    calls = 0

    async def transport(_request: PreparedRequest, _context: RequestContext) -> RawResponse:
        nonlocal calls
        calls += 1
        return response()

    constructions: list[float] = []
    for _ in range(20):
        started = time.perf_counter_ns()
        constructed = AsyncRuna._with_transport(api_key="runa_sk_performance", transport=transport)
        constructions.append((time.perf_counter_ns() - started) / 1_000_000)
        await constructed.close()
    client = AsyncRuna._with_transport(api_key="runa_sk_performance", transport=transport)
    durations: list[float] = []
    allocations: list[int] = []
    for _ in range(20):
        tracemalloc.start()
        before = tracemalloc.get_traced_memory()[0]
        started = time.perf_counter_ns()
        await client.me()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
        allocations.append(max(0, tracemalloc.get_traced_memory()[0] - before))
        tracemalloc.stop()
    await client.close()
    reuse = AsyncReuseTransport()
    reuse_client = AsyncRuna._with_transport(api_key="runa_sk_performance", transport=reuse)
    for _ in range(10):
        await reuse_client.me()
    await reuse_client.close()
    await reuse.close()
    resources = _resource_counters(reuse_client, reuse)
    retained: list[float] = []
    for _ in range(5):
        tracemalloc.start()
        gc.collect()
        before = tracemalloc.get_traced_memory()[0]
        for _ in range(100):
            cycle = AsyncRuna._with_transport(api_key="runa_sk_performance", transport=transport)
            await cycle.me()
            await cycle.close()
        del cycle
        gc.collect()
        await asyncio.sleep(0)
        retained.append(float(max(0, tracemalloc.get_traced_memory()[0] - before)))
        tracemalloc.stop()
    return (
        p95(durations),
        max(allocations),
        p95(constructions),
        p95(retained),
        calls,
        reuse.establishments,
        reuse.requests,
        resources,
    )


def evaluate_budget(report: dict[str, Any], payload_cap: int) -> bool:
    """Evaluate every measured budget; used by both the gate and mutation tests."""

    resources = report.get("resourceCounters")
    return bool(
        report.get("artifactBytes", payload_cap + 1) <= payload_cap
        and report.get("requestMillisecondsP95", 21) <= 20
        and report.get("importMillisecondsP95", 501) <= 500
        and report.get("constructionMillisecondsP95", 101) <= 100
        and report.get("allocationBytesMax", 1_048_577) <= 1_048_576
        and report.get("retainedBytesP95", 8_388_609) <= 8_388_608
        and report.get("lifecycleRequestCount") == 500
        and report.get("connectionEstablishments", 2) <= 1
        and report.get("reuseRequestCount") == 10
        and isinstance(resources, dict)
        and all(type(value) is int and value == 0 for value in resources.values())
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--mode", choices=("sync", "async"), required=True)
    parser.add_argument("--local-diagnostic", action="store_true")
    parser.add_argument("--source")
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
        calls,
        establishments,
        reuse_requests,
        resources,
    ) = sync_metrics() if args.mode == "sync" else asyncio.run(async_metrics())
    import_ms = import_p95()
    profile = f"P-017-PY-{form.upper()}-{args.mode.upper()}-V1"
    report = {
        "allocationBytesMax": allocation_bytes,
        "artifactForm": form,
        "artifactBytes": args.artifact.stat().st_size,
        "artifactSha256": file_sha256(args.artifact),
        "constructionMillisecondsP95": round(construction_ms, 6),
        "importMillisecondsP95": round(import_ms, 6),
        "connectionEstablishments": establishments,
        "lifecycleRequestCount": calls - 20,
        "mode": args.mode,
        "profile": profile,
        "requestMillisecondsP95": round(request_ms, 6),
        "retainedBytesP95": round(retained_bytes),
        "resourceCounters": resources,
        "reuseRequestCount": reuse_requests,
        "source": args.source if args.source is not None else "local-diagnostic",
    }
    passed = evaluate_budget(report, payload_cap)
    report["verdict"] = (
        "diagnostic-pass" if passed and args.local_diagnostic else "pass" if passed else "fail"
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
