from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .visualization_runtime import MODE_IDS, set_view

CASES = (
    ("placement-stable", "placement", 1, "SATISFIED", "stable"),
    ("placement-transition", "placement", 2, "SATISFIED", "transition"),
    ("contracts-unknown", "contracts", 3, "UNKNOWN", "stable"),
    ("contracts-at-risk", "contracts", 6, "AT_RISK", "stable"),
    ("contracts-violated", "contracts", 12, "VIOLATED", "stable"),
    ("jitter-measured", "jitter", 11, "VIOLATED", "rollback"),
    ("ipc-active", "ipc", 6, "AT_RISK", "stable"),
    ("placement-rollback", "placement", 11, "VIOLATED", "rollback"),
    ("placement-infeasible", "placement", 15, "VIOLATED", "infeasible"),
)


def _validate_case(
    report: dict[str, Any],
    *,
    mode: str,
    decision_id: int,
    state: str,
    event: str,
    refresh_hz: int,
) -> list[str]:
    diagnostics = report["diagnostics"]
    telemetry = report["telemetry"]
    failures: list[str] = []
    expected = {
        "mode": mode,
        "decision_id": decision_id,
        "state": state,
        "event": event,
        "mode_id": int(MODE_IDS[mode]),
        "refresh_hz": refresh_hz,
        "frame_checksum": report["frame_checksum"],
    }
    observed = {
        "mode": report["mode"],
        "decision_id": diagnostics["last_decision_id"],
        "state": telemetry["contract_state"],
        "event": telemetry["event"],
        "mode_id": diagnostics["mode_id"],
        "refresh_hz": diagnostics["target_refresh_hz"],
        "frame_checksum": diagnostics["frame_checksum"],
    }
    for key, value in expected.items():
        if observed[key] != value:
            failures.append(f"{key}: expected {value!r}, observed {observed[key]!r}")
    if diagnostics["applied_frames"] < 1:
        failures.append("MCU did not apply a frame")
    if diagnostics["last_draw_us"] < 0:
        failures.append("MCU reported an invalid draw duration")
    return failures


def run_visualization_campaign(
    history: Path,
    address: str,
    *,
    refresh_hz: int = 8,
    overlay_ms: int = 100,
    timeout: float = 2.0,
) -> dict[str, object]:
    cases: list[dict[str, object]] = []
    failures: list[str] = []
    off: dict[str, object] | None = None
    try:
        for name, mode, decision_id, state, event in CASES:
            report = set_view(
                mode,
                history=history,
                task="add",
                decision_id=decision_id,
                address=address,
                refresh_hz=refresh_hz,
                overlay_ms=overlay_ms,
                timeout=timeout,
            )
            case_failures = _validate_case(
                report,
                mode=mode,
                decision_id=decision_id,
                state=state,
                event=event,
                refresh_hz=refresh_hz,
            )
            failures.extend(f"{name}: {failure}" for failure in case_failures)
            cases.append(
                {
                    "name": name,
                    "status": "pass" if not case_failures else "fail",
                    **report,
                }
            )
    finally:
        off = set_view(
            "off",
            history=history,
            task="add",
            decision_id=None,
            address=address,
            refresh_hz=refresh_hz,
            overlay_ms=0,
            timeout=timeout,
        )
    off_diagnostics = off["diagnostics"]
    if (
        off_diagnostics["mode_id"] != 0
        or off_diagnostics["target_refresh_hz"] != 0
        or off_diagnostics["frame_checksum"] != 0
    ):
        failures.append("off: MCU did not enter a blank disabled state")
    return {
        "schema_version": 1,
        "captured_utc": datetime.now(UTC).isoformat(),
        "stage": 9,
        "status": "pass" if not failures else "fail",
        "configuration": {
            "history": str(history),
            "refresh_hz": refresh_hz,
            "overlay_ms": overlay_ms,
        },
        "cases": cases,
        "off": off,
        "failures": failures,
    }


def write_visualization_campaign(report: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
