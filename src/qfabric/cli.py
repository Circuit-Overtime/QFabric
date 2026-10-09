from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .abi import Schema
from .abi_codegen import generate_cpp_header, write_cpp_header
from .abi_probe import probe_mcu_abi, write_probe_report
from .abi_tools import build_golden_vectors, run_compile_fail_cases, write_golden_vectors
from .audit import audit_stage2, write_audit
from .build import build_stage2
from .runtime import parse_add_arguments, run_linux, run_rt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qf")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build Linux ARM64 and RT MCU artifacts")
    build.add_argument("--root", type=Path, default=Path.cwd())

    abi = subparsers.add_parser("abi", help="validate the ABI schema and golden vectors")
    abi_subparsers = abi.add_subparsers(dest="abi_command", required=True)
    abi_check = abi_subparsers.add_parser("check", help="validate ABI declarations")
    abi_check.add_argument("--schema", type=Path, default=Path("config/qfabric-abi.json"))
    abi_vectors = abi_subparsers.add_parser("vectors", help="generate canonical golden vectors")
    abi_vectors.add_argument("--schema", type=Path, default=Path("config/qfabric-abi.json"))
    abi_vectors.add_argument("--output", type=Path, default=Path("abi/golden-vectors.json"))
    abi_generate = abi_subparsers.add_parser("generate", help="generate the C++ ABI codec")
    abi_generate.add_argument("--schema", type=Path, default=Path("config/qfabric-abi.json"))
    abi_generate.add_argument(
        "--output", type=Path, default=Path("generated/qfabric_abi.hpp")
    )
    abi_probe = abi_subparsers.add_parser("probe", help="verify the generated codec on the MCU")
    abi_probe.add_argument("--vectors", type=Path, default=Path("abi/golden-vectors.json"))
    abi_probe.add_argument("--output", type=Path, required=True)
    abi_probe.add_argument("--timeout", type=float, default=2.0)
    abi_probe.add_argument("--address", default="unix:///var/run/arduino-router.sock")
    abi_compile_fail = abi_subparsers.add_parser(
        "compile-fail", help="verify rejection of unsupported ABI declarations"
    )
    abi_compile_fail.add_argument(
        "--cases", type=Path, default=Path("tests/abi_compile_fail")
    )

    audit = subparsers.add_parser("audit", help="validate the complete Stage 2 evidence")
    audit.add_argument("--root", type=Path, default=Path.cwd())
    audit.add_argument("--output", type=Path, required=True)
    audit.add_argument("--timeout", type=float, default=2.0)
    audit.add_argument("--address", default="unix:///var/run/arduino-router.sock")

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
        if args.command == "abi":
            if task_arguments:
                raise ValueError("qf abi does not accept task arguments")
            if args.abi_command == "check":
                schema = Schema.load(args.schema)
                print(
                    f"ABI schema valid: {len(schema.tasks)} tasks, "
                    f"{len(schema.types)} named types"
                )
                return 0
            if args.abi_command == "vectors":
                vectors = build_golden_vectors(args.schema)
                write_golden_vectors(vectors, args.output)
                print(f"golden vectors: {args.output}")
                return 0
            if args.abi_command == "probe":
                report = probe_mcu_abi(args.vectors, args.address, timeout=args.timeout)
                write_probe_report(report, args.output)
                print(f"Stage 3 MCU ABI probe: {report['status']}")
                print(f"probe report: {args.output}")
                for failure in report["failures"]:
                    print(f"- {failure}", file=sys.stderr)
                return 0 if report["status"] == "pass" else 1
            if args.abi_command == "compile-fail":
                report = run_compile_fail_cases(args.cases)
                for case in report["cases"]:
                    marker = "PASS" if case["rejected"] else "FAIL"
                    print(f"[{marker}] {case['case']}: {case['diagnostic'] or 'accepted'}")
                for failure in report["failures"]:
                    print(f"- {failure}", file=sys.stderr)
                return 0 if report["status"] == "pass" else 1
            header = generate_cpp_header(args.schema)
            write_cpp_header(header, args.output)
            print(f"generated C++ codec: {args.output}")
            return 0

        if args.command == "build":
            if task_arguments:
                raise ValueError("qf build does not accept task arguments")
            report = build_stage2(args.root.resolve())
            _print_build(report)
            return 0 if report["status"] == "pass" else 1

        if args.command == "audit":
            if task_arguments:
                raise ValueError("qf audit does not accept task arguments")
            result = audit_stage2(args.root.resolve(), args.address, timeout=args.timeout)
            write_audit(result, args.output)
            print(f"Stage 2 audit: {result['status']}")
            print(f"audit report: {args.output}")
            for failure in result["failures"]:
                print(f"- {failure}", file=sys.stderr)
            return 0 if result["status"] == "pass" else 1

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
