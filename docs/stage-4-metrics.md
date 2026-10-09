# Stage 4 profiling schema

Stage 4 profile reports use schema version 1. Each sample is identified by the ABI epoch and a
unique 64-bit invocation ID. Reports group measurements by task and actual execution domain.

## Clock discipline

End-to-end latency is always the difference between two Linux monotonic timestamps around one
invocation. Linux-local execution is a Linux monotonic duration. MCU execution and MCU-local
queueing are durations measured entirely by the MCU clock. QFabric never subtracts an MCU
timestamp from a Linux timestamp.

Communication and queueing fields are duration components with an explicit estimator source. A
component remains absent until its estimator is valid; absence is not represented as zero.

## Measurement window

Every task/domain group exposes:

- total invocation count;
- required and observed warm-up samples;
- retained-window capacity and sample count;
- dropped samples caused by bounded-window eviction;
- the minimum sample requirement;
- estimator validity and an invalidity reason; and
- evaluated deadlines, misses, and met percentage.

Cold-start output reports `warmup-incomplete`. After warm-up but before the minimum sample count it
reports `insufficient-samples`.

## Metrics

End-to-end latency, local execution, communication, queueing, and consecutive-latency jitter use
the same stable summary: count, minimum, mean, p50, p95, p99, maximum, and population standard
deviation, all in nanoseconds.

Instrumentation has three explicit modes:

- `disabled`: execute without collecting timing samples;
- `reduced`: collect correlation and Linux end-to-end timing only; and
- `full`: also collect available local execution, communication, queueing, and deadline data.

The machine-readable report is canonical JSON. `qf status` will render the same persisted report
for humans without recomputing its metrics.
