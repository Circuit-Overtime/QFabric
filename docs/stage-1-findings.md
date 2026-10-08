# Stage 1 preliminary findings

No timing contract is selected in this document. These results establish the initial natural
idle and CPU-loaded behavior of one Arduino UNO Q configuration and identify follow-up controls.

## Evidence

- Idle campaign: `stage1b-directional-idle`, QFabric commit `c246e8d`, three repetitions.
- Loaded campaign: `stage1b-directional-cpu-loaded`, the same commit, three repetitions.
- Each condition contains 24,000 recorded samples with zero failures, including 3,000
  MCU-initiated round trips.
- Loaded profile: `stress-ng --cpu 4 --cpu-method all`, successful for 414.70 seconds.
- Raw and processed data are retained on the UNO Q and backed up under the matching local
  `data/` paths, which remain intentionally untracked.

The table reports the mean of each repetition's percentile. Times are end-to-end Linux-observed
RPC latency.

| Experiment | Bytes | Idle p50 ms | Loaded p50 ms | Idle p95 ms | Loaded p95 ms | Idle p99 ms | Loaded p99 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Clock sample | 0 | 8.34 | 7.18 | 8.89 | 10.86 | 9.11 | 12.57 |
| Matrix update | 0 | 8.80 | 7.98 | 9.60 | 11.86 | 9.96 | 12.97 |
| Reverse orchestration | 0 | 23.60 | 27.03 | 32.64 | 33.16 | 33.47 | 35.34 |
| RPC echo | 0 | 7.74 | 6.49 | 8.85 | 10.11 | 9.11 | 11.80 |
| RPC echo | 1 | 8.06 | 6.50 | 8.99 | 10.42 | 9.26 | 12.00 |
| RPC echo | 8 | 9.81 | 7.84 | 10.46 | 11.68 | 10.66 | 13.08 |
| RPC echo | 32 | 14.45 | 13.47 | 15.43 | 17.04 | 15.89 | 19.10 |
| RPC echo | 128 | 32.93 | 32.10 | 34.04 | 35.90 | 34.82 | 37.15 |

The reverse-path primary metric is a complete MCU-clocked MCU→Linux→MCU round trip. It is
not a one-way latency estimate. As above, each entry is the mean of the three repetition-level
statistics.

| Condition | MCU p50 ms | MCU p95 ms | MCU p99 ms | MCU mean ms |
|---|---:|---:|---:|---:|
| Idle | 9.23 | 12.79 | 12.95 | 10.07 |
| CPU-loaded | 10.55 | 13.58 | 15.80 | 9.60 |
| Loaded change | +14.2% | +6.2% | +22.0% | -4.6% |

## Observations

- For Linux-initiated calls, CPU load reduced median latency by 2.5% to 20.1%, but increased
  p95 by 5.5% to 23.5% and p99 by 6.7% to 37.9%.
- The Linux CPU used the `schedutil` governor with a 300 MHz to 2.016 GHz range. The improved
  loaded median is therefore plausibly a frequency-scaling effect; this is an inference, not yet
  a causal conclusion. The degraded tails are consistent with added scheduling contention.
- The MCU-local median duration of `Arduino_LED_Matrix.draw()` was 7 microseconds in both
  conditions. Matrix RPC tail inflation is therefore outside the measured draw call itself.
- The reverse-path result was stable between repetitions: idle p50 varied from 9.225 to
  9.242 milliseconds and loaded p50 from 10.540 to 10.556 milliseconds. CPU load increased
  the MCU-clocked p50, p95, and p99, while reducing the mean. This is not contradictory: the
  loaded distribution shifted into distinct fast and slow regions, with samples below 8 ms
  rising from 6.1–11.9% at idle to 34.5–37.3% under load. A single mean would conceal that shape.
- Linux reverse orchestration time is diagnostic rather than the primary reverse metric. Its
  loaded p50, p95, and p99 increased by 14.6%, 1.6%, and 5.6%, respectively.
- Idle sequential echo rate fell from about 129 calls/s at zero-byte payload to about 30 calls/s
  at 128 bytes.
- Payloads through 128 bytes completed cleanly. An initial 256-byte probe produced sustained
  timeouts and eventually required MCU firmware re-registration. Sizes at and above 256 bytes
  are isolated from baseline campaigns until a reset-safe boundary method is implemented.

## Required follow-up

- Repeat a controlled frequency-policy experiment to separate DVFS from scheduler contention.
- Implement reset-safe payload boundary probing above 128 bytes.
- Explain the loaded reverse-path distribution with controlled CPU-frequency policy and Router
  or scheduler tracing; do not derive a contract threshold from its mean alone.
- Add bounded clock offset/drift analysis before attempting any one-way latency estimate.
- Measure LED enabled/disabled and refresh-rate profiles rather than only individual draw calls.
- Record MCU queue, memory, and utilization headroom before proposing contract thresholds.
