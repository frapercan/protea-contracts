# protea-contracts

Shared contract surface for the [PROTEA](https://github.com/frapercan/protea)
stack. Holds the four plugin ABCs, the typed payload + record types
that cross package boundaries, the canonical feature schema, and the
pure-function bio utilities that ORM models and source plugins both
reuse. Zero runtime deps on `sqlalchemy`, `fastapi`, `torch`, or
`protea-core` — this package must stay importable from any consumer
without dragging the platform.

## 5 minutes to your first plugin import

```bash
pip install protea-contracts
```

```python
from protea_contracts import (
    AnnotationSource, EmbeddingBackend, ExperimentRunner,
    GoaAnnotationRecord, GoaStreamPayload,
    parse_isoform, compute_sequence_hash,
    compute_schema_sha, ALL_FEATURES,
)

# 1. Build a typed payload — typos fail at construction, not at runtime.
payload = GoaStreamPayload(gaf_url="https://example.com/x.gaf.gz")

# 2. Build a frozen record — validates field shape + types at construction.
record = GoaAnnotationRecord(accession="P12345", go_id="GO:0008150")

# 3. Use the bio utilities directly, no ORM needed.
canonical, is_canonical, idx = parse_isoform("P12345-2")
# -> ("P12345", False, 2)

seq_hash = compute_sequence_hash("MKTAYIAK")
# -> 32-char MD5 hex digest

# 4. Plugin authors subclass the relevant ABC.
class MyBackend(EmbeddingBackend):
    name = "my_backend"
    def load_model(self, model_name, device, emit): ...
    def embed_batch(self, model, tokenizer, sequences, *, emit, **kw): ...
```

## What lives here

| Module | Exports | Used by |
|--------|---------|---------|
| `annotation_source` | `AnnotationSource` (marker ABC) | `protea-sources`, `protea-core` |
| `embedding_backend` | `EmbeddingBackend` (ABC: `load_model`, `embed_batch`) | `protea-backends`, `protea-core` |
| `experiment_runner` | `ExperimentRunner` (ABC: `fit`, `evaluate`, `export`), `RunResult`, `EvalResult` | `protea-runners`, `protea-core` |
| `feature_registry` | `Feature`, `FeatureDtype`, `FeatureRegistry` | `protea-core`, `protea-runners.lightgbm` |
| `feature_schema` | `ALL_FEATURES`, `FEATURE_FAMILIES`, `compute_schema_sha`, `compute_feature_schema_sha`, `RESERVED_COLUMNS`, `LABEL_COLUMN`, `SCHEMA_VERSION` | `protea-core` (export + inference), `protea-runners.lightgbm` (training) |
| `payloads` | `ProteaPayload` base, `PredictGOTermsPayload`, `PredictGOTermsBatchPayload`, `StorePredictionsPayload`, `RerankerSpec` | `protea-core` operations |
| `manifest` | `ManifestV1`, `DatasetSpec` | `protea-core` (export), `protea-runners.lightgbm` (training) |
| `records` | `GoaAnnotationRecord`, `GoaStreamPayload`, `QuickGoAnnotationRecord`, `QuickGoStreamPayload`, `EcoMappingPayload`, `UniProtProteinRecord`, `UniProtFastaStreamPayload`, `UniProtMetadataRecord`, `UniProtMetadataStreamPayload` | `protea-sources` (output), `protea-core` (input to operations) |
| `bio_utils` | `parse_isoform`, `compute_sequence_hash` | `protea-core` ORM (forwarder), `protea-sources` (UniProt parser) |

All payloads and records are `frozen=True, strict=True, extra="forbid"`
pydantic models. Field typos and missing required fields fail at
construction time with `ValidationError`, not at runtime when the
data is consumed.

## Hard constraints

- **Zero runtime deps** to `sqlalchemy`, `fastapi`, `torch`, or
  `protea-core`. The package must stay importable from any consumer
  without dragging the platform.
- **Public API is SemVer-ed**. The `compute_schema_sha` digest is
  load-bearing: bumping any field name, dtype, or the canonical
  ordering forces a major version bump and re-training of every
  downstream LightGBM booster. PROTEA persists the digest of the
  trained booster's feature set on every `RerankerModel` row and
  refuses to use a booster whose digest drifts from the live
  inference pipeline (the schema_sha drift incident of 2026-05-01,
  documented in PROTEA chapter 4 §4.4 and ADR D10).
- **Records are leaves**. Plugin authors yield records from
  `stream*()` methods; PROTEA operations consume them and never
  pass them back across the boundary. This keeps the contract
  one-way and makes the dataflow easy to audit.

## Versioning

SemVer 2.0.0:

- **Major** (X.0.0): breaking change to any public ABC, payload,
  record, or to the schema sha output.
- **Minor** (0.X.0): new features (additional fields with defaults,
  new optional methods on a plugin, new record type for a new
  source).
- **Patch** (0.0.X): bug fixes that do not change the contract.

Every release is tagged in git. The `compute_schema_sha` digest of
`ALL_FEATURES` is recomputed on every release and pinned in a
golden test (`tests/test_feature_schema.py`) so a major-bump-worthy
change cannot land without an explicit acknowledgement.

## Development

```bash
poetry install
poetry run pytest             # ~140 tests, ~0.3s
poetry run ruff check .
poetry run mypy --strict src
```

## Documentation

Full Sphinx documentation in `docs/source/` — every ABC and every
payload/record class autodocumented with usage examples. Build
locally with `poetry install --with docs && cd docs && make html`.

## License

MIT. See `LICENSE`.
