from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .runtime import _connect_bridge

DECODE_SCENARIOS = {
    "valid": (0, 0),
    "version-mismatch": (1, 3),
    "malformed-boolean": (2, 1),
    "short-header": (3, 1),
    "oversized-message": (4, 2),
    "reserved-flags": (5, 1),
}


def probe_mcu_abi(
    vectors_path: Path,
    address: str,
    *,
    timeout: float,
) -> dict[str, object]:
    vectors_document = json.loads(vectors_path.read_text(encoding="utf-8"))
    vectors = vectors_document["vectors"]
    failures: list[str] = []
    vector_results: list[dict[str, object]] = []
    scenario_results: list[dict[str, object]] = []

    bridge: Any = _connect_bridge(address)
    try:
        for index, vector in enumerate(vectors):
            observed = bridge.call("qf_stage3_golden_vector", index, timeout=timeout)
            expected = vector["frame_hex"]
            matches = observed == expected
            vector_results.append(
                {
                    "name": vector["name"],
                    "expected_hex": expected,
                    "observed_hex": observed,
                    "matches": matches,
                }
            )
            if not matches:
                failures.append(f"MCU golden vector mismatch: {vector['name']}")

        for name, (scenario, expected) in DECODE_SCENARIOS.items():
            observed = bridge.call("qf_stage3_decode_status", scenario, timeout=timeout)
            matches = observed == expected
            scenario_results.append(
                {
                    "name": name,
                    "expected_status": expected,
                    "observed_status": observed,
                    "matches": matches,
                }
            )
            if not matches:
                failures.append(
                    f"MCU decode status mismatch for {name}: expected {expected}, got {observed}"
                )
    finally:
        bridge.disconnect()

    return {
        "schema_version": 1,
        "captured_utc": datetime.now(UTC).isoformat(),
        "protocol_version": vectors_document["protocol_version"],
        "schema_sha256": vectors_document["schema_sha256"],
        "status": "pass" if not failures else "fail",
        "vectors": vector_results,
        "decode_scenarios": scenario_results,
        "failures": failures,
    }


def write_probe_report(report: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
