from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .io import load_measurements
from .model import Measurement
from .statistics import summarize


def analyze(input_path: Path, json_path: Path, csv_path: Path) -> dict[str, object]:
    groups: dict[tuple[str, int], list[Measurement]] = defaultdict(list)
    for row in load_measurements(input_path):
        groups[(row.experiment, row.payload_bytes)].append(row)

    summaries: list[dict[str, object]] = []
    for (experiment, payload_bytes), rows in sorted(groups.items()):
        item: dict[str, object] = {
            "experiment": experiment,
            "payload_bytes": payload_bytes,
        }
        item.update(summarize(rows).to_dict())
        summaries.append(item)

    result: dict[str, object] = {"schema_version": 1, "groups": summaries}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "experiment",
        "payload_bytes",
        "total",
        "count",
        "failures",
        "failure_rate_pct",
        "minimum_ns",
        "p50_ns",
        "p95_ns",
        "p99_ns",
        "maximum_ns",
        "mean_ns",
        "stdev_ns",
        "sequential_calls_per_second",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)
    return result
