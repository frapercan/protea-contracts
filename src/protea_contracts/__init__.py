"""Shared contract surface for the PROTEA stack."""

from protea_contracts.annotation_source import AnnotationSource
from protea_contracts.embedding_backend import EmbeddingBackend
from protea_contracts.experiment_runner import EvalResult, ExperimentRunner, RunResult
from protea_contracts.feature_registry import Feature, FeatureDtype, FeatureRegistry

__version__ = "0.0.1"

__all__ = [
    "AnnotationSource",
    "EmbeddingBackend",
    "EvalResult",
    "ExperimentRunner",
    "Feature",
    "FeatureDtype",
    "FeatureRegistry",
    "RunResult",
    "__version__",
]
