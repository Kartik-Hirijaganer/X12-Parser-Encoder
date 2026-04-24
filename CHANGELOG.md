# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-04-24

### Changed

- Standardized API responses and generated OpenAPI fields on camelCase.
- Reworked custom-domain Terraform ownership so ACM validation happens before CloudFront alias DNS wiring.
- Tightened GitHub OIDC deploy permissions around named state, artifact, Lambda, SPA, CloudFront, ACM, WAF, and Route 53 resources.

### Fixed

- Restored the web production build by aligning dashboard card props with the Card primitive.
- Centralized FastAPI error envelopes for middleware, upload, validation, and HTTP exception paths.
- Completed reduced-motion handling for modal, drawer, toast, and skeleton primitives.
- Rendered dashboard zero-row filter results through the shared EmptyState component.

## [0.1.1] - 2026-04-21

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
