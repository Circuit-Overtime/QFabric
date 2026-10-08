from __future__ import annotations

import math
from collections.abc import Iterable

from .model import Measurement, Summary


def percentile(values: Iterable[int], percentage: float) -> float:
    """Return a linearly interpolated percentile for 0 <= percentage <= 100."""
    if not 0 <= percentage <= 100:
        raise ValueError("percentage must be between 0 and 100")

    ordered = sorted(values)
    if not ordered:
        raise ValueError("at least one value is required")
    if len(ordered) == 1:
        return float(ordered[0])

    position = (len(ordered) - 1) * percentage / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])

    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize(measurements: Iterable[Measurement]) -> Summary:
    rows = list(measurements)
    successful = [row.latency_ns for row in rows if row.outcome == "ok"]
    failures = len(rows) - len(successful)

    if not successful:
        return Summary(
            total=len(rows),
            count=0,
            failures=failures,
            failure_rate_pct=(100 * failures / len(rows) if rows else 0),
            minimum_ns=None,
            p50_ns=None,
            p95_ns=None,
            p99_ns=None,
            maximum_ns=None,
            mean_ns=None,
            stdev_ns=None,
            sequential_calls_per_second=None,
        )

    mean = sum(successful) / len(successful)
    variance = sum((value - mean) ** 2 for value in successful) / len(successful)
    return Summary(
        total=len(rows),
        count=len(successful),
        failures=failures,
        failure_rate_pct=100 * failures / len(rows),
        minimum_ns=min(successful),
        p50_ns=percentile(successful, 50),
        p95_ns=percentile(successful, 95),
        p99_ns=percentile(successful, 99),
        maximum_ns=max(successful),
        mean_ns=mean,
        stdev_ns=math.sqrt(variance),
        sequential_calls_per_second=(1_000_000_000 / mean if mean > 0 else None),
    )
