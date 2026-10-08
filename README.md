# QFabric

QFabric investigates safe, closed-loop recovery of empirical timing contracts across Linux and RTOS execution domains on the Arduino UNO Q.

Development is organized by the tracking issues in the [GitHub issue tracker](https://github.com/Circuit-Overtime/QFabric/issues). The complete research plan is archived in [issue #13](https://github.com/Circuit-Overtime/QFabric/issues/13).

## Current stage

Stage 1 characterizes the UNO Q before contract thresholds or placement policy are implemented. It measures:

- Linux↔MCU Bridge round-trip latency;
- payload-size and sequential RPC-rate behavior;
- cross-domain clock samples without subtracting unsynchronized clocks;
- MCU execution and queueing diagnostics;
- LED matrix update overhead; and
- Linux behavior under controlled load.

See [Stage 1 documentation](docs/stage-1.md) for installation, checks, flashing, execution, and analysis commands.
The current idle-versus-loaded evidence and open measurement questions are recorded in
[Stage 1 preliminary findings](docs/stage-1-findings.md).

## Local checks

The hardware-independent tests use only Python's standard library:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```
