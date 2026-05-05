"""Shared contract surface for the PROTEA stack."""

from protea_contracts.annotation_source import AnnotationSource
from protea_contracts.embedding_backend import EmbeddingBackend
from protea_contracts.experiment_runner import EvalResult, ExperimentRunner, RunResult
from protea_contracts.feature_registry import Feature, FeatureDtype, FeatureRegistry
from protea_contracts.feature_schema import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    EMBEDDING_PCA_DIM,
    FEATURE_FAMILIES,
    LABEL_COLUMN,
    NUMERIC_FEATURES,
    RESERVED_COLUMNS,
    SCHEMA_VERSION,
    compute_feature_schema_sha,
    compute_schema_sha,
    required_columns,
)
from protea_contracts.manifest import DatasetSpec, ManifestV1
from protea_contracts.payloads import (
    PredictGOTermsBatchPayload,
    PredictGOTermsPayload,
    ProteaPayload,
    RerankerSpec,
    StorePredictionsPayload,
)

__version__ = "0.1.0"

__all__ = [
    "ALL_FEATURES",
    "CATEGORICAL_FEATURES",
    "EMBEDDING_PCA_DIM",
    "FEATURE_FAMILIES",
    "LABEL_COLUMN",
    "NUMERIC_FEATURES",
    "RESERVED_COLUMNS",
    "SCHEMA_VERSION",
    "AnnotationSource",
    "DatasetSpec",
    "EmbeddingBackend",
    "EvalResult",
    "ExperimentRunner",
    "Feature",
    "FeatureDtype",
    "FeatureRegistry",
    "ManifestV1",
    "PredictGOTermsBatchPayload",
    "PredictGOTermsPayload",
    "ProteaPayload",
    "RerankerSpec",
    "RunResult",
    "StorePredictionsPayload",
    "__version__",
    "compute_feature_schema_sha",
    "compute_schema_sha",
    "required_columns",
]
