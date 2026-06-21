"""Shared contract surface for the PROTEA stack."""

from protea_contracts.annotation_source import AnnotationSource
from protea_contracts.axis_tuple import (
    CANONICAL_AXIS_KEYS,
    SHORTID_HEX_LEN,
    axis_tuple_shortid,
)
from protea_contracts.bio_utils import compute_sequence_hash, parse_isoform
from protea_contracts.contexts import (
    ExportContext,
    ExportSink,
    FeatureBuildContext,
    KnnContext,
)
from protea_contracts.embedding_backend import EmbeddingBackend
from protea_contracts.embedding_payload import EmbeddingPayload, Granularity
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
from protea_contracts.records import (
    EcoMappingPayload,
    GoaAnnotationRecord,
    GoaStreamPayload,
    QuickGoAnnotationRecord,
    QuickGoStreamPayload,
    UniProtFastaStreamPayload,
    UniProtMetadataRecord,
    UniProtMetadataStreamPayload,
    UniProtProteinRecord,
)

__version__ = "0.7.0"

__all__ = [
    "ALL_FEATURES",
    "CANONICAL_AXIS_KEYS",
    "CATEGORICAL_FEATURES",
    "EMBEDDING_PCA_DIM",
    "FEATURE_FAMILIES",
    "LABEL_COLUMN",
    "NUMERIC_FEATURES",
    "RESERVED_COLUMNS",
    "SCHEMA_VERSION",
    "SHORTID_HEX_LEN",
    "AnnotationSource",
    "DatasetSpec",
    "EcoMappingPayload",
    "EmbeddingBackend",
    "EmbeddingPayload",
    "EvalResult",
    "ExperimentRunner",
    "ExportContext",
    "ExportSink",
    "Feature",
    "FeatureBuildContext",
    "FeatureDtype",
    "FeatureRegistry",
    "GoaAnnotationRecord",
    "GoaStreamPayload",
    "Granularity",
    "KnnContext",
    "ManifestV1",
    "PredictGOTermsBatchPayload",
    "PredictGOTermsPayload",
    "ProteaPayload",
    "QuickGoAnnotationRecord",
    "QuickGoStreamPayload",
    "RerankerSpec",
    "RunResult",
    "StorePredictionsPayload",
    "UniProtFastaStreamPayload",
    "UniProtMetadataRecord",
    "UniProtMetadataStreamPayload",
    "UniProtProteinRecord",
    "__version__",
    "axis_tuple_shortid",
    "compute_feature_schema_sha",
    "compute_schema_sha",
    "compute_sequence_hash",
    "parse_isoform",
    "required_columns",
]
