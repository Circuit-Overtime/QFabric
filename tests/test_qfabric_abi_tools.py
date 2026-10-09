import json
import tempfile
import unittest
from pathlib import Path

from qfabric.abi_tools import build_golden_vectors, write_golden_vectors

ROOT = Path(__file__).resolve().parents[1]


class QFabricAbiToolsTests(unittest.TestCase):
    def test_golden_vectors_are_reproducible(self) -> None:
        schema = ROOT / "config/qfabric-abi.json"
        first = build_golden_vectors(schema)
        second = build_golden_vectors(schema)
        self.assertEqual(first, second)
        self.assertEqual(
            json.loads((ROOT / "abi/golden-vectors.json").read_text()),
            first,
        )
        self.assertEqual(len(first["vectors"]), 3)
        self.assertEqual(
            first["vectors"][0]["payload_hex"],
            "800000007fffffff",
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "abi/golden-vectors.json"
            write_golden_vectors(first, output)
            self.assertEqual(json.loads(output.read_text()), first)


if __name__ == "__main__":
    unittest.main()
