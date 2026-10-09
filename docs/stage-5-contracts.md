# Stage 5 empirical deadline contracts

Stage 5 evaluates one first-paper contract: whether observed QTask end-to-end latency stays within
a relative deadline and an allowed miss rate. It is an **empirical soft real-time contract**, not
a formal WCET guarantee.

## Contract parameters

The version 1 policy fixes all behavior that could otherwise make a result ambiguous:

- `deadline_ns`: inclusive end-to-end boundary; latency equal to the deadline is a hit;
- `window_size`: number of post-warm-up observations in each non-overlapping window;
- `minimum_samples`: minimum evidence required before leaving `UNKNOWN`;
- `warmup_samples`: observations excluded before the first window;
- `max_miss_rate_pct`: a window above this threshold is violating;
- `at_risk_miss_rate_pct`: a window above this threshold is risky;
- `recovery_miss_rate_pct`: maximum miss rate that advances recovery hysteresis;
- `violation_windows`: consecutive violating windows required for `VIOLATED`;
- `recovery_windows`: consecutive recovery-quality windows required to leave a degraded state; and
- `infeasible_windows`: consecutive 100%-miss windows required for `INFEASIBLE`.

Thresholds obey:

```text
0 <= recovery <= at-risk <= maximum < 100
```

The evaluator changes state only at a complete-window boundary. Its maximum sustained-violation
detection bound is therefore:

```text
warmup_samples + violation_windows * window_size observations
```

## Observation and missing-data semantics

An `ok` observation supplies Linux end-to-end latency in nanoseconds. The deadline comparison is
inclusive: `latency_ns <= deadline_ns` is a hit. `error`, `timeout`, and `missing` observations do
not carry a latency and conservatively count as deadline misses. They remain visible as missing
timing samples in every evidence record.

Warm-up observations never count as evidence or affect streaks. An incomplete trailing window is
reported as pending and cannot change the state. Windows are non-overlapping, so replaying a trace
always gives the same boundaries and transitions.

## State machine

`UNKNOWN` is mandatory until sufficient evidence reaches a complete evaluation boundary.

| Current state | Window evidence | Next state |
| --- | --- | --- |
| `UNKNOWN` or `SATISFIED` | healthy | `SATISFIED` |
| `UNKNOWN` or `SATISFIED` | risky or first violating window | `AT_RISK` |
| `AT_RISK` | fewer than the required consecutive violating windows | `AT_RISK` |
| any non-infeasible state | required consecutive violating windows | `VIOLATED` |
| any state | required consecutive 100%-miss windows | `INFEASIBLE` |
| `AT_RISK`, `VIOLATED`, or `INFEASIBLE` | required consecutive recovery-quality windows | `SATISFIED` |

A window that does not meet the recovery threshold resets the recovery streak. A non-violating
window resets the violation streak. Any window below 100% misses resets the infeasible streak.
`INFEASIBLE` is therefore an evidence-backed empirical state and remains recoverable if later
conditions change; it is not a proof that the task can never satisfy the contract.

Each evaluated window reports sample and miss counts, missing timing count, observed miss rate,
the state transition, all hysteresis streaks, cumulative evidence, and a Wilson-score 95% interval
for the miss rate. State decisions use the declared observed-rate thresholds; confidence bounds
are reported rather than silently substituted into the policy.

## Deterministic trace replay

A trace is canonical JSON with schema version 1:

```json
{
  "schema_version": 1,
  "contract": {
    "deadline_ns": 500000,
    "window_size": 1000,
    "minimum_samples": 20,
    "warmup_samples": 10,
    "max_miss_rate_pct": 1.0,
    "at_risk_miss_rate_pct": 0.5,
    "recovery_miss_rate_pct": 0.25,
    "violation_windows": 3,
    "recovery_windows": 3,
    "infeasible_windows": 5
  },
  "observations": [
    {"outcome": "ok", "latency_ns": 420000},
    {"outcome": "timeout", "latency_ns": null}
  ]
}
```

Replay it with:

```bash
qf contract replay \
  --input data/raw/stage5/trace.json \
  --output data/processed/stage5/contract-report.json
```

The report records the `empirical-soft-real-time` claim type and the
`count-as-deadline-miss` missing-sample policy alongside every transition.

## Convert measured profiles

Convert exactly one task/domain/instrumentation group from a Stage 4 report into a canonical
contract trace:

```bash
qf contract trace \
  --profile data/processed/stage4/profile-overhead.json \
  --task add \
  --domain rt \
  --mode full \
  --deadline-us 12000 \
  --window-size 50 \
  --minimum-samples 20 \
  --warmup-samples 0 \
  --output data/raw/stage5/rt-full-trace.json
```

The converter requires an unambiguous group selection and preserves `ok`, `error`, and `timeout`
outcomes. A successful sample without an end-to-end duration becomes an explicit `missing`
observation. Trace provenance states that the source profile's warm-up was already excluded;
`warmup-samples` is an optional additional Stage 5 exclusion applied to the retained trace.

## Sensitivity analysis

Evaluate a Cartesian product of window sizes and violation/recovery hysteresis settings against
the exact same observations:

```bash
qf contract sensitivity \
  --input data/raw/stage5/rt-full-trace.json \
  --window-sizes 20,50,100 \
  --violation-windows 1,2,3 \
  --recovery-windows 1,2,3 \
  --output data/processed/stage5/rt-full-sensitivity.json
```

Every configuration reports its final state, transition count, incomplete trailing observations,
first entry into each state in both window and absolute-observation units, and the theoretical
sustained-violation detection bound. Candidate windows smaller than the declared minimum evidence
are rejected rather than silently changing the contract.

P99 and jitter contracts are intentionally deferred until this deadline/miss-rate contract has
hardware trace and sensitivity evidence.
