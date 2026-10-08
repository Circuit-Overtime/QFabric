from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .io import load_measurements
from .model import Measurement
from .statistics import summarize, summarize_values


def analyze(input_path: Path, json_path: Path, csv_path: Path) -> dict[str, object]:
    groups: dict[tuple[str, int, str], list[Measurement]] = defaultdict(list)
    for row in load_measurements(input_path):
        groups[(row.experiment, row.payload_bytes, row.run_id)].append(row)

    summaries: list[dict[str, object]] = []
    csv_rows: list[dict[str, object]] = []
    for (experiment, payload_bytes, run_id), rows in sorted(groups.items()):
        item: dict[str, object] = {
            "experiment": experiment,
            "payload_bytes": payload_bytes,
            "run_id": run_id,
        }
        item.update(summarize(rows).to_dict())

        csv_item = dict(item)
        diagnostic: tuple[str, str] | None = None
        if experiment == "matrix-update":
            diagnostic = ("mcu_execution", "mcu_execution_us")
        elif experiment == "mcu-linux-roundtrip":
            diagnostic = ("mcu_roundtrip", "mcu_roundtrip_us")

        if diagnostic is not None:
            csv_prefix, json_name = diagnostic
            execution = summarize_values(
                row.mcu_value for row in rows if row.outcome == "ok" and row.mcu_value is not None
            )
            item[json_name] = execution.to_dict()
            csv_item.update(
                {
                    f"{csv_prefix}_{name}_us" if name != "count" else f"{csv_prefix}_count": value
                    for name, value in execution.to_dict().items()
                }
            )
        summaries.append(item)
        csv_rows.append(csv_item)

    result: dict[str, object] = {"schema_version": 1, "groups": summaries}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "experiment",
        "payload_bytes",
        "run_id",
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
        "mcu_execution_count",
        "mcu_execution_minimum_us",
        "mcu_execution_p50_us",
        "mcu_execution_p95_us",
        "mcu_execution_p99_us",
        "mcu_execution_maximum_us",
        "mcu_execution_mean_us",
        "mcu_execution_stdev_us",
        "mcu_roundtrip_count",
        "mcu_roundtrip_minimum_us",
        "mcu_roundtrip_p50_us",
        "mcu_roundtrip_p95_us",
        "mcu_roundtrip_p99_us",
        "mcu_roundtrip_maximum_us",
        "mcu_roundtrip_mean_us",
        "mcu_roundtrip_stdev_us",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    return result
