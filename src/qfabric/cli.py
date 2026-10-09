from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .abi import Schema
from .abi_audit import audit_stage3, write_stage3_audit
from .abi_codegen import generate_cpp_header, write_cpp_header
from .abi_probe import probe_mcu_abi, write_probe_report
from .abi_tools import build_golden_vectors, run_compile_fail_cases, write_golden_vectors
from .audit import audit_stage2, write_audit
from .build import build_stage2
from .contract_analysis import (
    analyze_contract_sensitivity,
    audit_transition_scenario,
    build_transition_scenario,
    profile_group_to_trace,
    write_contract_trace,
    write_scenario_report,
    write_sensitivity_report,
)
from .contract_audit import audit_stage5, write_stage5_audit
from .contracts import (
    DeadlineContract,
    load_contract_trace,
    render_contract_status,
    replay_contract,
    write_contract_report,
)
from .profile_analysis import analyze_profile, write_profile_analysis
from .profile_audit import audit_stage4, write_stage4_audit
from .profile_runner import run_profile_campaign
from .profiling import Instrumentation, load_profile, render_status, write_profile
from .recommendation import (
    load_recommendation_input,
    recommend,
    render_recommendation,
    write_recommendation,
)
from .recommendation_input import (
    build_recommendation_input,
    load_operations,
    write_recommendation_input,
)
from .recommendation_scenarios import run_recommendation_scenarios, write_scenario_suite
from .runtime import parse_add_arguments, run_linux, run_rt


