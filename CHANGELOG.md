# Changelog

All notable changes to QFabric are documented in this file. The project follows
Semantic Versioning while the public API remains in initial development.

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

[0.1.0]: https://github.com/Circuit-Overtime/QFabric/releases/tag/v0.1.0
