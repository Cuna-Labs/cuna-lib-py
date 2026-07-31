from __future__ import annotations

import copy

import pytest

from tools.performance_gate import evaluate_budget


def passing_budget() -> dict[str, object]:
    return {
        "allocationBytesMax": 1,
        "artifactBytes": 1,
        "connectionEstablishments": 1,
        "constructionMillisecondsP95": 1,
        "importMillisecondsP95": 1,
        "lifecycleRequestCount": 500,
        "requestMillisecondsP95": 1,
        "retainedBytesP95": 1,
        "reuseRequestCount": 10,
        "resourceCounters": {
            "asyncTasks": 0,
            "callbackRegistrations": 0,
            "lifecycleRegistrations": 0,
            "openConnections": 0,
            "openThreads": 0,
            "poolEntries": 0,
            "timers": 0,
        },
    }


@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("retainedBytesP95", 8_388_609),
        ("connectionEstablishments", 2),
        ("reuseRequestCount", 9),
        ("lifecycleRequestCount", 499),
    ],
)
def test_performance_gate_rejects_mutated_measurements(field: str, value: int) -> None:
    budget = passing_budget()
    assert evaluate_budget(budget, 1_048_576)
    budget[field] = value
    assert not evaluate_budget(budget, 1_048_576)


@pytest.mark.hermetic
@pytest.mark.parametrize("counter", ["openThreads", "timers", "asyncTasks", "openConnections"])
def test_performance_gate_rejects_retained_resources(counter: str) -> None:
    budget = passing_budget()
    mutated = copy.deepcopy(budget)
    mutated["resourceCounters"][counter] = 1  # type: ignore[index]
    assert not evaluate_budget(mutated, 1_048_576)
