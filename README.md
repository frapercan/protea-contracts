# protea-contracts

**Shared contract surface for the [PROTEA](https://github.com/frapercan/PROTEA) stack.**
ABCs that plugin repos implement, pydantic payloads that cross queue and HTTP boundaries,
the canonical feature schema with its load-bearing `compute_schema_sha` fingerprint,
and pure-function bio utilities that every consumer can import without dragging the
platform.

[![Lint](https://github.com/frapercan/protea-contracts/actions/workflows/lint.yml/badge.svg)](https://github.com/frapercan/protea-contracts/actions/workflows/lint.yml)
[![Tests](https://github.com/frapercan/protea-contracts/actions/workflows/test.yml/badge.svg)](https://github.com/frapercan/protea-contracts/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/frapercan/protea-contracts/branch/develop/graph/badge.svg)](https://codecov.io/gh/frapercan/protea-contracts)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

**Status:** v0.3.0, production (foundational). Every active repo in the PROTEA stack
imports this package. SemVer-disciplined: any change to a payload field name, dtype,
or `ALL_FEATURES` ordering is a breaking change that requires a major version bump
and a coordinated upgrade across every downstream consumer.

---

<!-- protea-stack:start -->

## Repositories in the PROTEA stack

Single source of truth: [`docs/source/_data/stack.yaml`](https://github.com/frapercan/PROTEA/blob/develop/docs/source/_data/stack.yaml) in PROTEA. Run `python scripts/sync_stack.py` to regenerate this block.

| Repo | Role | Status | Summary |
|------|------|--------|---------|
| [PROTEA](https://github.com/frapercan/PROTEA) | Platform | `active` | Backend platform. Hosts the ORM, job queue, FastAPI surface, frontend, and orchestration. |
| **protea-contracts** (this repo) | Contracts | `active` | Shared contract surface. ABCs, pydantic payloads, feature schema, schema_sha. Imported by every other repo. |
| [protea-method](https://github.com/frapercan/protea-method) | Inference | `active` | Pure inference path (KNN, feature compute, reranker apply). Delegation target for the F2C extraction; live in production since F2C.5b. Bind-mounted by the LAFA containers. |
| [protea-sources](https://github.com/frapercan/protea-sources) | Source plugin | `active` | Annotation source plugins (GOA, QuickGO, UniProt). Discovered via Python entry_points (goa, quickgo, uniprot). |
| [protea-runners](https://github.com/frapercan/protea-runners) | Runner plugin | `active` | Experiment runner plugins (LightGBM, KNN, baseline). Discovered via Python entry_points (lightgbm, knn, baseline). |
| [protea-backends](https://github.com/frapercan/protea-backends) | Backend plugin | `active` | Protein language model embedding backends (ESM family, T5/ProstT5, Ankh, ESM3-C). Discovered via Python entry_points (esm, t5, ankh, esm3c). |
| [protea-reranker-lab](https://github.com/frapercan/protea-reranker-lab) | Lab | `active` | LightGBM reranker training lab. Pulls datasets from PROTEA, trains boosters, publishes them back via /reranker-models/import-by-reference. |
| [cafaeval-protea](https://github.com/frapercan/cafaeval-protea) | Evaluator | `active` | Standalone fork of cafaeval (CAFA-evaluator-PK) with the PK-coverage fix and a bit-exact parity guarantee against the upstream. |

<!-- protea-stack:end -->

---

## What is protea-contracts?

`protea-contracts` is the single source of truth for every interface that crosses a
package boundary in the PROTEA stack. It defines:

- **Four plugin ABCs** (`AnnotationSource`, `EmbeddingBackend`, `ExperimentRunner`,
  `FeatureRegistry`) that plugin packages subclass and register via Python
  `entry_points`. PROTEA discovers them at runtime without knowing their module paths.
- **Pydantic payloads and records** that validate the body of HTTP requests and
  RabbitMQ queue messages. All are `frozen=True, strict=True, extra="forbid"`.
  Typos and missing required fields fail at construction, not silently at consumption.
- **The canonical feature schema** (`ALL_FEATURES`, `FEATURE_FAMILIES`,
  `compute_schema_sha`). The digest gates whether a LightGBM booster trained
  yesterday is compatible with today's live inference pipeline. PROTEA persists the
  digest on every `RerankerModel` row and refuses to load a booster whose digest has
  drifted.
- **Bio utilities** (`parse_isoform`, `compute_sequence_hash`) used by PROTEA ORM
  models and source plugins, with no network calls or side effects.

## Why a separate package?

Three reasons drove the split (ADR D1):

1. **Plugin extensibility.** New annotation sources, embedding backends and experiment
   runners must be addable as out-of-tree contributions. Without a stable contract
   package each plugin would re-import private symbols from `protea-core`, recreating
   the monolith.

2. **Reproducibility.** The `compute_schema_sha` fingerprint must be a single source
   of truth across the platform, the lab, and the inference layer. Past silent drift
   between two parallel definitions cost one non-reproducible study run
   (ADR D10, 2026-05-01).

3. **Inference shipping.** `protea-method`, the pure inference path, can be
   PyPI-published without the platform stack precisely because every contract it
   touches lives here.

## Place in the stack

```
protea-contracts  (this repo)
      |
      |-- imported by --+--> protea-sources    (annotation source plugins)
                        +--> protea-backends   (PLM embedding backends)
                        +--> protea-runners    (experiment runner plugins)
                        +--> PROTEA            (platform core: ORM, queues, API)
                        +--> protea-method     (pure inference layer, LAFA)
                        +--> protea-reranker-lab (LightGBM training lab)
```

Zero runtime deps on `sqlalchemy`, `fastapi`, `torch`, or `protea-core`. Any
consumer can install this package without dragging the platform stack.

Full architecture documentation: [`docs/source/`](docs/source/) (build with
`poetry install --with docs && cd docs && make html`).

---

## Install

```bash
pip install protea-contracts
```

Verify the install and print the current feature schema fingerprint:

```bash
python -c "from protea_contracts import ALL_FEATURES, compute_schema_sha; print(compute_schema_sha(ALL_FEATURES))"
```

---

## Quick example

```python
from protea_contracts import (
    AnnotationSource, EmbeddingBackend, ExperimentRunner,
    GoaAnnotationRecord, GoaStreamPayload,
    parse_isoform, compute_sequence_hash,
    compute_schema_sha, ALL_FEATURES,
)

# 1. Build a typed payload: typos fail at construction, not at runtime.
payload = GoaStreamPayload(gaf_url="https://example.com/x.gaf.gz")

# 2. Build a frozen record: validates field shape + types at construction.
record = GoaAnnotationRecord(accession="P12345", go_id="GO:0008150")

# 3. Bio utilities: no ORM needed.
canonical, is_canonical, idx = parse_isoform("P12345-2")
# -> ("P12345", False, 2)

seq_hash = compute_sequence_hash("MKTAYIAK")
# -> 32-char MD5 hex digest

# 4. Plugin authors subclass the relevant ABC and register via entry_points.
class MyBackend(EmbeddingBackend):
    name = "my_backend"
    def load_model(self, model_name, device, emit): ...
    def embed_batch(self, model, tokenizer, sequences, *, emit, **kw): ...
```

---

## What lives here

| Module | Key exports | Used by |
|--------|-------------|---------|
| `annotation_source` | `AnnotationSource` (ABC) | `protea-sources`, PROTEA core |
| `embedding_backend` | `EmbeddingBackend` (ABC: `load_model`, `embed_batch`) | `protea-backends`, PROTEA core |
| `experiment_runner` | `ExperimentRunner` (ABC: `fit`, `evaluate`, `export`), `RunResult`, `EvalResult` | `protea-runners`, PROTEA core |
| `feature_registry` | `Feature`, `FeatureDtype`, `FeatureRegistry` | PROTEA core, `protea-runners.lightgbm` |
| `feature_schema` | `ALL_FEATURES`, `FEATURE_FAMILIES`, `compute_schema_sha`, `SCHEMA_VERSION` | PROTEA core (export + inference), `protea-runners.lightgbm` (training) |
| `payloads` | `ProteaPayload`, `PredictGOTermsPayload`, `PredictGOTermsBatchPayload`, `StorePredictionsPayload`, `RerankerSpec` | PROTEA core operations |
| `manifest` | `ManifestV1`, `DatasetSpec` | PROTEA core (export), `protea-runners.lightgbm` (training) |
| `records` | `GoaAnnotationRecord`, `GoaStreamPayload`, `QuickGoAnnotationRecord`, `QuickGoStreamPayload`, `EcoMappingPayload`, `UniProtProteinRecord`, `UniProtFastaStreamPayload`, `UniProtMetadataRecord`, `UniProtMetadataStreamPayload` | `protea-sources` (output), PROTEA core (input) |
| `bio_utils` | `parse_isoform`, `compute_sequence_hash` | PROTEA ORM (forwarder), `protea-sources` (UniProt parser) |
| `contexts` | `KnnContext`, `FeatureBuildContext`, `ExportContext`, `ExportSink` | PROTEA core operations |
| `embedding_payload` | `EmbeddingPayload` | `protea-backends`, PROTEA core |

All payloads and records are `frozen=True, strict=True, extra="forbid"` pydantic
models.

---

## Architecture

Full Sphinx documentation lives in `docs/source/`. Build locally:

```bash
poetry install --with docs
cd docs && make html
# open docs/build/html/index.html
```

The docs cover:

- Plugin ABC contracts and their lifecycle (ABCs section)
- Canonical feature schema and the schema_sha fingerprint guarantee
- Producer coverage CI guard (prevents dump-pipeline crashes on new columns)
- Contributing and SemVer evolution guide

---

## ADR index

| ADR | Title | Status |
|-----|-------|--------|
| D1 | Split contracts package from protea-core | Accepted |
| D10 | Unify compute_schema_sha to a single source of truth | Accepted |

---

## Versioning

SemVer 2.0.0:

- **Major** (X.0.0): breaking change to any public ABC, payload, record, or to the
  schema sha output.
- **Minor** (0.X.0): new features (additional fields with defaults, new optional
  methods on a plugin, new record type for a new source).
- **Patch** (0.0.X): bug fixes that do not change the contract.

Every release is tagged in git. The `compute_schema_sha` digest of `ALL_FEATURES` is
recomputed on every release and pinned in `tests/test_feature_schema.py`, so a
major-bump-worthy change cannot land without an explicit acknowledgement.

---

## Producer coverage CI

`ALL_FEATURES` is the canonical column set the PROTEA dump pipeline must emit.
When a column is added to `ALL_FEATURES` without an unconditional producer in the dump
path, the invariant only fails after multi-hour KNN compute (the 2026-05-13 lineage
incident burned roughly 5 hours of compute before crashing).

Every PR that touches `feature_schema.py` runs
`.github/workflows/producer-coverage.yml`, which iterates the full powerset of bool
flags on `PredictGOTermsBatchPayload` (128 combinations) and asserts that a mocked
dump producer emits a superset of `ALL_FEATURES` for every combination.

**Adding a new feature column safely:**

1. Append the column name to `NUMERIC_FEATURES` or `CATEGORICAL_FEATURES` in
   `feature_schema.py`.
2. Update `tests/test_feature_producer_coverage.py:_simulate_dump_record` to emit the
   new column unconditionally.
3. Open a matching PROTEA PR that wires the unconditional producer in
   `protea/core/_leaf_record_builder.py`.

If the column cannot be emitted unconditionally, it does not belong in `ALL_FEATURES`.

---

## Development

```bash
poetry install
poetry run pytest             # unit tests
poetry run ruff check .
poetry run mypy --strict src
```

---

## Contributing

All changes target `develop`; `main` tracks stable releases only.

```bash
git clone https://github.com/frapercan/protea-contracts.git
cd protea-contracts
git checkout develop
git checkout -b feature/my-change

poetry install

# Verify locally before opening a PR:
poetry run pytest
poetry run ruff check .
poetry run mypy --strict src

# Open a pull request targeting develop
```

Key constraints:

- **Zero runtime deps** on `sqlalchemy`, `fastapi`, `torch`, or `protea-core`. Adding
  any of those is a hard stop.
- **SemVer discipline.** Any change to a payload field name, dtype, or ordering of
  `ALL_FEATURES` is a breaking change that requires a major version bump and a
  coordinated upgrade of every downstream consumer (PROTEA, `protea-method`,
  `protea-reranker-lab`).
- **Golden test.** The `compute_schema_sha` digest of `ALL_FEATURES` is pinned in
  `tests/test_feature_schema.py`. A schema-breaking change that does not explicitly
  update the expected digest will fail CI.
- **Records are leaves.** New record types go in `records.py`. Plugin authors yield
  records; the consuming operation in PROTEA reads them. Records must not carry ORM
  references or cross the package boundary in the reverse direction.

---

## License

MIT. See `LICENSE`.

Author: Francisco Miguel Pérez Canales.
