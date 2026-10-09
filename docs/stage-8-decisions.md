# Stage 8 immutable decision history

Stage 8 makes QFabric recommendations and recovery actions inspectable from the exact evidence
used by the policy engine. Explanations and replay are derived from persisted decision records,
not reconstructed from mutable current state or free-form log text.

## Journal integrity model

Version 1 stores newline-delimited JSON in an append-only decision journal. Every record contains:

- a contiguous positive `decision_id`, used by `qf explain --decision` and `qf replay`;
- a UTC capture time, task, decision kind, and explicit policy name and version;
- the complete policy input required for deterministic replay;
- the exact policy outcome and structured explanation facts;
- the SHA-256 of the preceding record; and
- a SHA-256 over every field except the digest itself.

The first record links to a fixed all-zero genesis digest. Later records form a hash chain, so
editing, deleting, inserting, or reordering a line is detected when the journal is read. IDs are
assigned while holding an exclusive file lock, and each append is flushed and synchronized before
the lock is released. Readers validate the complete chain under a shared lock.

The journal is tamper-evident, not tamper-proof: an actor able to rewrite the entire file could
recompute every digest. Version 1 does not claim cryptographic identity, signatures, secure time,
or protection against rollback to an older valid journal. Those require an external trust anchor.

## Persistence semantics

Decision input, outcome, and facts are converted through canonical JSON before append, separating
the stored value from caller-owned mutable objects. Restarting the process opens and validates the
same journal, retains existing identifiers, and allocates the next contiguous ID. A malformed or
truncated tail is rejected rather than silently discarded.

The journal contains policy evidence and may grow without bound. Rotation, retention, access
control, redaction, and multi-host replication are outside the version 1 scope and must be defined
before recording sensitive or long-running deployments.
