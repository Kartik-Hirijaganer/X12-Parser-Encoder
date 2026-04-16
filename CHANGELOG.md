# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- High-level convenience API: `from_csv`, `from_excel`, `build_270`, and
  `read_271`. Template-aware imports auto-correct dates, names, whitespace, and
  service-type defaults while surfacing short member IDs as user-confirmable
  warnings rather than silent corrections. `read_271` returns a structured
  `EligibilityResultSet` with per-subscriber `EligibilityResult` projections and
  an optional pandas `to_dataframe()` export.
- Library-native data contracts for agent-style pipelines: `PatientRecord`,
  `ImportResult`, `Correction`, `WarningMessage`, `RowError`,
  `EligibilityResult`, `EligibilitySegment`, `BenefitEntity`, and `AAAError` are
  now exported from `x12_edi_tools`.

## [0.1.0] - 2026-04-12

### Added

- Typed X12 270 and 271 parser, encoder, and validator library foundations.
- FastAPI application with upload, convert, generate, validate, parse, export, profile, health, and pipeline endpoints.
- React workbench with routed workflows, template downloads, settings persistence, and result pages.
- Phase 8 release automation, Prometheus metrics, correlation-aware observability, and public contributor and security documentation.
