from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build_stage2
from .runtime import parse_add_arguments, run_linux, run_rt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qf")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build Linux ARM64 and RT MCU artifacts")
    build.add_argument("--root", type=Path, default=Path.cwd())

    run = subparsers.add_parser("run", help="run one QTask on an explicit execution domain")
    run.add_argument("task")
    run.add_argument("--domain", choices=("linux", "rt"), required=True)
    run.add_argument("--root", type=Path, default=Path.cwd())
    run.add_argument("--timeout", type=float, default=2.0)
    run.add_argument("--address", default="unix:///var/run/arduino-router.sock")
    return parser


def _print_build(report: dict[str, object]) -> None:
    targets = report["targets"]
    for name in ("linux", "rt"):
        target = targets[name]
        marker = "PASS" if target["passed"] else "FAIL"
        print(f"[{marker}] {name}: {target['architecture']}")
        if not target["passed"] and target["stderr"]:
            print(target["stderr"].strip(), file=sys.stderr)
    print(f"build report: {report['report']}")


def main(argv: list[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    task_arguments: list[str] = []
    if "--" in raw_arguments:
        separator = raw_arguments.index("--")
        task_arguments = raw_arguments[separator + 1 :]
        raw_arguments = raw_arguments[:separator]
    args = build_parser().parse_args(raw_arguments)
    try:
        if args.command == "build":
            if task_arguments:
                raise ValueError("qf build does not accept task arguments")
            report = build_stage2(args.root.resolve())
            _print_build(report)
            return 0 if report["status"] == "pass" else 1

        if args.task != "add":
            raise ValueError(f"unknown QTask: {args.task}")
        a, b = parse_add_arguments(task_arguments)
        if args.domain == "linux":
            result = run_linux(args.root.resolve(), a, b)
        else:
            result = run_rt(args.address, a, b, timeout=args.timeout)
        print(result)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
