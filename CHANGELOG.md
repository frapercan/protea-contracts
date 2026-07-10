# Changelog

All notable changes to `protea-contracts` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Because every consumer in the PROTEA stack pins this package, breaking changes
(removed or renamed exports, payload field changes, ABC signature changes, or a
moved `compute_schema_sha` / `axis_tuple_shortid` digest) require a major bump.

## [1.3.0]

### Added

- `feature_docs` module: the single source of truth for what each canonical
  feature column measures, how it is computed in words, who produces it, and
  whether a producer runs in the default export. Exposes the frozen
  `FeatureDoc` dataclass, the `FeatureStatus` enum (`PRODUCED`,
  `DECLARED_ABSENT`, `POOL_INJECTED`, `BROKEN`) and the
  `FEATURE_DOCS` mapping with one entry per column in `ALL_FEATURES` (71
  entries). The six LAFA columns (`classifier_*`, `self_prior_score`,
  `association_*`) are recorded as `DECLARED_ABSENT` per ADR-D45: their
  producers exist but no producer runs in the default export, so it emits
  `NaN`.
- `scripts/check_feature_docs.py` drift lint (also asserted in
  `tests/test_feature_docs.py`): fails if a declared feature lacks a
  `FeatureDoc`, if a doc names an undeclared column, or if a doc's family
  disagrees with `FEATURE_FAMILIES`. Wired into the `ci` workflow.
- Sphinx reference page `reference/feature_docs` rendered at build time from
  `FEATURE_DOCS` via a `feature-docs-table` directive, so the docs cannot
  drift from the registry.

This release is additive: no export was removed or renamed, no payload or ABC
signature changed, and the `ALL_FEATURES` fingerprint is unchanged
(`8cc4cabded9b`). `__all__` remains a superset of the previous surface.

## [1.1.0]

### Added

- `interpro` feature family in `feature_schema`: `interpro_hit`,
  `interpro_score`, `interpro_n_signatures`, the member-DB one-hots
  (`interpro_db_pfam`, `interpro_db_panther`, `interpro_db_superfamily`,
  `interpro_db_smart`, `interpro_db_cdd`, `interpro_db_prosite`) and the
  per-source presence flags (`knn_present`, `interpro_present`). The columns
  join `ALL_FEATURES` (numeric block) and a new `interpro` entry in
  `FEATURE_FAMILIES` so the export producer and reranker lab can reference the
  InterPro signature-to-GO mapping features. The `ALL_FEATURES` golden digest
  moves from `a0986dedd912` to `8d9a1668b1a2`.

## [Unreleased]

### Added

- Quickstart guide for plugin authors in the Sphinx docs.
- API reference page and concepts section for the `axis_tuple` module
  (`CANONICAL_AXIS_KEYS`, `axis_tuple_shortid`), previously undocumented.
- `docs.yml` CI workflow that builds the docs with warnings-as-errors and
  publishes them to GitHub Pages from `develop`.
- This changelog.

### Changed

- Internal refactor (behaviour-preserving, public surface unchanged): the
  shared `sha256(...)[:12]` short-digest formula now lives in a single private
  `_hashing.short_sha` helper used by `axis_tuple_shortid`,
  `compute_schema_sha`, `compute_feature_schema_sha` and `DatasetSpec.hash`.
  The duplicated non-empty-string field validators in `payloads.py` collapse
  into one helper.
- Reworked the docs toctree into a narrative (getting started, the contract
  model, API reference, development) and refreshed README badges, hosted-docs
  link, and version references to the 1.x line.

## [1.0.1] - 2026-06-07

### Fixed

- Restored the `axis_tuple` module (`CANONICAL_AXIS_KEYS`,
  `axis_tuple_shortid`) that the 1.0.0 bump dropped from the public surface,
  which had broken consumers that join on the axis-tuple shortid.

## [1.0.0] - 2026-06-07

### Added

- Pool-context feature families (`plm_context`, `k_neighborhood`) and the
  matching `plm_id` / `k_context` columns in `ALL_FEATURES`.

## [0.3.0] - 2026-05-12

### Added

- Streaming record and payload types for the UniProt and QuickGO sources.

## [0.2.0] - 2026-05-08

### Added

- Embedding payload contract (`EmbeddingPayload`) with mean-pool and
  per-residue granularities.

## [0.1.0] - 2026-05-05

### Added

- Initial contract surface: the four plugin ABCs, the canonical feature
  schema with `compute_schema_sha`, the prediction payloads, the dataset
  manifest, and the pure-function bio utilities.

[Unreleased]: https://github.com/frapercan/protea-contracts/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/frapercan/protea-contracts/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/frapercan/protea-contracts/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/frapercan/protea-contracts/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/frapercan/protea-contracts/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/frapercan/protea-contracts/releases/tag/v0.1.0
