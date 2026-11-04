"""The donor policy: who may donate annotations, and how it reaches a cache key.

The pool used to be defined only as "has a representation under this
configuration" and "has some annotation in this set". These tests pin the two
properties that make adding a policy safe: an unset policy behaves exactly as
before, and a set one changes the cache key so a pool built under one policy
can never be served for another.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from protea_contracts.payloads import (
    DonorPolicy,
    PredictGOTermsBatchPayload,
    PredictGOTermsPayload,
)


class TestDefaultIsTheHistoricalBehaviour:
    def test_unset_policy_admits_everything(self) -> None:
        assert DonorPolicy().is_permissive is True

    def test_unset_policy_does_not_change_the_cache_key(self) -> None:
        """An empty discriminator leaves existing cache entries valid."""
        assert DonorPolicy().cache_discriminator() == ""

    @pytest.mark.parametrize("model", [PredictGOTermsPayload, PredictGOTermsBatchPayload])
    def test_a_payload_without_a_policy_gets_the_permissive_one(
        self, model: type[PredictGOTermsPayload] | type[PredictGOTermsBatchPayload]
    ) -> None:
        common: dict[str, object] = {
            "embedding_config_id": "cfg",
            "annotation_set_id": "aset",
            "ontology_snapshot_id": "snap",
        }
        if model is PredictGOTermsBatchPayload:
            common |= {
                "prediction_set_id": "pset",
                "parent_job_id": "job",
                "query_accessions": ["P00001"],
            }
        payload = model.model_validate(common)
        assert payload.donor_policy.is_permissive is True


class TestARestrictedPolicy:
    def test_any_restriction_makes_it_non_permissive(self) -> None:
        assert DonorPolicy(reviewed_only=True).is_permissive is False
        assert DonorPolicy(evidence_codes=["EXP"]).is_permissive is False
        assert DonorPolicy(exclude_reference_prefixes=["GO_REF:0000002"]).is_permissive is False

    def test_it_changes_the_cache_key(self) -> None:
        assert DonorPolicy(reviewed_only=True).cache_discriminator() != ""

    def test_different_policies_get_different_keys(self) -> None:
        """The property that prevents one policy's pool serving another."""
        seen = {
            DonorPolicy(reviewed_only=True).cache_discriminator(),
            DonorPolicy(evidence_codes=["EXP"]).cache_discriminator(),
            DonorPolicy(evidence_codes=["IEA"]).cache_discriminator(),
            DonorPolicy(exclude_reference_prefixes=["GO_REF:0000002"]).cache_discriminator(),
        }
        assert len(seen) == 4

    def test_the_key_does_not_depend_on_declaration_order(self) -> None:
        """Two spellings of the same policy must not build two pools."""
        a = DonorPolicy(evidence_codes=["EXP", "IDA"])
        b = DonorPolicy(evidence_codes=["IDA", "EXP"])
        assert a.cache_discriminator() == b.cache_discriminator()

    def test_the_policy_is_immutable(self) -> None:
        policy = DonorPolicy(reviewed_only=True)
        with pytest.raises(ValidationError):
            policy.reviewed_only = False  # type: ignore[misc]


class TestItTravelsOnThePayload:
    def test_a_restricted_policy_survives_validation(self) -> None:
        payload = PredictGOTermsBatchPayload.model_validate(
            {
                "embedding_config_id": "cfg",
                "annotation_set_id": "aset",
                "ontology_snapshot_id": "snap",
                "prediction_set_id": "pset",
                "parent_job_id": "job",
                "query_accessions": ["P00001"],
                "donor_policy": {
                    "reviewed_only": True,
                    "evidence_codes": ["EXP", "IDA"],
                    "exclude_reference_prefixes": ["GO_REF:0000002"],
                },
            }
        )
        assert payload.donor_policy.reviewed_only is True
        assert payload.donor_policy.evidence_codes == ["EXP", "IDA"]
        assert payload.donor_policy.is_permissive is False


class TestMembershipAtTheWindowStart:
    """``admitted_by_release``: a donor must already be a member of the corpus.

    Measured on 2026-11-04: release 211's annotation set carries 30,128
    proteins the corpus admitted only later, 29,922 of which donate in the
    full length ankh bank. These pin that the restriction travels, keys its
    own cache, and leaves every policy recorded before it byte-identical.
    """

    def test_it_is_unset_by_default(self) -> None:
        assert DonorPolicy().admitted_by_release is None

    def test_setting_it_restricts_the_pool(self) -> None:
        assert DonorPolicy(admitted_by_release=211).is_permissive is False

    def test_it_keys_its_own_cache(self) -> None:
        assert DonorPolicy(admitted_by_release=211).cache_discriminator() == (
            "reviewed=0|codes=*|norefs=*|admitted<=211"
        )
        assert (
            DonorPolicy(admitted_by_release=211).cache_discriminator()
            != DonorPolicy(admitted_by_release=227).cache_discriminator()
        )

    def test_every_key_minted_before_it_stays_the_same(self) -> None:
        # A pool cached under a policy that never mentioned membership keeps
        # its key, so the disk cache is not invalidated by the new field.
        assert DonorPolicy(reviewed_only=True).cache_discriminator() == (
            "reviewed=1|codes=*|norefs=*"
        )
        assert DonorPolicy(evidence_codes=["IDA", "EXP"]).cache_discriminator() == (
            "reviewed=0|codes=EXP,IDA|norefs=*"
        )

    def test_an_unset_membership_dumps_what_a_policy_dumped_before(self) -> None:
        # The dump is recorded on every prediction set and compared by the
        # method seal, so a permissive policy must not grow a key.
        before: dict[str, object] = {
            "reviewed_only": False,
            "evidence_codes": None,
            "exclude_reference_prefixes": [],
        }
        assert DonorPolicy().model_dump() == before
        assert DonorPolicy().model_dump(mode="json") == before

    def test_a_set_membership_is_in_the_dump(self) -> None:
        assert DonorPolicy(admitted_by_release=211).model_dump()["admitted_by_release"] == 211

    def test_the_dump_round_trips(self) -> None:
        for policy in (DonorPolicy(), DonorPolicy(admitted_by_release=211, reviewed_only=True)):
            assert DonorPolicy.model_validate(policy.model_dump(mode="json")) == policy

    def test_a_release_below_one_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            DonorPolicy(admitted_by_release=0)

    def test_it_travels_on_the_batch_payload(self) -> None:
        payload = PredictGOTermsBatchPayload.model_validate(
            {
                "embedding_config_id": "cfg",
                "annotation_set_id": "aset",
                "ontology_snapshot_id": "snap",
                "prediction_set_id": "pset",
                "parent_job_id": "job",
                "query_accessions": ["P00001"],
                "donor_policy": {"admitted_by_release": 211},
            }
        )
        assert payload.donor_policy.admitted_by_release == 211
        assert payload.model_dump(mode="json")["donor_policy"] == {
            "reviewed_only": False,
            "evidence_codes": None,
            "exclude_reference_prefixes": [],
            "admitted_by_release": 211,
        }
