# QFabric

QFabric investigates safe, closed-loop recovery of empirical timing contracts across Linux and RTOS execution domains on the Arduino UNO Q.

Development is organized by the tracking issues in the [GitHub issue tracker](https://github.com/Circuit-Overtime/QFabric/issues). The complete research plan is archived in [issue #13](https://github.com/Circuit-Overtime/QFabric/issues/13).

## Current stage

Stage 1 is complete. Its 136,800-sample evidence base, findings, recommendations, and documented
platform limitations are recorded in [the Stage 1 findings](docs/stage-1-findings.md).

Stage 2 proves that one logical QTask can execute through the same CLI on either a real Linux ARM64
artifact or the STM32/Zephyr RT domain, with explicit domain selection and no placement policy.
See [Stage 2 documentation](docs/stage-2.md) for build, deployment, and smoke-test commands.

## Local checks

The hardware-independent tests use only Python's standard library:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```
