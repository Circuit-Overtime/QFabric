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

Stage 5 is the current stage. It turns the measured timing evidence into deterministic empirical
soft real-time contract states and transitions.

## Local checks

The hardware-independent tests use only Python's standard library:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```
