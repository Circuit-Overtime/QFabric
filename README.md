# QFabric

QFabric investigates safe, closed-loop recovery of empirical timing contracts across Linux and RTOS execution domains on the Arduino UNO Q.

Development is organized by the tracking issues in the [GitHub issue tracker](https://github.com/Circuit-Overtime/QFabric/issues). The complete research plan is archived in [issue #13](https://github.com/Circuit-Overtime/QFabric/issues/13).

## Current stage

Stage 1 is complete. Its 136,800-sample evidence base, findings, recommendations, and documented
platform limitations are recorded in [the Stage 1 findings](docs/stage-1-findings.md).

Stage 2 is complete. One logical QTask executes through the same CLI on either a real Linux ARM64
artifact or the STM32/Zephyr RT domain, with explicit domain selection and no placement policy.
The implementation and acceptance evidence are recorded in the
[Stage 2 findings](docs/stage-2-findings.md).

Stage 3 is complete. It defines the versioned cross-domain ABI, generated serialization, replay
protection, defensive decoding, and effect classes. The implementation and hardware audit are
recorded in the [Stage 3 findings](docs/stage-3-findings.md).

Stage 4 is complete. It provides correlated end-to-end QTask profiling, strict cross-clock
measurement semantics, bounded sample windows, independently verified aggregates, and measured
instrumentation overhead. The implementation and hardware audit are recorded in the
[Stage 4 findings](docs/stage-4-findings.md).

Stage 5 is complete. It turns measured timing evidence into deterministic empirical soft
real-time contract states and transitions. The semantics and hardware evidence are recorded in
the [Stage 5 specification](docs/stage-5-contracts.md) and
[Stage 5 findings](docs/stage-5-findings.md).

Stage 6 is complete. It provides gated, explainable, deterministic recommendations over measured
end-to-end evidence without changing live placement. The policy and audit evidence are recorded in
the [Stage 6 specification](docs/stage-6-recommendations.md) and
[Stage 6 findings](docs/stage-6-findings.md).

Stage 7 is complete. It provides safe closed-loop recovery from credible empirical timing-contract
violations, including gated actuation, zero-inflight boundaries, epoch-controlled transitions,
probation, commit, rollback, cooldown, and candidate blacklisting. The protocol, hardware evidence,
claim boundary, and independent audit are recorded in the
[Stage 7 specification](docs/stage-7-recovery.md) and
[Stage 7 findings](docs/stage-7-findings.md).

Stage 8 is complete. It provides hash-chained immutable decision history, restart-safe persistence,
faithful human and JSON explanations, stable identifiers, and exact versioned replay for Stage 6
recommendations and Stage 7 recovery actions. The schema, evidence, audit, and trust limitations
are recorded in the [Stage 8 specification](docs/stage-8-decisions.md) and
[Stage 8 findings](docs/stage-8-findings.md).

Stage 9 is the current stage. It builds the LED matrix and RGB physical observability interface
tracked in [issue #10](https://github.com/Circuit-Overtime/QFabric/issues/10), driven only by real
QFabric telemetry and stable decision identifiers.

## Local checks

The hardware-independent tests use only Python's standard library:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```
