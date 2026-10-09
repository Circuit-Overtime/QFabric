import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qfabric.cli import main
from qfabric.contracts import ContractObservation, DeadlineContract
from qfabric.profiling import Instrumentation, ProfileCollector, ProfileSample, write_profile


class QFabricCliTests(unittest.TestCase):
    def test_contract_trace_replay_command(self) -> None:
        contract = DeadlineContract(
            deadline_ns=100,
            window_size=2,
            minimum_samples=2,
            warmup_samples=0,
            max_miss_rate_pct=25,
            at_risk_miss_rate_pct=10,
            recovery_miss_rate_pct=0,
            violation_windows=2,
            recovery_windows=2,
            infeasible_windows=3,
        )
        trace = {
            "schema_version": 1,
            "contract": contract.to_dict(),
            "observations": [
                ContractObservation("ok", 50).to_dict(),
                ContractObservation("ok", 60).to_dict(),
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.json"
            report_path = Path(directory) / "report.json"
            trace_path.write_text(json.dumps(trace), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "contract",
                        "replay",
                        "--input",
                        str(trace_path),
                        "--output",
                        str(report_path),
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("state: SATISFIED", output.getvalue())
            self.assertEqual(json.loads(report_path.read_text())["state"], "SATISFIED")

    def test_status_human_and_json_output(self) -> None:
        collector = ProfileCollector(capacity=2, warmup=0, minimum_samples=1)
        collector.add(
            ProfileSample(
                task="add",
                task_id=1,
                invocation_id=1,
                epoch=1,
                domain="linux",
                instrumentation=Instrumentation.REDUCED,
                outcome="ok",
                linux_started_ns=10,
                linux_finished_ns=20,
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "profile.json"
            write_profile(collector.report(), profile)
            human = io.StringIO()
            with contextlib.redirect_stdout(human):
                status = main(["status", "--input", str(profile)])
            self.assertEqual(status, 0)
            self.assertIn("QFabric profile status", human.getvalue())

            machine = io.StringIO()
            with contextlib.redirect_stdout(machine):
                status = main(["status", "--input", str(profile), "--json"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(machine.getvalue())["schema_version"], 1)

    def test_abi_check_and_vector_commands(self) -> None:
        root = Path(__file__).resolve().parents[1]
        schema = root / "config/qfabric-abi.json"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["abi", "check", "--schema", str(schema)])
        self.assertEqual(status, 0)
        self.assertIn("ABI schema valid", output.getvalue())

        with tempfile.TemporaryDirectory() as directory:
            vectors = Path(directory) / "vectors.json"
            status = main(
                ["abi", "vectors", "--schema", str(schema), "--output", str(vectors)]
            )
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(vectors.read_text())["protocol_version"], 1)

    def test_required_linux_command_shape(self) -> None:
        output = io.StringIO()
        with (
            patch("qfabric.cli.run_linux", return_value=5) as run,
            contextlib.redirect_stdout(output),
        ):
            status = main(["run", "add", "--domain", "linux", "--", "2", "3"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "5\n")
        self.assertEqual(run.call_args.args[1:], (2, 3))

    def test_required_rt_command_shape(self) -> None:
        output = io.StringIO()
        with (
            patch("qfabric.cli.run_rt", return_value=5) as run,
            contextlib.redirect_stdout(output),
        ):
            status = main(["run", "add", "--domain", "rt", "--", "2", "3"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "5\n")
        self.assertEqual(run.call_args.args[1:3], (2, 3))

    def test_domains_share_validation_error(self) -> None:
        errors = []
        for domain in ("linux", "rt"):
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = main(["run", "add", "--domain", domain, "--", "2"])
            self.assertEqual(status, 1)
            errors.append(error.getvalue())
        self.assertEqual(errors[0], errors[1])


if __name__ == "__main__":
    unittest.main()
