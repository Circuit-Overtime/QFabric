from __future__ import annotations

import itertools
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

from .contracts import (
    CONTRACT_SCHEMA_VERSION,
    ContractObservation,
    ContractState,
    DeadlineContract,
    replay_contract,
)

SENSITIVITY_SCHEMA_VERSION = 1


def profile_group_to_trace(
    profile: dict[str, object],
    contract: DeadlineContract,
    *,
    task: str,
    domain: str,
    instrumentation: str,
) -> dict[str, object]:
    groups = profile["groups"]
    matches = [
        group
        for group in groups
        if group.get("task") == task
        and group.get("domain") == domain
        and group.get("instrumentation") == instrumentation
    ]
    if len(matches) != 1:
        raise ValueError(
            "profile selector must match exactly one group: "
            f"task={task}, domain={domain}, instrumentation={instrumentation}; "
            f"matched {len(matches)}"
        )
    group = matches[0]
    observations = [_sample_to_observation(sample) for sample in group["samples"]]
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract": contract.to_dict(),
        "provenance": {
            "source": "qfabric-stage4-profile",
            "source_profile_schema_version": profile["schema_version"],
            "task": task,
            "domain": domain,
            "instrumentation": instrumentation,
            "source_retained_samples": len(observations),
            "source_warmup_already_excluded": True,
        },
        "observations": [observation.to_dict() for observation in observations],
    }


def _sample_to_observation(sample: dict[str, Any]) -> ContractObservation:
    outcome = sample.get("outcome")
    latency = sample.get("end_to_end_ns")
    if outcome == "ok" and isinstance(latency, int) and latency >= 0:
        return ContractObservation("ok", latency)
    if outcome in {"error", "timeout"}:
        return ContractObservation(outcome)
    return ContractObservation("missing")


def write_contract_trace(trace: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def analyze_contract_sensitivity(
    base_contract: DeadlineContract,
    observations: list[ContractObservation],
    *,
    window_sizes: list[int],
    violation_windows: list[int],
    recovery_windows: list[int],
) -> dict[str, object]:
    for name, values in (
        ("window_sizes", window_sizes),
        ("violation_windows", violation_windows),
        ("recovery_windows", recovery_windows),
    ):
        if not values or any(value < 1 for value in values):
            raise ValueError(f"{name} must contain positive integers")
    if any(size < base_contract.minimum_samples for size in window_sizes):
        raise ValueError("every sensitivity window must be at least minimum_samples")

    configurations = []
    for window_size, violation_count, recovery_count in itertools.product(
        sorted(set(window_sizes)),
        sorted(set(violation_windows)),
        sorted(set(recovery_windows)),
    ):
        infeasible_count = max(base_contract.infeasible_windows, violation_count)
        contract = replace(
            base_contract,
            window_size=window_size,
            violation_windows=violation_count,
            recovery_windows=recovery_count,
            infeasible_windows=infeasible_count,
        )
        replay = replay_contract(contract, observations)
        first_entry = {
            state.value: next(
                (
                    window["window_index"]
                    for window in replay["windows"]
                    if window["state_after"] == state.value
                ),
                None,
            )
            for state in ContractState
            if state != ContractState.UNKNOWN
        }
        first_entry_observation = {
            state: (
                None
                if window_index is None
                else base_contract.warmup_samples + window_index * window_size
            )
            for state, window_index in first_entry.items()
        }
        configurations.append(
            {
                "window_size": window_size,
                "violation_windows": violation_count,
                "recovery_windows": recovery_count,
                "infeasible_windows": infeasible_count,
                "final_state": replay["state"],
                "complete_windows": len(replay["windows"]),
                "pending_samples": replay["pending_samples"],
                "transition_count": sum(
                    bool(window["transitioned"]) for window in replay["windows"]
                ),
                "first_entry_window": first_entry,
                "first_entry_observation": first_entry_observation,
                "sustained_violation_detection_bound_observations": (
                    base_contract.warmup_samples + violation_count * window_size
                ),
            }
        )

    state_counts = Counter(configuration["final_state"] for configuration in configurations)
    return {
        "schema_version": SENSITIVITY_SCHEMA_VERSION,
        "claim": "empirical-soft-real-time",
        "source_observations": len(observations),
        "base_contract": base_contract.to_dict(),
        "configuration_count": len(configurations),
        "final_state_counts": dict(sorted(state_counts.items())),
        "configurations": configurations,
    }


def write_sensitivity_report(report: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
