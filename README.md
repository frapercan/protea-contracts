# protea-contracts

Shared contract surface for the PROTEA stack. Holds the ABCs, payload
schemas, feature registry contract, and the `compute_schema_sha`
helper that downstream packages depend on.

| Package | Role | Depends on `protea-contracts`? |
|---------|------|---|
| `protea-core` | Platform: jobs, queues, ORM, FastAPI, UI host | yes |
| `protea-method` | Inferencia pura (KNN, feature compute, apply reranker) | yes |
| `protea-cafaeval` | CAFA evaluator standalone | no (independent) |
| `protea-sources` | Annotation source plugins (GOA, QuickGO, UniProt, future InterProScan) | yes |
| `protea-runners` | Experiment runner plugins (LightGBM, KNN baseline, future GNN) | yes |
| `protea-backends` | Embedding backend plugins (ESM, ProtT5, Ankh, ESM3-C) | yes |

## Hard constraints

- **Zero deps** to `sqlalchemy`, `fastapi`, `torch`, `protea-core`.
  This package must stay importable from any consumer without
  dragging the platform.
- **Public API is SemVer-ed**. Breaking changes bump major. The
  `compute_schema_sha` digest is a contract: bumping any field name,
  dtype, or enum value forces a major version bump and re-training
  of all downstream LightGBM boosters.

## Roadmap

This is the F0 bootstrap (T0.10 of the PROTEA master plan v3).
Full content lands in F1:

- T1.1 ABCs (`AnnotationSource`, `EmbeddingBackend`,
  `ExperimentRunner`, `FeatureRegistry`).
- T1.2 Feature schema central (`ALL_FEATURES`, `FEATURE_FAMILIES`,
  `EMBEDDING_PCA_DIM`, `compute_schema_sha`).
- T1.3 Pydantic payloads (`PredictGOTermsPayload`,
  `PredictGOTermsBatchPayload`, `RerankerSpec`, `ManifestV1`,
  `DatasetSpec`).
- T1.4 Tag `v0.1.0` + publish to a private index.

## Versioning

SemVer 2.0.0:

- **Major** (X.0.0): breaking change to any public ABC, payload, or
  to the schema sha output.
- **Minor** (0.X.0): new features (additional fields with defaults,
  new optional ABC methods, new enum values).
- **Patch** (0.0.X): bug fixes that do not change the contract.

Each release is tagged in git and published as a wheel to the
private index used by `protea-core`, `protea-method`, etc.

## Development

```bash
poetry install
poetry run pytest
poetry run ruff check .
poetry run mypy src tests
```
