import unittest

from qfabric_stage1.bridge_runner import check_bridge, payload_for_size, roundtrip


class FakeBridge:
    def call(self, method, *args, timeout=5):
        if method != "qf_stage1_echo":
            raise AssertionError(method)
        return args[0]


class BridgeRunnerTests(unittest.TestCase):
    def test_bridge_health_check(self) -> None:
        check_bridge(FakeBridge(), timeout=1)

    def test_payload_size(self) -> None:
        self.assertEqual(len(payload_for_size(32).encode()), 32)
        with self.assertRaises(ValueError):
            payload_for_size(-1)

    def test_roundtrip_records_only_post_warmup_samples(self) -> None:
        rows = list(
            roundtrip(
                FakeBridge(),
                payload_size=8,
                iterations=3,
                warmup=2,
                timeout=1,
            )
        )
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.outcome == "ok" for row in rows))
        self.assertTrue(all(row.payload_bytes == 8 for row in rows))
        self.assertEqual(len({row.run_id for row in rows}), 1)


if __name__ == "__main__":
    unittest.main()
