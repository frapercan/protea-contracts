"""Tests for protea_contracts.payloads (T1.3)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import Field, ValidationError

from protea_contracts import (
    PredictGOTermsBatchPayload,
    PredictGOTermsPayload,
    ProteaPayload,
    RerankerSpec,
    StorePredictionsPayload,
)


def _uuid() -> str:
    return str(uuid.uuid4())


class TestProteaPayloadBase:
    def test_strict_mode_rejects_string_for_bool(self) -> None:
        class _P(ProteaPayload, frozen=True):
            flag: bool = False

        with pytest.raises(ValidationError):
            _P.model_validate({"flag": "yes"})

    def test_frozen(self) -> None:
        class _P(ProteaPayload, frozen=True):
            n: int = 1

        p = _P()
        with pytest.raises(ValidationError):
            p.n = 2  # type: ignore[misc]


class TestPredictGOTermsPayload:
    def _kwargs(self, **overrides: object) -> dict[str, object]:
        defaults: dict[str, object] = {
            "embedding_config_id": _uuid(),
            "annotation_set_id": _uuid(),
            "ontology_snapshot_id": _uuid(),
        }
        defaults.update(overrides)
        return defaults

    def test_minimal_valid_payload(self) -> None:
        p = PredictGOTermsPayload.model_validate(self._kwargs())
        # Defaults preserved exactly.
        assert p.limit_per_entry == 5
        assert p.batch_size == 1024
        assert p.search_backend == "numpy"
        assert p.compute_alignments is True
        assert p.compute_taxonomy is True
        assert p.compute_reranker_features is True
        assert p.compute_v6_features is False
        assert p.compute_lineage_features is False
        assert p.expand_votes_to_ancestors is False
        assert p.aspect_separated_knn is True
        assert p.reranker_model_id is None

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            PredictGOTermsPayload.model_validate(
                self._kwargs(embedding_config_id="")
            )
        with pytest.raises(ValidationError):
            PredictGOTermsPayload.model_validate(
                self._kwargs(ontology_snapshot_id="   ")
            )

    def test_strips_whitespace(self) -> None:
        p = PredictGOTermsPayload.model_validate(
            self._kwargs(embedding_config_id="  abc  ")
        )
        assert p.embedding_config_id == "abc"

    def test_limit_per_entry_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            PredictGOTermsPayload.model_validate(self._kwargs(limit_per_entry=0))

    def test_query_accessions_optional(self) -> None:
        p = PredictGOTermsPayload.model_validate(self._kwargs())
        assert p.query_accessions is None
        p2 = PredictGOTermsPayload.model_validate(
            self._kwargs(query_accessions=["P12345", "Q67890"])
        )
        assert p2.query_accessions == ["P12345", "Q67890"]


class TestPredictGOTermsBatchPayload:
    def _kwargs(self, **overrides: object) -> dict[str, object]:
        defaults: dict[str, object] = {
            "embedding_config_id": _uuid(),
            "annotation_set_id": _uuid(),
            "ontology_snapshot_id": _uuid(),
            "prediction_set_id": _uuid(),
            "parent_job_id": _uuid(),
            "query_accessions": ["P12345"],
        }
        defaults.update(overrides)
        return defaults

    def test_valid_payload(self) -> None:
        p = PredictGOTermsBatchPayload.model_validate(self._kwargs())
        assert p.limit_per_entry == 5
        assert p.aspect_separated_knn is True

    def test_query_accessions_required(self) -> None:
        kwargs = self._kwargs()
        del kwargs["query_accessions"]
        with pytest.raises(ValidationError):
            PredictGOTermsBatchPayload.model_validate(kwargs)

    def test_reranker_context_optional(self) -> None:
        p = PredictGOTermsBatchPayload.model_validate(self._kwargs())
        assert p.reranker_model_id is None
        assert p.reranker_artifact_uri is None
        assert p.reranker_feature_schema_sha is None


class TestStorePredictionsPayload:
    def test_valid_payload(self) -> None:
        p = StorePredictionsPayload.model_validate(
            {
                "parent_job_id": _uuid(),
                "prediction_set_id": _uuid(),
                "predictions": [{"protein": "P1", "go": "GO:1"}],
            }
        )
        assert p.is_final_chunk is True
        assert len(p.predictions) == 1

    def test_is_final_chunk_overridable(self) -> None:
        p = StorePredictionsPayload.model_validate(
            {
                "parent_job_id": _uuid(),
                "prediction_set_id": _uuid(),
                "predictions": [],
                "is_final_chunk": False,
            }
        )
        assert p.is_final_chunk is False


class TestRerankerSpec:
    def test_minimal_valid(self) -> None:
        spec = RerankerSpec.model_validate({"runner": "lightgbm"})
        assert spec.objective == "lambdarank"
        assert spec.enabled_feature_families is None
        assert spec.drop_features == []
        assert spec.seed == 42
        assert spec.extras == {}

    def test_runner_required(self) -> None:
        with pytest.raises(ValidationError):
            RerankerSpec.model_validate({})
        with pytest.raises(ValidationError):
            RerankerSpec.model_validate({"runner": ""})

    def test_runner_stripped(self) -> None:
        spec = RerankerSpec.model_validate({"runner": "  lightgbm  "})
        assert spec.runner == "lightgbm"

    def test_extras_passthrough(self) -> None:
        spec = RerankerSpec.model_validate(
            {"runner": "lightgbm", "extras": {"num_boost_round": 5000}}
        )
        assert spec.extras["num_boost_round"] == 5000

    def test_frozen(self) -> None:
        spec = RerankerSpec.model_validate({"runner": "lightgbm"})
        with pytest.raises(ValidationError):
            spec.runner = "gnn"  # type: ignore[misc]


class TestAProteinIsNotAutomaticallyItsOwnNeighbour:
    """The retriever can be told to exclude the query from its own neighbourhood.

    Recorded rather than assumed, and defaulting to the historical behaviour, so
    that a stored result keeps its meaning and a new one can say which of the two
    it is. The two are levels of the retriever, not a detail of how it ran.
    """

    def test_it_defaults_to_the_behaviour_every_stored_run_had(self) -> None:
        from protea_contracts import PredictGOTermsPayload

        p = PredictGOTermsPayload.model_validate(
            {"embedding_config_id": "22222222-2222-2222-2222-222222222222",
             "annotation_set_id": "33333333-3333-3333-3333-333333333333",
             "ontology_snapshot_id": "44444444-4444-4444-4444-444444444444"}
        )
        assert p.exclude_self_neighbour is False

    def test_it_travels_in_the_dump_so_the_receipt_can_carry_it(self) -> None:
        from protea_contracts import PredictGOTermsPayload

        p = PredictGOTermsPayload.model_validate(
            {"embedding_config_id": "22222222-2222-2222-2222-222222222222",
             "annotation_set_id": "33333333-3333-3333-3333-333333333333",
             "ontology_snapshot_id": "44444444-4444-4444-4444-444444444444",
             "exclude_self_neighbour": True}
        )
        assert p.exclude_self_neighbour is True
        assert p.model_dump()["exclude_self_neighbour"] is True


class TestTheBasePayloadRefusesWhatItCannotHonour:
    """The failure the other two settings do not cover.

    ``strict=True`` stops a value being coerced into the wrong type and
    ``frozen=True`` stops it changing afterwards. Neither stops a key the
    model never declared from being dropped on the floor, which is how a
    consumer running older code than its dispatcher does the wrong work and
    reports success.
    """

    def test_an_undeclared_key_is_refused_rather_than_dropped(self) -> None:
        class Demo(ProteaPayload, frozen=True):
            a: int

        with pytest.raises(ValidationError) as exc:
            Demo.model_validate({"a": 1, "max_k_position": 4})
        assert "max_k_position" in str(exc.value)

    def test_the_refusal_names_the_key_so_a_version_skew_is_readable(self) -> None:
        """A dispatcher reading this must be able to tell WHICH field is unknown.

        The whole value of the refusal is that it points at the field the
        consumer is too old to have, so "extra_forbidden" alone would leave
        the reader where the silent drop left them.
        """

        class Demo(ProteaPayload, frozen=True):
            a: int

        with pytest.raises(ValidationError) as exc:
            Demo.model_validate({"a": 1, "unknown_one": 1, "unknown_two": 2})
        message = str(exc.value)
        assert "unknown_one" in message
        assert "unknown_two" in message

    def test_a_declared_field_named_extras_is_untouched(self) -> None:
        """Forbidding extras does not forbid a field that happens to be a mapping."""

        class Demo(ProteaPayload, frozen=True):
            extras: dict[str, int] = Field(default_factory=dict)

        assert Demo.model_validate({"extras": {"k": 1}}).extras == {"k": 1}
