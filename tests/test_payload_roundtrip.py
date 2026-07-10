"""Round-trip stability for every pydantic payload class on the surface.

For each payload type re-exported from :mod:`protea_contracts`, build a
canonical valid instance and assert
``Class.model_validate(instance.model_dump()) == instance``. Catches
the regression class where a default factory, custom validator, or
extra-field policy is changed in a way that breaks the
serialise / deserialise loop (which the JSONB-backed job queue relies
on every time a Job is enqueued and later resumed).

Per-payload kwargs live in :data:`CANONICAL_KWARGS`; adding a new
payload to ``__all__`` MUST also add an entry there or the
:func:`test_every_pydantic_payload_in_all_is_covered` guard fails.
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any

import numpy as np
import pytest
from pydantic import BaseModel

import protea_contracts
from protea_contracts import (
    DatasetSpec,
    EcoMappingPayload,
    EmbeddingPayload,
    GoaAnnotationRecord,
    GoaStreamPayload,
    ManifestV1,
    PredictGOTermsBatchPayload,
    PredictGOTermsPayload,
    ProteaPayload,
    QuickGoAnnotationRecord,
    QuickGoStreamPayload,
    RerankerSpec,
    StorePredictionsPayload,
    UniProtFastaStreamPayload,
    UniProtMetadataRecord,
    UniProtMetadataStreamPayload,
    UniProtProteinRecord,
)

#: Payload classes whose round-trip is intentionally NOT covered here:
#:
#: - :class:`ProteaPayload` is the abstract base. Subclasses cover it.
#: - :class:`EmbeddingPayload` carries numpy ndarrays whose default
#:   ``model_dump`` round-trip is not equality-stable
#:   (``np.array != np.array.tolist()``); the type already has its own
#:   dedicated invariant tests in ``test_embedding_payload.py``.
_ROUNDTRIP_EXEMPT: frozenset[type[BaseModel]] = frozenset({
    ProteaPayload,
    EmbeddingPayload,
})


def _uuid() -> str:
    return str(uuid.uuid4())


#: Canonical valid kwargs per payload class. Each entry must be the
#: minimal-but-complete dict that constructs a representative instance.
#: When a new payload is added to ``protea_contracts.__all__``, an entry
#: here is required (see ``test_every_pydantic_payload_in_all_is_covered``).
CANONICAL_KWARGS: dict[type[BaseModel], dict[str, Any]] = {
    PredictGOTermsPayload: {
        "embedding_config_id": _uuid(),
        "annotation_set_id": _uuid(),
        "ontology_snapshot_id": _uuid(),
    },
    PredictGOTermsBatchPayload: {
        "embedding_config_id": _uuid(),
        "annotation_set_id": _uuid(),
        "ontology_snapshot_id": _uuid(),
        "prediction_set_id": _uuid(),
        "parent_job_id": _uuid(),
        "query_accessions": ["P12345"],
    },
    StorePredictionsPayload: {
        "parent_job_id": _uuid(),
        "prediction_set_id": _uuid(),
        "predictions": [{"protein": "P1", "go": "GO:0008150"}],
    },
    RerankerSpec: {"runner": "lightgbm"},
    GoaStreamPayload: {"gaf_url": "https://example.org/goa.gaf.gz"},
    QuickGoStreamPayload: {"gene_product_ids": ["P12345", "Q67890"]},
    EcoMappingPayload: {"url": "https://example.org/eco.txt"},
    QuickGoAnnotationRecord: {"accession": "P12345", "go_id": "GO:0008150"},
    UniProtFastaStreamPayload: {"search_criteria": "reviewed:true"},
    UniProtMetadataStreamPayload: {
        "search_criteria": "reviewed:true",
        "fields": ["accession", "reviewed"],
    },
    UniProtMetadataRecord: {
        "accession": "P12345",
        "raw_fields": {"Entry": "P12345", "Reviewed": "reviewed"},
    },
    UniProtProteinRecord: {
        "accession": "P12345",
        "canonical_accession": "P12345",
        "is_canonical": True,
        "reviewed": True,
        "sequence": "MTEYKLVVVGAG",
        "length": 12,
        "sequence_hash": "0123456789abcdef0123456789abcdef",
    },
    GoaAnnotationRecord: {"accession": "P12345", "go_id": "GO:0008150"},
    DatasetSpec: {
        "name": "smoke-v0",
        "source_manifest": "/tmp/manifest.json",
        "enabled_feature_families": None,
        "drop_features": [],
        "train_snapshot_pairs": None,
        "eval_snapshot_pair": None,
    },
    ManifestV1: {
        "name": "smoke-v0",
        "k": 5,
        "embedding_config_id": _uuid(),
        "ontology_snapshot_id": _uuid(),
        "train_snapshot_pairs": ["v226"],
        "eval_snapshot_pair": "v230",
        "schema_sha": "0" * 12,
    },
}


def _embedding_payload_instance() -> EmbeddingPayload:
    """Build a representative mean-pool ``EmbeddingPayload`` for the smoke test."""
    return EmbeddingPayload(
        granularity="mean_pool",
        embeddings=np.zeros((2, 4), dtype=np.float16),
    )


def _all_pydantic_payload_classes() -> list[type[BaseModel]]:
    """Discover every pydantic model re-exported via ``__all__``.

    Anything that subclasses :class:`pydantic.BaseModel` and is listed
    in :data:`protea_contracts.__all__` counts. ABCs, dataclasses
    (:class:`RunResult`, :class:`EvalResult`, :class:`Feature`) and
    constants are skipped. Classes in :data:`_ROUNDTRIP_EXEMPT` are
    dropped (see the constant's docstring for the rationale).
    """
    out: list[type[BaseModel]] = []
    for name in protea_contracts.__all__:
        obj = getattr(protea_contracts, name, None)
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseModel)
            and obj not in _ROUNDTRIP_EXEMPT
        ):
            out.append(obj)
    return out


def test_every_pydantic_payload_in_all_is_covered() -> None:
    """``CANONICAL_KWARGS`` must cover every payload exported from the package.

    A new payload added without a fixture here would skip the
    round-trip check; that defeats the point of this module. Failure
    mode: add the new class to ``CANONICAL_KWARGS`` with a valid
    minimal dict and the rest of the suite picks it up automatically.
    """
    discovered = {cls.__name__ for cls in _all_pydantic_payload_classes()}
    covered = {cls.__name__ for cls in CANONICAL_KWARGS}
    missing = sorted(discovered - covered)
    extra = sorted(covered - discovered)
    assert not missing, (
        f"Pydantic payloads missing from CANONICAL_KWARGS: {missing!r}. "
        "Add a canonical valid kwargs dict for each so the round-trip "
        "suite covers them."
    )
    assert not extra, (
        f"CANONICAL_KWARGS entries no longer reachable via "
        f"protea_contracts.__all__: {extra!r}. Either re-export them "
        "from src/protea_contracts/__init__.py or drop the fixture."
    )


@pytest.mark.parametrize(
    "cls, kwargs",
    list(CANONICAL_KWARGS.items()),
    ids=lambda v: v.__name__ if inspect.isclass(v) else "kwargs",
)
def test_payload_roundtrip(cls: type[BaseModel], kwargs: dict[str, Any]) -> None:
    """``Class.model_validate(instance.model_dump()) == instance`` for every payload.

    The PROTEA worker pipeline serialises payloads to JSONB on enqueue
    and re-validates on dequeue; a payload that fails to round-trip
    silently loses fields or coerces types, with the worker only
    discovering it mid-job.
    """
    instance = cls.model_validate(kwargs)
    dumped = instance.model_dump()
    rebuilt = cls.model_validate(dumped)
    assert rebuilt == instance, (
        f"{cls.__name__} failed model_validate(model_dump()) round-trip; "
        "a default factory, custom validator, or extra-field policy may "
        "have drifted out of sync with the dump path."
    )


@pytest.mark.parametrize(
    "cls, kwargs",
    list(CANONICAL_KWARGS.items()),
    ids=lambda v: v.__name__ if inspect.isclass(v) else "kwargs",
)
def test_payload_json_roundtrip(cls: type[BaseModel], kwargs: dict[str, Any]) -> None:
    """JSON-mode dump must also round-trip (Job.payload JSONB hot path).

    ``model_dump(mode="json")`` serialises types like ``Path`` to
    strings, which is what the JSONB column actually stores. The
    Python-mode round-trip above is necessary but not sufficient: a
    payload field whose JSON form does not validate back would still
    crash the worker on dequeue.
    """
    instance = cls.model_validate(kwargs)
    json_dumped = instance.model_dump(mode="json")
    rebuilt = cls.model_validate(json_dumped)
    assert rebuilt == instance, (
        f"{cls.__name__} failed JSON-mode round-trip; the JSONB-backed "
        "queue would lose data on dequeue."
    )


def test_embedding_payload_smoke_construct_and_dump() -> None:
    """:class:`EmbeddingPayload` is exempt from the generic round-trip
    (numpy ndarrays do not compare by value through
    ``model_dump``/``model_validate``) but its constructor + dump path
    must still succeed without raising. The dedicated invariant suite
    in ``test_embedding_payload.py`` covers the shape semantics.
    """
    payload = _embedding_payload_instance()
    assert payload.granularity == "mean_pool"
    dumped = payload.model_dump()
    assert "embeddings" in dumped
    # Recovering shape via as_matrix() exercises the consumer hot path.
    matrix = payload.as_matrix()
    assert matrix.shape == (2, 4)
