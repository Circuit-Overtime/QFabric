# Stage 6 static recommendation policy

Stage 6 recommends an execution domain from measured evidence. It is strictly advisory: generating
a recommendation never invokes a task, changes placement, deploys firmware, or mutates runtime
state.

## Policy boundary

The `gated-static-end-to-end-v1` policy compares Linux and RT using measured p95 end-to-end
latency. Local execution time is reported for explanation and MCU utilization, but it is never
substituted for the complete serialization, Bridge, queueing, and execution path.

Every candidate is evaluated against these hard gates:

1. both domains have the policy's minimum evidence, otherwise the recommendation is withheld;
2. a cross-domain transition is semantically eligible;
3. the destination admission controller allows the domain;
4. the Stage 5 contract state is `SATISFIED`;
5. observed miss rate does not exceed the contract;
6. predicted p95 including supported chain-boundary costs does not exceed the deadline;
7. a cross-domain move is outside cooldown; and
8. RT placement preserves the declared MCU headroom.

The current domain is always semantically eligible. A different domain is automatically eligible
only for a `Q_PURE` task; other effects require explicit transition hooks. Admission and cooldown
remain separate gates so their rejection reasons cannot be confused with semantic safety.

After the hard gates, the lowest predicted end-to-end latency wins. Equal predictions use a stable
domain-name ordering. Every admissible but slower alternative receives
`higher_predicted_end_to_end`; every hard-gate rejection retains its specific evidence and reason
code.

## Chain and capacity accounting

For a supported task chain, each adjacent task or data location declares its current domain and a
measured boundary cost. A candidate pays that cost when its domain differs from the neighbor:

```text
predicted_end_to_end = measured_candidate_p95 + charged_chain_boundaries
```

This makes a Linux-to-RT-to-Linux placement pay both supported boundaries and prevents an apparent
standalone saving from creating obvious domain ping-pong.

MCU utilization is predicted as:

```text
task_utilization_pct = rate_hz * mcu_local_execution_p95_ns / 1e9 * 100
projected_pct = utilization_without_task_pct + task_utilization_pct
usable_pct = 100 - reserved_headroom_pct
```

RT is rejected when projected utilization exceeds usable capacity. Reports always expose the base,
task, projected, reserved, and usable percentages.

## Interface and deterministic output

Evaluate every task in the input:

```bash
qf recommend \
  --input data/processed/stage6/recommendation-input.json \
  --output data/processed/stage6/recommendations.json
```

Evaluate exactly one named task, matching the required `qf recommend filter` form:

```bash
qf recommend filter \
  --input data/processed/stage6/recommendation-input.json \
  --output data/processed/stage6/filter-recommendation.json
```

Each record ID is the SHA-256 of canonical task, policy, and MCU-capacity input. There is no
timestamp in the decision record, so identical inputs produce byte-equivalent recommendations.
Every report carries `advisory_only: true`, `placement_changes: 0`, and
`placement_changed: false` for each task.

## Version 1 exclusions

Stage 6 does not change live placement, estimate formal WCET, invent missing boundary costs, or
infer transition hooks. Dynamic migration, canary execution, and automatic rollback belong to
later stages.
