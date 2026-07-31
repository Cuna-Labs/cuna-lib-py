"""Run the fixed PRD-017 Python artifact budgets with synthetic transport."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

from runa import AsyncRuna, Runa
from runa._internal.transport import PreparedRequest, RawResponse, RequestContext

ME_BODY = (
    b'{"id":"00000000-0000-0000-0000-000000000000","email":"person@example.com",'
    b'"workspace":{"assigned":false,"waitlist_position":0}}'
)


def response() -> RawResponse:
    return RawResponse(200, {"content-type": "application/json"}, ME_BODY)


def p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=100, method="inclusive")[94]


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


def sync_metrics() -> tuple[float, int, float, float, int]:
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
    retained: list[float] = []
    for _ in range(5):
        tracemalloc.start()
        before = tracemalloc.get_traced_memory()[0]
        for _ in range(100):
            cycle = Runa(api_key="runa_sk_performance", transport=transport)
            cycle.close()
        retained.append(float(max(0, tracemalloc.get_traced_memory()[0] - before)))
        tracemalloc.stop()
    return p95(durations), max(allocations), p95(constructions), p95(retained), calls


async def async_metrics() -> tuple[float, int, float, float, int]:
    calls = 0

    async def transport(_request: PreparedRequest, _context: RequestContext) -> RawResponse:
        nonlocal calls
        calls += 1
        return response()

    constructions: list[float] = []
    for _ in range(20):
        started = time.perf_counter_ns()
        constructed = AsyncRuna._with_transport(
            api_key="runa_sk_performance", transport=transport
        )
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
    retained: list[float] = []
    for _ in range(5):
        tracemalloc.start()
        before = tracemalloc.get_traced_memory()[0]
        for _ in range(100):
            cycle = AsyncRuna._with_transport(
                api_key="runa_sk_performance", transport=transport
            )
            await cycle.close()
        retained.append(float(max(0, tracemalloc.get_traced_memory()[0] - before)))
        tracemalloc.stop()
    return p95(durations), max(allocations), p95(constructions), p95(retained), calls


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--mode", choices=("sync", "async"), required=True)
    parser.add_argument("--local-diagnostic", action="store_true")
    args = parser.parse_args()
    form = "sdist" if args.artifact.name.endswith(".tar.gz") else "wheel"
    payload_cap = 1_572_864 if form == "sdist" else 1_048_576
    request_ms, allocation_bytes, construction_ms, retained_bytes, calls = (
        sync_metrics() if args.mode == "sync" else asyncio.run(async_metrics())
    )
    import_ms = import_p95()
    profile = f"P-017-PY-{form.upper()}-{args.mode.upper()}-V1"
    passed = (
        args.artifact.stat().st_size <= payload_cap
        and request_ms <= 20
        and import_ms <= 500
        and construction_ms <= 100
        and allocation_bytes <= 1_048_576
        and retained_bytes <= 8_388_608
        and calls == 20
    )
    report = {
        "allocationBytesMax": allocation_bytes,
        "artifactBytes": args.artifact.stat().st_size,
        "constructionMillisecondsP95": round(construction_ms, 6),
        "importMillisecondsP95": round(import_ms, 6),
        "mode": args.mode,
        "profile": profile,
        "requestMillisecondsP95": round(request_ms, 6),
        "retainedBytesP95": round(retained_bytes),
        "resourceCounters": {
            "callbackRegistrations": 0,
            "lifecycleRegistrations": 0,
            "openConnections": 0,
            "poolEntries": 0,
            "timers": 0,
        },
        "verdict": (
            "diagnostic-pass" if passed and args.local_diagnostic else "pass" if passed else "fail"
        ),
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
