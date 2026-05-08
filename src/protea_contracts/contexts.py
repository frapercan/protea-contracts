"""Parameter-object containers for the inference and export hot paths.

These dataclasses encapsulate the data clumps that historically
travelled as 11-16 positional arguments across the KNN transfer, batch
inference, and frozen-dataset export entry points in ``protea-core``.

Refactoring guru: *Introduce Parameter Object* + *Preserve Whole
Object* (fixes Long Parameter List + Data Clumps).

These types are intentionally NOT JSON-serialisable: they carry numpy
arrays, in-memory dicts, and filesystem paths. They are the shape used
once the worker process has loaded references and is ready to do
work, not the shape that crosses the queue boundary. For boundary
types see :mod:`protea_contracts.payloads`.

Design rules:

- Frozen dataclasses (mutability of contained dicts is by convention).
- ``slots=True`` because instances are constructed many times per
  batch and ``__dict__`` overhead is wasted memory.
- All non-required fields default to ``None`` so call sites can adopt
  the contexts incrementally without one mega-PR.
- Infrastructure handles (SQLAlchemy ``Session``, ``ArtifactStore``,
  loggers, queue consumers) are intentionally absent: they are
  resources, not data, and stay as separate function arguments.

Example::

    from protea_contracts.contexts import KnnContext

    ctx = KnnContext(
        query_accessions=["P12345"],
        query_embeddings=embeddings_array,
        query_sequences={"P12345": "MAFLR..."},
    )
    predictions = predict(ctx, p=payload, *, store=store, session=session)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "ExportContext",
    "ExportSink",
    "FeatureBuildContext",
    "KnnContext",
]


@dataclass(frozen=True, slots=True)
class KnnContext:
    """Query + reference handles for a single KNN transfer batch.

    Used by both the inference path (``_predict_batch``) and the
    training path (``_knn_transfer_and_label``). The training path
    additionally populates :attr:`query_known_gos` with the labels
    visible at the snapshot pair's old version; the inference path
    leaves it ``None``.

    :attr:`ref_data` is an opaque legacy bag (``dict[str, dict]`` keyed
    by aspect) preserved for backward-compatibility during the F2C
    wire. A typed replacement is tracked as a future refactor; callers
    should treat its inner shape as private and access it only through
    helpers that already exist in ``protea-core``.
    """

    query_accessions: list[str]
    query_embeddings: NDArray[np.floating]
    query_sequences: dict[str, str] | None = None
    query_tax_ids: dict[str, int | None] | None = None
    query_known_gos: dict[str, set[str]] | None = None

    ref_data: Mapping[str, Any] | None = None
    ref_sequences: dict[str, str] | None = None
    ref_tax_ids: dict[str, int | None] | None = None

    neighbors: list[list[tuple[str, float]]] | None = None


@dataclass(frozen=True, slots=True)
class FeatureBuildContext:
    """Auxiliary structures shared across feature compute calls.

    Precomputed once per inference (or per training run) and re-used
    across query batches. Holding them in a single context keeps the
    per-call signatures stable as the feature set evolves.

    Fields:

    - ``ia_weights``: information-accretion per GO term (CAFA IA).
    - ``pca_state``: ``(mean, components)`` for embedding projection.
    - ``embedding_pool``: stacked reference embeddings for distance
      features.
    - ``pivot_go_ids``: the GO terms that anchor lineage features.
    - ``parent_map``: ancestor closure of the GO DAG, str-keyed.
    - ``go_id_map``: integer row id to GO term string.
    - ``aspect_map``: integer row id to aspect (``BPO``/``MFO``/``CCO``).
    - ``gt_pairs``: ground-truth ``(accession, go_id)`` pairs; training
      only.
    """

    ia_weights: dict[str, float] | None = None
    pca_state: tuple[NDArray[np.floating], NDArray[np.floating]] | None = None
    embedding_pool: NDArray[np.floating] | None = None
    pivot_go_ids: frozenset[str] | None = None
    parent_map: dict[str, frozenset[str]] | None = None
    go_id_map: dict[int, str] | None = None
    aspect_map: dict[int, str] | None = None
    gt_pairs: frozenset[tuple[str, str]] | None = None


@dataclass(frozen=True, slots=True)
class ExportContext:
    """What gets exported in a frozen reranker-dataset dump.

    Captures the source-side coordinates: dump directory, dataset
    name, KNN ``k``, the embedding/ontology/annotation handles that
    fix the semantic provenance, and the temporal split layout.

    Destination concerns (artefact store, key prefix, producer
    metadata) live in :class:`ExportSink`.
    """

    dump_dir: Path
    name: str
    k: int
    embedding_config_id: str
    ontology_snapshot_id: str
    annotation_source: str

    split_files: dict[str, list[Path]]
    valid_split_versions: list[tuple[int, int]]
    test_files: dict[str, Path | None]
    test_old_v: int
    test_new_v: int


@dataclass(frozen=True, slots=True)
class ExportSink:
    """Destination + provenance for a reranker-dataset export.

    Separated from :class:`ExportContext` so that re-exports against
    different stores (local FS vs MinIO) re-use the same source-side
    spec without copy-paste. The artefact store handle itself is not
    part of this dataclass: stores carry network sockets and are
    resources, not data.
    """

    key_prefix: str = ""
    producer_version: str | None = None
    producer_git_sha: str | None = None
