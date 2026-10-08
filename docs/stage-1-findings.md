# Stage 1 preliminary findings

No timing contract is selected in this document. These results establish the initial natural
idle and CPU-loaded behavior of one Arduino UNO Q configuration and identify follow-up controls.

## Evidence

- Idle campaign: `initial-idle-04`, QFabric commit `13df00e`, three repetitions.
- Loaded campaign: `initial-cpu-load`, QFabric commit `dab7002`, three repetitions.
- Each condition contains 21,000 recorded samples with zero failures.
- Loaded profile: `stress-ng --cpu 4 --cpu-method all`, successful for 324.30 seconds.
- Raw and processed data are retained on the UNO Q and backed up under the matching local
  `data/` paths, which remain intentionally untracked.

The table reports the mean of each repetition's percentile. Times are end-to-end Linux-observed
RPC latency.

| Experiment | Bytes | Idle p50 ms | Loaded p50 ms | Idle p95 ms | Loaded p95 ms | Idle p99 ms | Loaded p99 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Clock sample | 0 | 8.38 | 6.94 | 8.94 | 10.33 | 9.14 | 12.42 |
| Matrix update | 0 | 8.82 | 7.95 | 9.57 | 11.87 | 10.10 | 12.95 |
| RPC echo | 0 | 7.52 | 6.48 | 8.99 | 10.09 | 10.58 | 11.82 |
| RPC echo | 1 | 7.92 | 6.49 | 8.94 | 10.23 | 9.24 | 11.96 |
| RPC echo | 8 | 9.77 | 7.89 | 10.43 | 11.61 | 10.66 | 13.03 |
| RPC echo | 32 | 14.44 | 13.34 | 15.43 | 16.87 | 15.85 | 18.69 |
| RPC echo | 128 | 32.95 | 31.99 | 33.86 | 35.98 | 34.67 | 37.14 |

## Observations

- CPU load reduced median latency by 2.9% to 19.2%, but increased p95 by 6.3% to 24.1% and
  p99 by 7.1% to 35.9%.
- The Linux CPU used the `schedutil` governor with a 300 MHz to 2.016 GHz range. The improved
  loaded median is therefore plausibly a frequency-scaling effect; this is an inference, not yet
  a causal conclusion. The degraded tails are consistent with added scheduling contention.
- The MCU-local median duration of `Arduino_LED_Matrix.draw()` was 7 microseconds in both
  conditions. Matrix RPC tail inflation is therefore outside the measured draw call itself.
- Idle sequential echo rate fell from about 130 calls/s at zero-byte payload to about 30 calls/s
  at 128 bytes.
- Payloads through 128 bytes completed cleanly. An initial 256-byte probe produced sustained
  timeouts and eventually required MCU firmware re-registration. Sizes at and above 256 bytes
  are isolated from baseline campaigns until a reset-safe boundary method is implemented.

## Required follow-up

- Repeat a controlled frequency-policy experiment to separate DVFS from scheduler contention.
- Implement reset-safe payload boundary probing above 128 bytes.
- Add MCU-to-Linux direction measurements and bounded clock offset/drift analysis.
- Measure LED enabled/disabled and refresh-rate profiles rather than only individual draw calls.
- Record MCU queue, memory, and utilization headroom before proposing contract thresholds.
