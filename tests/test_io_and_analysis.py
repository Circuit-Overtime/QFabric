import json
import tempfile
import unittest
from pathlib import Path

from qfabric_stage1.analysis import analyze
from qfabric_stage1.io import append_measurements, load_measurements
from qfabric_stage1.model import Measurement


class MeasurementIoTests(unittest.TestCase):
    def test_round_trip_and_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.jsonl"
            json_path = root / "summary.json"
            csv_path = root / "summary.csv"
            rows = [
                Measurement(
                    run_id="a",
                    experiment="rpc-roundtrip",
                    sequence=index,
                    started_utc="2026-01-01T00:00:00+00:00",
                    latency_ns=latency,
                    outcome="ok",
                    payload_bytes=8,
                )
                for index, latency in enumerate((100, 200, 300))
            ]

            append_measurements(raw_path, rows)
            self.assertEqual(list(load_measurements(raw_path)), rows)

            result = analyze(raw_path, json_path, csv_path)
            self.assertEqual(result["groups"][0]["count"], 3)
            self.assertTrue(csv_path.read_text(encoding="utf-8").startswith("experiment,"))
            self.assertEqual(json.loads(json_path.read_text())["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()

