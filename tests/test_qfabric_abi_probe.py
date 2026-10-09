import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qfabric.abi_probe import DECODE_SCENARIOS, probe_mcu_abi, write_probe_report

ROOT = Path(__file__).resolve().parents[1]


class FakeBridge:
    def __init__(self, vectors, *, bad_vector=False):
        self.vectors = vectors
        self.bad_vector = bad_vector
        self.disconnected = False

    def call(self, method, argument, timeout=2):
        if method == "qf_stage3_golden_vector":
            if self.bad_vector and argument == 0:
                return "bad"
            return self.vectors[argument]["frame_hex"]
        if method == "qf_stage3_decode_status":
            expected = {scenario: status for scenario, status in DECODE_SCENARIOS.values()}
            return expected[argument]
        raise AssertionError(method)

    def disconnect(self):
        self.disconnected = True


class QFabricAbiProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vectors_path = ROOT / "abi/golden-vectors.json"
        self.vectors = json.loads(self.vectors_path.read_text())["vectors"]

    def test_matching_mcu_probe_passes_and_writes_report(self) -> None:
        bridge = FakeBridge(self.vectors)
        with patch("qfabric.abi_probe._connect_bridge", return_value=bridge):
            report = probe_mcu_abi(self.vectors_path, "unix:///router.sock", timeout=1)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(bridge.disconnected)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "probe.json"
            write_probe_report(report, output)
            self.assertEqual(json.loads(output.read_text())["status"], "pass")

    def test_vector_mismatch_fails(self) -> None:
        bridge = FakeBridge(self.vectors, bad_vector=True)
        with patch("qfabric.abi_probe._connect_bridge", return_value=bridge):
            report = probe_mcu_abi(self.vectors_path, "unix:///router.sock", timeout=1)
        self.assertEqual(report["status"], "fail")
        self.assertIn("golden vector mismatch", report["failures"][0])


if __name__ == "__main__":
    unittest.main()