def _parse_positive_ints(value: str) -> list[int]:
    try:
        parsed = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as error:
        raise ValueError("expected a comma-separated list of positive integers") from error
    if not parsed or any(item < 1 for item in parsed):
        raise ValueError("expected a comma-separated list of positive integers")
    return parsed


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
    abi_audit = abi_subparsers.add_parser("audit", help="validate complete Stage 3 evidence")
    abi_audit.add_argument("--root", type=Path, default=Path.cwd())
    abi_audit.add_argument("--output", type=Path, required=True)
    abi_audit.add_argument("--timeout", type=float, default=2.0)
    abi_audit.add_argument("--address", default="unix:///var/run/arduino-router.sock")

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

    recommend_command = subparsers.add_parser(
        "recommend", help="produce advisory static domain recommendations"
    )
    recommend_command.add_argument("task", nargs="?")
    recommend_command.add_argument(
        "--input", type=Path, default=Path(".qfabric/recommendation-input.json")
    )
    recommend_command.add_argument("--output", type=Path)
    recommend_command.add_argument("--json", action="store_true", dest="as_json")

    recommend_input = subparsers.add_parser(
        "recommend-input", help="derive recommendation input from Stage 5 evidence"
    )
    recommend_input.add_argument("--stage5-root", type=Path, required=True)
    recommend_input.add_argument(
        "--abi", type=Path, default=Path("config/qfabric-abi.json")
    )
    recommend_input.add_argument(
        "--operations", type=Path, default=Path("config/stage6-operations.json")
    )
    recommend_input.add_argument("--output", type=Path, required=True)

    recommend_scenarios = subparsers.add_parser(
        "recommend-scenarios", help="run positive and negative recommendation scenarios"
    )
    recommend_scenarios.add_argument("--input", type=Path, required=True)
    recommend_scenarios.add_argument("--output", type=Path, required=True)

    contract = subparsers.add_parser(
        "contract", help="evaluate an empirical soft real-time contract"
    )
    contract_subparsers = contract.add_subparsers(dest="contract_command", required=True)
    contract_replay = contract_subparsers.add_parser(
        "replay", help="deterministically replay a recorded contract trace"
    )
    contract_replay.add_argument("--input", type=Path, required=True)
    contract_replay.add_argument("--output", type=Path, required=True)
    contract_replay.add_argument("--json", action="store_true", dest="as_json")
    contract_trace = contract_subparsers.add_parser(
        "trace", help="convert one Stage 4 profile group into a contract trace"
    )
    contract_trace.add_argument("--profile", type=Path, required=True)
    contract_trace.add_argument("--task", default="add")
    contract_trace.add_argument("--domain", choices=("linux", "rt"), required=True)
    contract_trace.add_argument(
        "--mode", choices=("disabled", "reduced", "full"), default="full"
    )
    contract_trace.add_argument("--deadline-us", type=int, required=True)
    contract_trace.add_argument("--window-size", type=int, default=100)
    contract_trace.add_argument("--minimum-samples", type=int, default=20)
    contract_trace.add_argument("--warmup-samples", type=int, default=0)
    contract_trace.add_argument("--max-miss-rate-pct", type=float, default=1.0)
    contract_trace.add_argument("--at-risk-miss-rate-pct", type=float, default=0.5)
    contract_trace.add_argument("--recovery-miss-rate-pct", type=float, default=0.25)
    contract_trace.add_argument("--violation-windows", type=int, default=3)
    contract_trace.add_argument("--recovery-windows", type=int, default=3)
    contract_trace.add_argument("--infeasible-windows", type=int, default=5)
    contract_trace.add_argument("--output", type=Path, required=True)
    contract_sensitivity = contract_subparsers.add_parser(
        "sensitivity", help="compare window and hysteresis settings for a trace"
    )
    contract_sensitivity.add_argument("--input", type=Path, required=True)
    contract_sensitivity.add_argument("--window-sizes", default="20,50,100")
    contract_sensitivity.add_argument("--violation-windows", default="1,2,3")
    contract_sensitivity.add_argument("--recovery-windows", default="1,2,3")
    contract_sensitivity.add_argument("--output", type=Path, required=True)
    contract_scenario = contract_subparsers.add_parser(
        "scenario", help="inject and audit every contract-state transition"
    )
    contract_scenario.add_argument("--input", type=Path, required=True)
    contract_scenario.add_argument("--trace-output", type=Path, required=True)
    contract_scenario.add_argument("--report-output", type=Path, required=True)
    contract_audit = contract_subparsers.add_parser(
        "audit", help="validate complete Stage 5 hardware and transition evidence"
    )
    contract_audit.add_argument("--root", type=Path, required=True)
    contract_audit.add_argument("--output", type=Path, required=True)
    contract_audit.add_argument("--minimum-hardware-observations", type=int, default=1000)

    status = subparsers.add_parser("status", help="show the latest persisted QTask profile")
    status.add_argument("--input", type=Path, default=Path(".qfabric/profile.json"))
    status.add_argument("--json", action="store_true", dest="as_json")

    profile = subparsers.add_parser("profile", help="run a correlated QTask profile campaign")
    profile.add_argument("--domain", choices=("linux", "rt", "both"), default="both")
    profile.add_argument(
        "--mode", choices=("disabled", "reduced", "full", "all"), default="full"
    )
    profile.add_argument("--iterations", type=int, default=100)
    profile.add_argument("--warmup", type=int, default=10)
    profile.add_argument("--capacity", type=int, default=1024)
    profile.add_argument("--minimum-samples", type=int, default=20)
    profile.add_argument("--deadline-us", type=int, default=20_000)
    profile.add_argument("--epoch", type=int)
    profile.add_argument("--timeout", type=float, default=2.0)
    profile.add_argument("--address", default="unix:///var/run/arduino-router.sock")
    profile.add_argument("--root", type=Path, default=Path.cwd())
    profile.add_argument("--output", type=Path, default=Path(".qfabric/profile.json"))
    profile.add_argument("--json", action="store_true", dest="as_json")

    profile_analyze = subparsers.add_parser(
        "profile-analyze", help="independently verify profile metrics and overhead"
    )
    profile_analyze.add_argument("--input", type=Path, required=True)
    profile_analyze.add_argument("--output", type=Path, required=True)
    profile_analyze.add_argument("--tolerance-pct", type=float, default=0.01)

    profile_audit = subparsers.add_parser(
        "profile-audit", help="validate complete Stage 4 profiling evidence"
    )
    profile_audit.add_argument(
        "--overhead",
        type=Path,
        default=Path("data/processed/stage4/profile-overhead.json"),
    )
    profile_audit.add_argument(
        "--cold-start",
        type=Path,
        default=Path("data/processed/stage4/profile-cold-start.json"),
    )
    profile_audit.add_argument(
        "--output", type=Path, default=Path("data/processed/stage4/stage4-audit.json")
    )
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
            if args.abi_command == "audit":
                report = audit_stage3(args.root.resolve(), args.address, timeout=args.timeout)
                write_stage3_audit(report, args.output)
                print(f"Stage 3 audit: {report['status']}")
                print(f"audit report: {args.output}")
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

        if args.command == "recommend":
            if task_arguments:
                raise ValueError("qf recommend does not accept task arguments after --")
            source = load_recommendation_input(args.input)
            report = recommend(source, task_filter=args.task)
            if args.output is not None:
                write_recommendation(report, args.output)
            print(
                json.dumps(report, indent=2, sort_keys=True)
                if args.as_json
                else render_recommendation(report)
            )
            if args.output is not None:
                print(f"recommendation report: {args.output}")
            return 0

        if args.command == "recommend-input":
            if task_arguments:
                raise ValueError("qf recommend-input does not accept task arguments")
            operations = load_operations(args.operations)
            document = build_recommendation_input(args.stage5_root, args.abi, operations)
            write_recommendation_input(document, args.output)
            print(f"recommendation input: {args.output}")
            return 0

        if args.command == "recommend-scenarios":
            if task_arguments:
                raise ValueError("qf recommend-scenarios does not accept task arguments")
            source = load_recommendation_input(args.input)
            report = run_recommendation_scenarios(source)
            write_scenario_suite(report, args.output)
            print(f"Stage 6 recommendation scenarios: {report['status']}")
            print(f"scenario report: {args.output}")
            for failure in report["failures"]:
                print(f"- {failure}", file=sys.stderr)
            return 0 if report["status"] == "pass" else 1

        if args.command == "contract":
            if task_arguments:
                raise ValueError("qf contract does not accept task arguments")
            if args.contract_command == "audit":
                report = audit_stage5(
                    args.root,
                    minimum_hardware_observations=args.minimum_hardware_observations,
                )
                write_stage5_audit(report, args.output)
                print(f"Stage 5 audit: {report['status']}")
                print(f"audit report: {args.output}")
                for failure in report["failures"]:
                    print(f"- {failure}", file=sys.stderr)
                return 0 if report["status"] == "pass" else 1
            if args.contract_command == "trace":
                contract = DeadlineContract(
                    deadline_ns=args.deadline_us * 1_000,
                    window_size=args.window_size,
                    minimum_samples=args.minimum_samples,
                    warmup_samples=args.warmup_samples,
                    max_miss_rate_pct=args.max_miss_rate_pct,
                    at_risk_miss_rate_pct=args.at_risk_miss_rate_pct,
                    recovery_miss_rate_pct=args.recovery_miss_rate_pct,
                    violation_windows=args.violation_windows,
                    recovery_windows=args.recovery_windows,
                    infeasible_windows=args.infeasible_windows,
                )
                profile = load_profile(args.profile)
                trace = profile_group_to_trace(
                    profile,
                    contract,
                    task=args.task,
                    domain=args.domain,
                    instrumentation=args.mode,
                )
                write_contract_trace(trace, args.output)
                print(
                    f"contract trace: {args.output} "
                    f"({len(trace['observations'])} observations)"
                )
                return 0
            contract, observations = load_contract_trace(args.input)
            if args.contract_command == "scenario":
                trace = build_transition_scenario(contract, observations)
                write_contract_trace(trace, args.trace_output)
                report = audit_transition_scenario(trace)
                write_scenario_report(report, args.report_output)
                print(f"Stage 5 transition scenario: {report['status']}")
                print(f"injected trace: {args.trace_output}")
                print(f"scenario report: {args.report_output}")
                for failure in report["failures"]:
                    print(f"- {failure}", file=sys.stderr)
                return 0 if report["status"] == "pass" else 1
            if args.contract_command == "sensitivity":
                report = analyze_contract_sensitivity(
                    contract,
                    observations,
                    window_sizes=_parse_positive_ints(args.window_sizes),
                    violation_windows=_parse_positive_ints(args.violation_windows),
                    recovery_windows=_parse_positive_ints(args.recovery_windows),
                )
                write_sensitivity_report(report, args.output)
                print(
                    f"contract sensitivity: {report['configuration_count']} configurations"
                )
                print(f"sensitivity report: {args.output}")
                return 0
            report = replay_contract(contract, observations)
            write_contract_report(report, args.output)
            rendered = (
                json.dumps(report, indent=2, sort_keys=True)
                if args.as_json
                else render_contract_status(report)
            )
            print(rendered)
            print(f"contract report: {args.output}")
            return 0

        if args.command == "status":
            if task_arguments:
                raise ValueError("qf status does not accept task arguments")
            report = load_profile(args.input)
            if args.as_json:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(render_status(report))
            return 0

        if args.command == "profile":
            if task_arguments:
                raise ValueError("qf profile does not accept task arguments")
            domains = ("linux", "rt") if args.domain == "both" else (args.domain,)
            modes = (
                tuple(Instrumentation)
                if args.mode == "all"
                else (Instrumentation(args.mode),)
            )
            epoch = args.epoch if args.epoch is not None else int(time.time()) & 0xFFFFFFFF
            report = run_profile_campaign(
                args.root.resolve(),
                args.address,
                domains=domains,
                modes=modes,
                iterations=args.iterations,
                warmup=args.warmup,
                capacity=args.capacity,
                minimum_samples=args.minimum_samples,
                deadline_ns=args.deadline_us * 1_000,
                epoch=epoch,
                timeout=args.timeout,
            )
            write_profile(report, args.output)
            rendered = (
                json.dumps(report, indent=2, sort_keys=True)
                if args.as_json
                else render_status(report)
            )
            print(rendered)
            print(f"profile report: {args.output}")
            return 0

        if args.command == "profile-analyze":
            if task_arguments:
                raise ValueError("qf profile-analyze does not accept task arguments")
            report = load_profile(args.input)
            analysis = analyze_profile(report, tolerance_pct=args.tolerance_pct)
            write_profile_analysis(analysis, args.output)
            print(f"Stage 4 profile analysis: {analysis['status']}")
            print(f"analysis report: {args.output}")
            for overhead in analysis["instrumentation_overhead"]:
                print(
                    f"- {overhead['domain']}/{overhead['mode']}: "
                    f"mean {overhead['mean_delta_pct']:+.3f}%, "
                    f"p95 {overhead['p95_delta_pct']:+.3f}%"
                )
            for failure in analysis["failures"]:
                print(f"- {failure}", file=sys.stderr)
            return 0 if analysis["status"] == "pass" else 1

        if args.command == "profile-audit":
            if task_arguments:
                raise ValueError("qf profile-audit does not accept task arguments")
            report = audit_stage4(args.overhead, args.cold_start)
            write_stage4_audit(report, args.output)
            print(f"Stage 4 audit: {report['status']}")
            print(f"audit report: {args.output}")
            for failure in report["failures"]:
                print(f"- {failure}", file=sys.stderr)
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
