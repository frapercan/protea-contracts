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

__version__ = "0.0.1"

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
    "EmbeddingBackend",
    "EvalResult",
    "ExperimentRunner",
    "Feature",
    "FeatureDtype",
    "FeatureRegistry",
    "RunResult",
    "__version__",
    "compute_feature_schema_sha",
    "compute_schema_sha",
    "required_columns",
]
