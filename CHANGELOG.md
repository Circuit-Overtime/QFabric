# Changelog

All notable changes to QFabric are documented in this file. The project follows
Semantic Versioning.

## [1.0.0] - 2026-10-09

### Stable release

- Declared the `qf` command-line interface, QTask ABI version 1, report schemas,
  and contract/recovery state semantics as the first stable compatibility
  baseline.
- Promoted the package from alpha to production/stable status after the complete
  staged audit, research evaluation, TestPyPI installation test, and public
  `0.1.0` release validation.
- Preserved the `qf-stage1` command as a compatibility entry point for the
  Stage 1 measurement tooling.
- Reissued the reproducible research bundle under the stable version, including
  the paper, Stage 11 evaluation, package distributions, manifest, and checksums.

### Compatibility policy

- Backward-incompatible changes to the stable CLI, QTask ABI, or persisted
  report schemas require a new major release.
- New backward-compatible functionality may be introduced in minor releases;
  fixes that preserve the public surface may be introduced in patch releases.
- The empirical and hardware limitations documented for `0.1.0` remain in
  force; stability is an interface and artifact guarantee, not a hard real-time
  certification.

## [0.1.0] - 2026-10-09

### Added

- Versioned, bounded cross-domain QTask ABI with generated C++ serialization.
- Native Linux/AArch64 and Arduino UNO Q STM32/Zephyr execution paths.
- Correlated empirical timing profiles and soft real-time contract monitoring.
- Explainable placement recommendations with semantic and RT admission gates.
- Zero-inflight, epoch-controlled recovery with probation, commit, and rollback.
- Hash-chained decision history, deterministic replay, and physical LED telemetry.
- Optional Linux `perf` attribution with a userspace-only fallback.
- Four-application, seven-baseline Stage 11 evaluation and independent audit.
- IEEE-style research manuscript and reproducible table and figure generation.

### Known limitations

- Evidence is from one Arduino UNO Q and one concrete QTask implementation.
- Application-graph comparisons use deterministic replay of measured traces.
- Claims are empirical soft real-time claims, not hard real-time guarantees.
- Hardware control commands require the matching repository firmware and board.

[1.0.0]: https://github.com/Circuit-Overtime/QFabric/releases/tag/v1.0.0
[0.1.0]: https://github.com/Circuit-Overtime/QFabric/releases/tag/v0.1.0
