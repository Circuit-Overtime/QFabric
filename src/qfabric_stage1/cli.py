from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

from .analysis import analyze
from .bridge_runner import clock_samples, matrix_updates, roundtrip
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
    run.add_argument("experiment", choices=("roundtrip", "clock", "matrix"))
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--iterations", type=positive_integer, default=1000)
    run.add_argument("--warmup", type=nonnegative_integer, default=100)
    run.add_argument("--timeout", type=float, default=5.0)
    run.add_argument("--payload-size", type=nonnegative_integer, default=0)
    run.add_argument("--address", default="unix:///var/run/arduino-router.sock")

    analysis = subparsers.add_parser("analyze", help="summarize JSONL measurements")
    analysis.add_argument("--input", type=Path, required=True)
    analysis.add_argument("--json", type=Path, required=True)
    analysis.add_argument("--csv", type=Path, required=True)
    return parser


def connect_bridge(address: str):
    try:
        from arduino.router_bridge import Bridge
    except ImportError as error:
        raise RuntimeError(
            "arduino-router-bridge is not installed; see docs/stage-1.md"
        ) from error

    bridge = Bridge(address=address)
    if not bridge.connect(timeout=5):
        bridge.disconnect()
        raise RuntimeError(f"could not connect to Arduino Router at {address}")
    return bridge


def print_summary(rows: Iterable[Measurement]) -> list[Measurement]:
    collected = list(rows)
    print(json.dumps(summarize(collected).to_dict(), indent=2, sort_keys=True))
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            result = analyze(args.input, args.json, args.csv)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        return run_hardware(args)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

