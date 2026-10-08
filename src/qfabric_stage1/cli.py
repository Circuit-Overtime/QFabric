from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

from .analysis import analyze
from .bridge_runner import (
    check_bridge,
    clock_samples,
    concurrent_roundtrips,
    matrix_updates,
    mcu_to_linux_roundtrips,
    resource_snapshot,
    roundtrip,
)
from .io import append_measurements
from .model import Measurement
from .statistics import summarize


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def nonnegative_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("cannot be negative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qf-stage1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run one hardware benchmark")
    run.add_argument(
        "experiment", choices=("roundtrip", "concurrency", "reverse", "clock", "matrix")
    )
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--iterations", type=positive_integer, default=1000)
    run.add_argument("--warmup", type=nonnegative_integer, default=100)
    run.add_argument("--timeout", type=float, default=5.0)
    run.add_argument("--payload-size", type=nonnegative_integer, default=0)
    run.add_argument("--workers", type=positive_integer, default=1)
    run.add_argument("--address", default="unix:///var/run/arduino-router.sock")

    check = subparsers.add_parser("check", help="verify Router and MCU benchmark availability")
    check.add_argument("--timeout", type=float, default=2.0)
    check.add_argument("--address", default="unix:///var/run/arduino-router.sock")

    resources = subparsers.add_parser(
        "resources", help="capture MCU capacity and runtime headroom diagnostics"
    )
    resources.add_argument("--output", type=Path, required=True)
    resources.add_argument("--timeout", type=float, default=5.0)
    resources.add_argument("--reset-after", action="store_true")
    resources.add_argument("--address", default="unix:///var/run/arduino-router.sock")

    analysis = subparsers.add_parser("analyze", help="summarize JSONL measurements")
    analysis.add_argument("--input", type=Path, required=True)
    analysis.add_argument("--json", type=Path, required=True)
    analysis.add_argument("--csv", type=Path, required=True)
    return parser


def connect_bridge(address: str):
    try:
        from arduino.router_bridge import Bridge
    except ImportError as error:
        raise RuntimeError("arduino-router-bridge is not installed; see docs/stage-1.md") from error

    bridge = Bridge(address=address)
    if not bridge.connect(timeout=5):
        bridge.disconnect()
        raise RuntimeError(f"could not connect to Arduino Router at {address}")
    return bridge


def print_summary(rows: Iterable[Measurement]) -> list[Measurement]:
    collected = list(rows)
    result: dict[str, object] = summarize(collected).to_dict()
    batch_elapsed_values = {
        row.batch_elapsed_ns for row in collected if row.batch_elapsed_ns is not None
    }
    if len(batch_elapsed_values) == 1:
        batch_elapsed_ns = batch_elapsed_values.pop()
        assert batch_elapsed_ns is not None
        if batch_elapsed_ns <= 0:
            raise ValueError("concurrent batch timing must be positive")
        concurrency_values = {row.concurrency for row in collected}
        if len(concurrency_values) != 1:
            raise ValueError("concurrent measurements contain inconsistent worker counts")
        successful = sum(row.outcome == "ok" for row in collected)
        result.update(
            {
                "concurrency": concurrency_values.pop(),
                "concurrent_batch_elapsed_ns": batch_elapsed_ns,
                "concurrent_attempts_per_second": len(collected)
                * 1_000_000_000
                / batch_elapsed_ns,
                "concurrent_successes_per_second": successful
                * 1_000_000_000
                / batch_elapsed_ns,
            }
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return collected


def run_hardware(args: argparse.Namespace) -> int:
    bridge = connect_bridge(args.address)
    try:
        if args.experiment == "roundtrip":
            rows = roundtrip(
                bridge,
                payload_size=args.payload_size,
                iterations=args.iterations,
                warmup=args.warmup,
                timeout=args.timeout,
            )
        elif args.experiment == "concurrency":
            rows = concurrent_roundtrips(
                bridge,
                payload_size=args.payload_size,
                workers=args.workers,
                iterations=args.iterations,
                warmup=args.warmup,
                timeout=args.timeout,
            )
        elif args.experiment == "reverse":
            rows = mcu_to_linux_roundtrips(
                bridge,
                iterations=args.iterations,
                warmup=args.warmup,
                timeout=args.timeout,
            )
        elif args.experiment == "clock":
            rows = clock_samples(
                bridge,
                iterations=args.iterations,
                warmup=args.warmup,
                timeout=args.timeout,
            )
        else:
            rows = matrix_updates(
                bridge,
                iterations=args.iterations,
                warmup=args.warmup,
                timeout=args.timeout,
            )

        collected = print_summary(rows)
        append_measurements(args.output, collected)
        return 0 if all(row.outcome == "ok" for row in collected) else 2
    finally:
        bridge.disconnect()


def check_hardware(args: argparse.Namespace) -> int:
    bridge = connect_bridge(args.address)
    try:
        check_bridge(bridge, timeout=args.timeout)
        print("Stage 1 Bridge health check passed")
        return 0
    finally:
        bridge.disconnect()


def capture_resources(args: argparse.Namespace) -> int:
    bridge = connect_bridge(args.address)
    try:
        snapshot = resource_snapshot(
            bridge,
            timeout=args.timeout,
            reset_after=args.reset_after,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0
    finally:
        bridge.disconnect()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            result = analyze(args.input, args.json, args.csv)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "check":
            return check_hardware(args)
        if args.command == "resources":
            return capture_resources(args)
        return run_hardware(args)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
