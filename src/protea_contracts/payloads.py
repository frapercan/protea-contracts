"""Pydantic payloads shared between protea-core and downstream plugins.

These are the immutable, strictly-typed input shapes for the platform
operations. Every Job's ``payload`` JSONB must validate against one of
these models before the worker dispatches the operation.

This module is intentionally separate from
:mod:`protea_contracts.feature_schema` so callers that only need the
payload shape (e.g. the frontend submitting a Job) do not have to
import the feature constants.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Convenience alias used across payload field declarations.
PositiveInt = Annotated[int, Field(gt=0)]


class ProteaPayload(BaseModel):
    """Immutable, strictly-typed base class for all operation payloads.

    Subclass and declare fields using pydantic annotations. Validation
    runs automatically via :meth:`model_validate`. ``strict=True``
    prevents silent type coercion (``"yes"`` is not a valid ``bool``).
    """

    model_config = ConfigDict(strict=True, frozen=True)


# ---------------------------------------------------------------------------
# predict_go_terms payloads
# ---------------------------------------------------------------------------


class PredictGOTermsPayload(ProteaPayload, frozen=True):
    """Payload for the ``predict_go_terms`` coordinator job."""

    embedding_config_id: str
    annotation_set_id: str
    ontology_snapshot_id: str
    query_accessions: list[str] | None = None
    query_set_id: str | None = None
    limit_per_entry: PositiveInt = 5
    distance_threshold: float | None = None
    batch_size: PositiveInt = 1024

    # Search backend
    search_backend: str = "numpy"
    metric: str = "cosine"
    faiss_index_type: str = "Flat"
    faiss_nlist: int = 100
    faiss_nprobe: int = 10
    faiss_hnsw_m: int = 32
    faiss_hnsw_ef_search: int = 64

    # Feature engineering: enabled by default so every PredictionSet
    # carries the full scoring/reranking feature set. Callers must opt
    # *out* explicitly when they want a lean KNN-only run.
    compute_alignments: bool = True
    compute_taxonomy: bool = True
    compute_reranker_features: bool = True

    # v6 reranker features: 6 Anc2Vec + 3 tax_voters + 16 emb_pca.
    # When enabled, PCA state is fit once per ``EmbeddingConfig`` and
    # the 25 extra columns are persisted on every ``GOPrediction`` row.
    compute_v6_features: bool = False

    # Lineage features (4 columns) describing the GO-DAG relation
    # between each candidate term and the query's pre-cutoff known
    # annotations. Default off so existing boosters (trained without
    # the lineage family) continue to score bit-exact.
    compute_lineage_features: bool = False
    # First-place LAFA system producers (lafa-integrate). Opt-in; default
    # off so existing predictions are bit-exact. compute_classifier adds the
    # direct full-catalogue predictor (also contributes candidates);
    # compute_self_prior uses the query's own pre-cutoff non-experimental
    # annotations; compute_association uses the cross-aspect conditional
    # probability of each candidate given the protein's known pre-cutoff terms.
    compute_classifier: bool = False
    compute_self_prior: bool = False
    compute_association: bool = False
    # compute_ia attaches IA(t), the snapshot-invariant information accretion of
    # each candidate term (the go_id-keyed quantity cafaeval f_micro_w weights
    # with), as a booster feature on the GOPrediction features JSONB blob.
    # Default off so existing predictions stay bit-exact. ``ia_file`` overrides
    # the IA table source (else PROTEA_IA_FEATURE_PATH env or the snapshot ia_url).
    compute_ia: bool = False
    ia_file: str | None = None

    # Ancestor expansion of leaf GO predictions (opt-in). When enabled,
    # every leaf candidate gets its is_a / part_of ancestor closure
    # synthesised as additional records, matching the candidate
    # distribution the lab booster saw at training time.
    expand_votes_to_ancestors: bool = False

    # Per-aspect KNN indices (opt-in). When True, three separate KNN
    # indices are built (one per GO aspect P/F/C). Guarantees every
    # query receives BPO/MFO/CCO candidates even if its nearest
    # neighbours in a unified index happen to be annotated only in one
    # or two aspects (a common cause of BPO recall ceilings).
    aspect_separated_knn: bool = True

    # Optional reranker promoted from protea-runners.lightgbm. When
    # set, the batch worker scores predictions with the referenced
    # booster after validating ``feature_schema_sha`` against the live
    # feature set; mismatch degrades to KNN-distance ordering rather
    # than crashing.
    reranker_model_id: str | None = None

    # Per-category (NK / LK / PK) reranker dispatch (lafa-integrate INT-5).
    # The first-place LAFA system trains three LightGBM boosters, one per
    # CAFA partition. When all three are set the batch worker assigns every
    # candidate a category from the query's pre-cutoff EXPERIMENTAL known
    # terms and scores it with the matching booster. Default None keeps the
    # single ``reranker_model_id`` path (no regression).
    reranker_model_id_nk: str | None = None
    reranker_model_id_lk: str | None = None
    reranker_model_id_pk: str | None = None

    @field_validator(
        "embedding_config_id",
        "annotation_set_id",
        "ontology_snapshot_id",
        mode="before",
    )
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()


class PredictGOTermsBatchPayload(ProteaPayload, frozen=True):
    """Payload for one KNN batch dispatched by the coordinator."""

    embedding_config_id: str
    annotation_set_id: str
    ontology_snapshot_id: str
    prediction_set_id: str
    parent_job_id: str
    query_accessions: list[str]
    query_set_id: str | None = None
    limit_per_entry: PositiveInt = 5
    distance_threshold: float | None = None
    search_backend: str = "numpy"
    metric: str = "cosine"
    faiss_index_type: str = "Flat"
    faiss_nlist: int = 100
    faiss_nprobe: int = 10
    faiss_hnsw_m: int = 32
    faiss_hnsw_ef_search: int = 64

    # Feature engineering: kept in sync with PredictGOTermsPayload defaults.
    compute_alignments: bool = True
    compute_taxonomy: bool = True
    compute_reranker_features: bool = True
    compute_v6_features: bool = False
    # Lineage features (4 columns) describing the GO-DAG relation
    # between each candidate term and the query's pre-cutoff known
    # annotations. Default off so bit-exact reproducibility against
    # the current lab champion (52 features, no lineage) is preserved.
    compute_lineage_features: bool = False
    # First-place LAFA system producers (lafa-integrate). Opt-in; default
    # off so existing predictions are bit-exact. compute_classifier adds the
    # direct full-catalogue predictor (also contributes candidates);
    # compute_self_prior uses the query's own pre-cutoff non-experimental
    # annotations; compute_association uses the cross-aspect conditional
    # probability of each candidate given the protein's known pre-cutoff terms.
    compute_classifier: bool = False
    compute_self_prior: bool = False
    compute_association: bool = False
    # IA information-accretion feature; kept in sync with PredictGOTermsPayload.
    compute_ia: bool = False
    ia_file: str | None = None
    expand_votes_to_ancestors: bool = False
    aspect_separated_knn: bool = True

    # Reranker context propagated from the coordinator. ``artifact_uri``
    # and ``feature_schema_sha`` are snapshotted at dispatch time so the
    # worker does not have to re-query the RerankerModel row.
    reranker_model_id: str | None = None
    reranker_artifact_uri: str | None = None
    reranker_feature_schema_sha: str | None = None

    # Per-category (NK / LK / PK) reranker dispatch (lafa-integrate INT-5).
    # The coordinator snapshots each per-category booster's artifact_uri +
    # feature_schema_sha so the batch worker scores without re-querying the
    # RerankerModel rows. When all three (artifact_uri, feature_schema_sha)
    # pairs are present the worker splits candidates by category and applies
    # the matching booster; otherwise it falls back to the single-booster
    # ``reranker_artifact_uri`` path (no regression).
    reranker_nk_artifact_uri: str | None = None
    reranker_nk_feature_schema_sha: str | None = None
    reranker_lk_artifact_uri: str | None = None
    reranker_lk_feature_schema_sha: str | None = None
    reranker_pk_artifact_uri: str | None = None
    reranker_pk_feature_schema_sha: str | None = None


class StorePredictionsPayload(ProteaPayload, frozen=True):
    """Payload carrying serialized prediction dicts to the write worker."""

    parent_job_id: str
    prediction_set_id: str
    predictions: list[dict[str, Any]]

    # When the upstream batch chunks its predictions across multiple
    # write messages (because the full payload exceeds the RabbitMQ
    # 128 MB limit), only the last chunk should advance the coordinator's
    # batch counter; otherwise ``progress_current`` ticks once per chunk
    # and the parent job marks itself succeeded before all batches finish.
    is_final_chunk: bool = True


# ---------------------------------------------------------------------------
# Reranker training spec (consumed by protea-runners)
# ---------------------------------------------------------------------------


class RerankerSpec(BaseModel):
    """Runner-agnostic spec for a reranker training run.

    Travels in the ``ExperimentRun.hparams`` JSONB and is the input to
    :meth:`protea_contracts.experiment_runner.ExperimentRunner.fit`.
    Concrete runners (``lightgbm``, future ``gnn``, etc.) can validate
    additional knobs through ``extras``.
    """

    runner: str
    """Plugin name resolved against the ``protea.runners`` entry_points."""

    objective: str = "lambdarank"
    """``"binary"`` (logloss + AUC) or ``"lambdarank"`` (listwise)."""

    enabled_feature_families: list[str] | None = None
    """``None`` keeps all feature families. Otherwise the union of the listed."""

    drop_features: list[str] = Field(default_factory=list)
    """Explicit feature names to exclude even when their family is active."""

    seed: int = 42
    extras: dict[str, Any] = Field(default_factory=dict)
    """Runner-specific knobs validated by the implementation."""

    model_config = ConfigDict(strict=True, frozen=True)

    @field_validator("runner", mode="before")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("runner must be a non-empty string")
        return v.strip()
