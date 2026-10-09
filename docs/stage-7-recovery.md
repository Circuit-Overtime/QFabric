# Stage 7 safe closed-loop recovery

Stage 7 is QFabric's core novelty stage. It turns a credible empirical timing-contract violation
and an admitted Stage 6 alternative into a boundary-safe trial, then commits only after verified
probation or rolls back with cooldown and temporary blacklisting.

The protocol remains an empirical soft real-time mechanism. It does not claim formal WCET or make
an unsafe task eligible merely because another domain appears faster.

## Recovery states

- `MONITORING`: observe the current placement; no recovery is armed.
- `WAITING_BOUNDARY`: a credible violation and eligible alternative exist, but switching waits for
  a declared safe boundary.
- `PROBATION`: the epoch changed and the alternate domain is being verified.
- `ROLLBACK_WAIT`: probation failed, but restoration waits for a declared safe boundary.
- `COOLDOWN`: a commit or rollback completed; new switches are suppressed.
- `INFEASIBLE`: safe alternatives are exhausted; automatic switching stops.

`UNKNOWN`, `SATISFIED`, `AT_RISK`, or invalid evidence cannot arm recovery. Only a valid Stage 5
`VIOLATED` source can do so. The alternate must differ from the current domain and pass semantic,
admission, predicted-feasibility, cooldown, and blacklist gates.

## Boundary and epoch invariants

Every switch and rollback action records `safe_boundary: true`. A domain change increments the
epoch exactly once, so a failed trial increments once on entry and once on restoration. Detection
may occur away from a boundary, but execution remains on the original domain in
`WAITING_BOUNDARY` until the trace declares a safe transition point.

If the violation clears, the recommendation changes, or a gate closes before that point, recovery
is cancelled without a domain or epoch change.

## Probation, commit, and rollback

Version 1 requires three consecutive target `SATISFIED` windows while every protected contract
remains healthy. Any non-satisfied target window resets the healthy streak. Target `VIOLATED` or
`INFEASIBLE`, a protected-contract regression, or probation timeout arms rollback.

Rollback occurs immediately only at a safe boundary; otherwise `ROLLBACK_WAIT` preserves the trial
placement until a safe restoration point. The failed destination is then blacklisted for five
windows and recovery cools down for three windows. Because the blacklist outlasts cooldown, the
same candidate cannot be retried immediately.

When the current placement is credibly violated and all safe alternatives are exhausted, the
controller enters `INFEASIBLE` and holds instead of oscillating.

## Deterministic trace replay

A recovery trace fixes the policy, initial placement and epoch, and one observation per contract
window. Each observation supplies source evidence, the static recommendation gates, boundary
availability, probation health, transient misses, and protected-contract health.

```bash
qf recover replay \
  --input data/raw/stage7/recovery-trace.json \
  --output data/processed/stage7/recovery-report.json
```

The report preserves every before/after state, action, domain, epoch, cooldown, and blacklist. It
also reports detection delay, time to verified recovery, transient misses, protected-contract
regressions, attempts, commits, rollbacks, rollback rate, successful recovery rate, domain changes,
and oscillations.

This initial replay implementation changes no live placement. Hardware actuation will be added
only after the protocol invariants and fault-injection traces pass the Stage 7 audit.

## Controlled fault-injection suite

Run the deterministic protocol evaluation with:

```bash
qf recover scenarios \
  --output data/processed/stage7/recovery-scenarios.json
```

The ten scenarios cover noisy or insufficient evidence, successful boundary-delayed recovery,
semantic and admission rejection, target failure, protected-contract regression with deferred
rollback, probation timeout, cooldown plus blacklist suppression, cancellation before a boundary,
and exhausted alternatives. Every injected trace is labelled
`controlled-fault-injection-not-hardware-performance`.

The suite requires complete recovery-state coverage, safe-boundary flags on every domain change,
epoch increments matching domain changes, deterministic replay, and zero false switches. Its
aggregate report includes detection-delay and verified-recovery samples, transient misses,
protected-contract regressions, attempts, commits, rollbacks, success and rollback rates, and
oscillation count.
