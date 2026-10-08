# Stage 1 preliminary findings

No timing contract is selected in this document. These results establish the initial natural
idle and CPU-loaded behavior of one Arduino UNO Q configuration and identify follow-up controls.

## Evidence

- Idle campaign: `stage1b-directional-idle`, QFabric commit `c246e8d`, three repetitions.
- Loaded campaign: `stage1b-directional-cpu-loaded`, the same commit, three repetitions.
- Performance-governor campaigns: `stage1-performance-idle` and
  `stage1-performance-cpu-loaded`, QFabric commit `1cef3ad`, three repetitions each. The
  benchmark and MCU probe were unchanged from `c246e8d`; the later commit added the safe
  governor wrapper.
- Each of the four conditions contains 24,000 recorded samples with zero failures, including
  3,000 MCU-initiated round trips: 96,000 samples in total.
- Loaded profile: `stress-ng --cpu 4 --cpu-method all`, successful for 414.70 seconds.
- The performance-governor loaded profile used the same four workers and completed successfully
  in 427.07 seconds. Both performance campaign captures reported a 2.016 GHz current frequency,
  and the wrapper restored `schedutil` afterward.
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

The corresponding performance-governor measurements are below. They use the same aggregation
rule and units.

| Experiment | Bytes | Idle p50 ms | Loaded p50 ms | Idle p95 ms | Loaded p95 ms | Idle p99 ms | Loaded p99 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Clock sample | 0 | 7.56 | 7.56 | 8.45 | 11.00 | 8.78 | 12.93 |
| Matrix update | 0 | 8.06 | 7.97 | 9.38 | 11.53 | 9.61 | 12.66 |
| Reverse orchestration | 0 | 22.12 | 27.96 | 30.80 | 33.82 | 31.62 | 35.64 |
| RPC echo | 0 | 7.29 | 6.55 | 7.89 | 10.53 | 8.14 | 12.10 |
| RPC echo | 1 | 7.51 | 7.47 | 7.99 | 11.42 | 8.29 | 12.81 |
| RPC echo | 8 | 8.98 | 8.88 | 9.58 | 12.91 | 9.92 | 14.33 |
| RPC echo | 32 | 14.27 | 13.56 | 14.94 | 17.48 | 15.11 | 19.01 |
| RPC echo | 128 | 32.53 | 32.23 | 33.60 | 35.84 | 33.98 | 37.60 |

The reverse-path primary metric is a complete MCU-clocked MCU→Linux→MCU round trip. It is
not a one-way latency estimate. As above, each entry is the mean of the three repetition-level
statistics.

| Governor and condition | MCU p50 ms | MCU p95 ms | MCU p99 ms | MCU mean ms |
|---|---:|---:|---:|---:|
| `schedutil`, idle | 9.23 | 12.79 | 12.95 | 10.07 |
| `schedutil`, CPU-loaded | 10.55 | 13.58 | 15.80 | 9.60 |
| `schedutil` loaded change | +14.2% | +6.2% | +22.0% | -4.6% |
| `performance`, idle | 8.14 | 11.89 | 11.96 | 9.34 |
| `performance`, CPU-loaded | 10.57 | 14.29 | 16.17 | 9.76 |
| `performance` loaded change | +29.9% | +20.2% | +35.2% | +4.5% |

## Observations

- Under `schedutil`, CPU load reduced Linux-initiated median latency by 2.5% to 20.1%, but
  increased p95 by 5.5% to 23.5% and p99 by 6.7% to 37.9%.
- With `schedutil`, improved loaded medians were partly confounded by frequency scaling. Under
  the `performance` governor, load changed Linux-initiated payload medians by -10.1% to -0.5%,
  while increasing p95 by 6.7% to 42.9% and p99 by 10.7% to 54.6%. Frequency policy therefore
  does not explain the tail degradation; scheduling or Router contention remains the leading
  interpretation, not yet a causal attribution.
- The MCU-local median duration of `Arduino_LED_Matrix.draw()` was 7 microseconds in both
  conditions. Matrix RPC tail inflation is therefore outside the measured draw call itself.
- The reverse-path result was stable between repetitions: idle p50 varied from 9.225 to
  9.242 milliseconds and loaded p50 from 10.540 to 10.556 milliseconds. CPU load increased
  the MCU-clocked p50, p95, and p99, while reducing the mean. This is not contradictory: the
  loaded distribution shifted into distinct fast and slow regions, with samples below 8 ms
  rising from 6.1–11.9% at idle to 34.5–37.3% under load. A single mean would conceal that shape.
- Linux reverse orchestration time is diagnostic rather than the primary reverse metric. Its
  loaded p50, p95, and p99 increased by 14.6%, 1.6%, and 5.6%, respectively.
- At idle, `performance` reduced the MCU-clocked reverse p50 by 11.9% and p99 by 7.6% relative
  to `schedutil`. Under CPU load, changing from `schedutil` to `performance` changed reverse p50
  by only +0.2% and p99 by +2.4%. The fixed-policy load penalty and bimodal shape therefore
  persisted: 31.5–36.7% of loaded samples were below 8 ms, while 43.9–50.2% were between 10 and
  12 ms.
- The environment capture sampled 2.016 GHz at the beginning of both `performance` campaigns,
  but did not continuously record frequency residency. The result controls governor policy, not
  a separately verified per-sample clock frequency.
- Idle sequential echo rate fell from about 129 calls/s at zero-byte payload to about 30 calls/s
  at 128 bytes.
- Payloads through 128 bytes completed cleanly. An initial 256-byte probe produced sustained
  timeouts and eventually required MCU firmware re-registration. Sizes at and above 256 bytes
  are isolated from baseline campaigns until a reset-safe boundary method is implemented.

## Required follow-up

- Implement reset-safe payload boundary probing above 128 bytes.
- Explain the loaded reverse-path distribution with Router or scheduler tracing and continuous
  frequency telemetry; do not derive a contract threshold from its mean alone.
- Add bounded clock offset/drift analysis before attempting any one-way latency estimate.
- Measure LED enabled/disabled and refresh-rate profiles rather than only individual draw calls.
- Record MCU queue, memory, and utilization headroom before proposing contract thresholds.
