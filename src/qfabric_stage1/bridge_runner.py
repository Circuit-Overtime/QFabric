from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime
from typing import Any, Protocol

from .model import Measurement


class BridgeClient(Protocol):
    def call(self, method: str, *args: Any, timeout: float = 5) -> Any: ...

    def provide(self, method: str, handler: Callable[..., Any]) -> None: ...

    def unprovide(self, method: str) -> None: ...


def check_bridge(bridge: BridgeClient, *, timeout: float) -> None:
    payload = "qfabric-health-check"
    value = bridge.call("qf_stage1_echo", payload, timeout=timeout)
    if value != payload:
        raise RuntimeError(f"Bridge health check returned an invalid result: {value!r}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def payload_for_size(size: int) -> str:
    if size < 0:
        raise ValueError("payload size cannot be negative")
    return "q" * size


def _measure_calls(
    bridge: BridgeClient,
    *,
    experiment: str,
    method: str,
    arguments: Callable[[int], tuple[Any, ...]],
    iterations: int,
    warmup: int,
    timeout: float,
    payload_bytes: int = 0,
    validate: Callable[[Any, int], bool] | None = None,
) -> Iterator[Measurement]:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if warmup < 0:
        raise ValueError("warmup cannot be negative")

    for sequence in range(-warmup, iterations):
        args = arguments(sequence)
        started_utc = utc_now()
        started_ns = time.perf_counter_ns()
        try:
            value = bridge.call(method, *args, timeout=timeout)
            latency_ns = time.perf_counter_ns() - started_ns
            valid = validate(value, sequence) if validate else True
            outcome = "ok" if valid else "invalid-result"
            detail = None if valid else repr(value)
            mcu_value = value if isinstance(value, int) and not isinstance(value, bool) else None
        except Exception as error:  # The error class depends on the installed Bridge package.
            latency_ns = time.perf_counter_ns() - started_ns
            outcome = "error"
            detail = f"{type(error).__name__}: {error}"
            mcu_value = None

        if sequence >= 0:
            yield Measurement(
                run_id="",  # Assigned by the public wrapper for a whole experiment run.
                experiment=experiment,
                sequence=sequence,
                started_utc=started_utc,
                latency_ns=latency_ns,
                outcome=outcome,
                payload_bytes=payload_bytes,
                mcu_value=mcu_value,
                detail=detail,
            )


def with_run_id(rows: Iterable[Measurement], run_id: str | None = None) -> Iterator[Measurement]:
    identifier = run_id or str(uuid.uuid4())
    for row in rows:
        yield Measurement(
            run_id=identifier,
            experiment=row.experiment,
            sequence=row.sequence,
            started_utc=row.started_utc,
            latency_ns=row.latency_ns,
            outcome=row.outcome,
            payload_bytes=row.payload_bytes,
            mcu_value=row.mcu_value,
            detail=row.detail,
        )


def roundtrip(
    bridge: BridgeClient,
    *,
    payload_size: int,
    iterations: int,
    warmup: int,
    timeout: float,
) -> Iterator[Measurement]:
    payload = payload_for_size(payload_size)
    rows = _measure_calls(
        bridge,
        experiment="rpc-roundtrip",
        method="qf_stage1_echo",
        arguments=lambda _sequence: (payload,),
        iterations=iterations,
        warmup=warmup,
        timeout=timeout,
        payload_bytes=len(payload.encode()),
        validate=lambda value, _sequence: value == payload,
    )
    return with_run_id(rows)


def clock_samples(
    bridge: BridgeClient, *, iterations: int, warmup: int, timeout: float
) -> Iterator[Measurement]:
    rows = _measure_calls(
        bridge,
        experiment="clock-sample",
        method="qf_stage1_micros",
        arguments=lambda _sequence: (),
        iterations=iterations,
        warmup=warmup,
        timeout=timeout,
        validate=lambda value, _sequence: isinstance(value, int),
    )
    return with_run_id(rows)


def matrix_updates(
    bridge: BridgeClient, *, iterations: int, warmup: int, timeout: float
) -> Iterator[Measurement]:
    rows = _measure_calls(
        bridge,
        experiment="matrix-update",
        method="qf_stage1_matrix_draw",
        arguments=lambda sequence: (sequence & 0xFFFFFFFF,),
        iterations=iterations,
        warmup=warmup,
        timeout=timeout,
        validate=lambda value, _sequence: isinstance(value, int) and value >= 0,
    )
    return with_run_id(rows)


def mcu_to_linux_roundtrips(
    bridge: BridgeClient, *, iterations: int, warmup: int, timeout: float
) -> Iterator[Measurement]:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if warmup < 0:
        raise ValueError("warmup cannot be negative")

    def linux_echo(token: int) -> int:
        return token

    def measurements() -> Iterator[Measurement]:
        bridge.provide("qf_stage1_linux_echo", linux_echo)
        try:
            for index in range(-warmup, iterations):
                token = index + warmup + 1
                started_utc = utc_now()
                started_ns = time.perf_counter_ns()
                try:
                    accepted = bridge.call("qf_stage1_reverse_start", token, timeout=timeout)
                    if accepted is not True:
                        raise RuntimeError(f"MCU rejected reverse token {token}")

                    deadline = time.monotonic() + timeout
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError(
                                f"MCU reverse result for token {token} timed out after {timeout}s"
                            )
                        duration_us = bridge.call(
                            "qf_stage1_reverse_result", token, timeout=remaining
                        )
                        if duration_us != -1:
                            break
                        time.sleep(min(0.001, remaining))

                    latency_ns = time.perf_counter_ns() - started_ns
                    valid = (
                        isinstance(duration_us, int)
                        and not isinstance(duration_us, bool)
                        and duration_us >= 0
                    )
                    outcome = "ok" if valid else "invalid-result"
                    detail = None if valid else repr(duration_us)
                    mcu_value = duration_us if valid else None
                except Exception as error:
                    latency_ns = time.perf_counter_ns() - started_ns
                    outcome = "error"
                    detail = f"{type(error).__name__}: {error}"
                    mcu_value = None

                if index >= 0:
                    yield Measurement(
                        run_id="",
                        experiment="mcu-linux-roundtrip",
                        sequence=index,
                        started_utc=started_utc,
                        latency_ns=latency_ns,
                        outcome=outcome,
                        mcu_value=mcu_value,
                        detail=detail,
                    )
        finally:
            bridge.unprovide("qf_stage1_linux_echo")

    return with_run_id(measurements())
