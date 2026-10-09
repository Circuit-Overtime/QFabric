import unittest

from qfabric.contract_analysis import analyze_contract_sensitivity, profile_group_to_trace
from qfabric.contracts import ContractObservation, DeadlineContract


def policy(**changes) -> DeadlineContract:
    values = {
        "deadline_ns": 100,
        "window_size": 4,
        "minimum_samples": 2,
        "warmup_samples": 0,
        "max_miss_rate_pct": 25,
        "at_risk_miss_rate_pct": 10,
        "recovery_miss_rate_pct": 0,
        "violation_windows": 2,
        "recovery_windows": 2,
        "infeasible_windows": 3,
    }
    values.update(changes)
    return DeadlineContract(**values)


class QFabricContractAnalysisTests(unittest.TestCase):
    def test_profile_group_conversion_preserves_outcomes_and_provenance(self) -> None:
        profile = {
            "schema_version": 1,
            "groups": [
                {
                    "task": "add",
                    "domain": "rt",
                    "instrumentation": "full",
                    "samples": [
                        {"outcome": "ok", "end_to_end_ns": 80},
                        {"outcome": "timeout", "end_to_end_ns": None},
                        {"outcome": "ok", "end_to_end_ns": None},
                    ],
                }
            ],
        }
        trace = profile_group_to_trace(
            profile, policy(), task="add", domain="rt", instrumentation="full"
        )
        self.assertEqual(trace["provenance"]["source_retained_samples"], 3)
        self.assertTrue(trace["provenance"]["source_warmup_already_excluded"])
        self.assertEqual(
            [observation["outcome"] for observation in trace["observations"]],
            ["ok", "timeout", "missing"],
        )

    def test_profile_selector_must_be_unique(self) -> None:
        with self.assertRaisesRegex(ValueError, "matched 0"):
            profile_group_to_trace(
                {"schema_version": 1, "groups": []},
                policy(),
                task="add",
                domain="linux",
                instrumentation="full",
            )

    def test_sensitivity_exposes_window_and_hysteresis_detection_cost(self) -> None:
        observations = (
            [ContractObservation("ok", 50)] * 4
            + [ContractObservation("ok", 101)] * 8
            + [ContractObservation("ok", 50)] * 8
        )
        report = analyze_contract_sensitivity(
            policy(),
            observations,
            window_sizes=[2, 4],
            violation_windows=[1, 2],
            recovery_windows=[1, 2],
        )
        self.assertEqual(report["configuration_count"], 8)
        configurations = report["configurations"]
        fastest = next(
            row
            for row in configurations
            if row["window_size"] == 2
            and row["violation_windows"] == 1
            and row["recovery_windows"] == 1
        )
        cautious = next(
            row
            for row in configurations
            if row["window_size"] == 4
            and row["violation_windows"] == 2
            and row["recovery_windows"] == 2
        )
        self.assertEqual(fastest["sustained_violation_detection_bound_observations"], 2)
        self.assertEqual(cautious["sustained_violation_detection_bound_observations"], 8)
        self.assertLess(
            fastest["first_entry_observation"]["VIOLATED"],
            cautious["first_entry_observation"]["VIOLATED"],
        )

    def test_sensitivity_rejects_windows_below_minimum_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least minimum_samples"):
            analyze_contract_sensitivity(
                policy(minimum_samples=4),
                [ContractObservation("ok", 50)] * 4,
                window_sizes=[2],
                violation_windows=[1],
                recovery_windows=[1],
            )


if __name__ == "__main__":
    unittest.main()
