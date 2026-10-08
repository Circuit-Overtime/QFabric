import threading
import time
import unittest

from qfabric_stage1.bridge_runner import (
    check_bridge,
    concurrent_roundtrips,
    mcu_to_linux_roundtrips,
    payload_for_size,
    resource_snapshot,
    roundtrip,
)


class FakeBridge:
    def call(self, method, *args, timeout=5):
        if method != "qf_stage1_echo":
            raise AssertionError(method)
        return args[0]

    def provide(self, method, handler):
        raise AssertionError(method)

    def unprovide(self, method):
        raise AssertionError(method)


class FakeReverseBridge:
    def __init__(self):
        self.handler = None
        self.duration_us = None
        self.pending_polls = 0

    def provide(self, method, handler):
        if method != "qf_stage1_linux_echo":
            raise AssertionError(method)
        self.handler = handler

    def unprovide(self, method):
        if method != "qf_stage1_linux_echo":
            raise AssertionError(method)
        self.handler = None

    def call(self, method, *args, timeout=5):
        if method == "qf_stage1_reverse_start":
            if self.handler is None:
                raise AssertionError("handler is unavailable")
            token = args[0]
            if self.handler(token) != token:
                raise AssertionError("token mismatch")
            self.duration_us = 42
            self.pending_polls = 1
            return True
        if method == "qf_stage1_reverse_result":
            if self.pending_polls:
                self.pending_polls -= 1
                return -1
            return self.duration_us
        raise AssertionError(method)


class FakeResourceBridge:
    def __init__(self):
        self.reset = False

    def call(self, method, *args, timeout=5):
        if method == "qf_stage1_resource_constant":
            return (32768, 32768, 500, 1024, 256, 0)[args[0]]
        if method == "qf_stage1_diagnostic":
            return (123, 456, 789, 1000)[args[0]]
        if method == "qf_stage1_reset_diagnostics":
            self.reset = True
            return True
        raise AssertionError(method)


class FakeConcurrentBridge:
    def __init__(self):
        self.active = 0
        self.maximum_active = 0
        self.lock = threading.Lock()

    def call(self, method, *args, timeout=5):
        if method != "qf_stage1_echo":
            raise AssertionError(method)
        with self.lock:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
        time.sleep(0.005)
        with self.lock:
            self.active -= 1
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

    def test_mcu_to_linux_roundtrip(self) -> None:
        bridge = FakeReverseBridge()
        rows = list(
            mcu_to_linux_roundtrips(
                bridge,
                iterations=3,
                warmup=2,
                timeout=1,
            )
        )
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.outcome == "ok" for row in rows))
        self.assertTrue(all(row.mcu_value == 42 for row in rows))
        self.assertEqual(len({row.run_id for row in rows}), 1)
        self.assertIsNone(bridge.handler)

    def test_resource_snapshot(self) -> None:
        bridge = FakeResourceBridge()
        result = resource_snapshot(
            bridge,
            timeout=1,
            reset_after=True,
        )
        self.assertEqual(result["constants"]["rpc_request_buffer_bytes"], 256)
        self.assertFalse(result["capabilities"]["stack_watermark"])
        self.assertEqual(
            result["limitations"]["runtime_allocation_probe"],
            "disabled-unsafe-on-stock-uno-q",
        )
        self.assertEqual(result["diagnostics"]["maximum_loop_gap_us"], 789)
        self.assertTrue(result["diagnostics_reset_after_capture"])
        self.assertTrue(bridge.reset)

    def test_concurrent_roundtrips_bound_outstanding_calls(self) -> None:
        bridge = FakeConcurrentBridge()
        rows = list(
            concurrent_roundtrips(
                bridge,
                payload_size=8,
                workers=3,
                iterations=7,
                warmup=3,
                timeout=1,
            )
        )
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row.outcome == "ok" for row in rows))
        self.assertTrue(all(row.experiment == "rpc-concurrency-3" for row in rows))
        self.assertTrue(all(row.concurrency == 3 for row in rows))
        self.assertEqual(len({row.batch_elapsed_ns for row in rows}), 1)
        self.assertGreater(rows[0].batch_elapsed_ns, 0)
        self.assertEqual(bridge.maximum_active, 3)


if __name__ == "__main__":
    unittest.main()
