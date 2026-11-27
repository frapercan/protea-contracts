"""The donor policy: who may donate annotations, and how it reaches a cache key.

The pool used to be defined only as "has a representation under this
configuration" and "has some annotation in this set". These tests pin the two
properties that make adding a policy safe: an unset policy behaves exactly as
before, and a set one changes the cache key so a pool built under one policy
can never be served for another.
"""

from __future__ import annotations

import json
from typing import get_args

import pytest
from pydantic import ValidationError

from protea_contracts.payloads import (
    DonorPolicy,
    EvidenceChannel,
    PredictGOTermsBatchPayload,
    PredictGOTermsPayload,
)

_PREDICT: dict[str, object] = {
    "embedding_config_id": "cfg",
    "annotation_set_id": "aset",
    "ontology_snapshot_id": "snap",
}
_BATCH: dict[str, object] = {
    **_PREDICT,
    "prediction_set_id": "pset",
    "parent_job_id": "job",
    "query_accessions": ["P00001"],
}
_Predict = type[PredictGOTermsPayload] | type[PredictGOTermsBatchPayload]
_BOTH_PAYLOADS = pytest.mark.parametrize(
    ("model", "body"),
    [(PredictGOTermsPayload, _PREDICT), (PredictGOTermsBatchPayload, _BATCH)],
    ids=["predict", "batch"],
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


#: Policies as the code before this release dumped and keyed them: the literals
#: are what version 1.7.0 (commit dafcde5) printed for each body. A policy
#: recorded before 1.8.0 must dump and key exactly the same, or every stored arm
#: stops matching its own record and every cached pool loses its key.
_RECORDED_BEFORE_THE_DONOR_SET: list[tuple[dict[str, object], str, str]] = [
    (
        {},
        '{"reviewed_only":false,"evidence_codes":null,"exclude_reference_prefixes":[]}',
        "",
    ),
    (
        {"reviewed_only": True},
        '{"reviewed_only":true,"evidence_codes":null,"exclude_reference_prefixes":[]}',
        "reviewed=1|codes=*|norefs=*",
    ),
    (
        {"evidence_codes": ["IDA", "EXP"]},
        '{"reviewed_only":false,"evidence_codes":["IDA","EXP"],"exclude_reference_prefixes":[]}',
        "reviewed=0|codes=EXP,IDA|norefs=*",
    ),
    (
        {"exclude_reference_prefixes": ["GO_REF:0000104", "GO_REF:0000002"]},
        '{"reviewed_only":false,"evidence_codes":null,'
        '"exclude_reference_prefixes":["GO_REF:0000104","GO_REF:0000002"]}',
        "reviewed=0|codes=*|norefs=GO_REF:0000002,GO_REF:0000104",
    ),
    (
        {"admitted_by_release": 211},
        '{"reviewed_only":false,"evidence_codes":null,"exclude_reference_prefixes":[],'
        '"admitted_by_release":211}',
        "reviewed=0|codes=*|norefs=*|admitted<=211",
    ),
    (
        {
            "evidence_codes": ["EXP", "IDA", "IPI", "IMP", "IGI", "IEP", "TAS", "IC"],
            "exclude_reference_prefixes": ["GO_REF:0000002"],
            "admitted_by_release": 211,
        },
        '{"reviewed_only":false,"evidence_codes":["EXP","IDA","IPI","IMP","IGI","IEP","TAS",'
        '"IC"],"exclude_reference_prefixes":["GO_REF:0000002"],"admitted_by_release":211}',
        "reviewed=0|codes=EXP,IC,IDA,IEP,IGI,IMP,IPI,TAS|norefs=GO_REF:0000002|admitted<=211",
    ),
    (
        {
            "reviewed_only": True,
            "evidence_codes": ["IEA", "EXP"],
            "exclude_reference_prefixes": ["GO_REF:0000002"],
            "admitted_by_release": 194,
        },
        '{"reviewed_only":true,"evidence_codes":["IEA","EXP"],'
        '"exclude_reference_prefixes":["GO_REF:0000002"],"admitted_by_release":194}',
        "reviewed=1|codes=EXP,IEA|norefs=GO_REF:0000002|admitted<=194",
    ),
]
_RECORDED = pytest.mark.parametrize(
    ("body", "dump", "key"),
    _RECORDED_BEFORE_THE_DONOR_SET,
    ids=[
        "permissive",
        "reviewed",
        "codes",
        "prefixes",
        "membership",
        "experimental-codes-at-a-release",
        "every-older-field",
    ],
)

#: Every channel of PROTEA's partition, in its order.
_CHANNELS: tuple[EvidenceChannel, ...] = (
    "truth",
    "curated",
    "phylogenetic",
    "orthology_electronic",
    "reviewed_field_electronic",
    "signature_electronic",
    "no_data",
)


def _body_of(model: _Predict) -> dict[str, object]:
    """The smallest valid body of either predict payload."""
    return _PREDICT if model is PredictGOTermsPayload else _BATCH


class TestAPolicyRecordedBeforeTheDonorSetIsUntouched:
    """Release 1.8.0 adds two restrictions and moves no stored policy.

    The dump is recorded on every prediction set and compared field by field
    by the method seal, and the key names every cached pool. Both are checked
    against the literals version 1.7.0 produced, byte for byte.
    """

    @_RECORDED
    def test_it_dumps_byte_identical(self, body: dict[str, object], dump: str, key: str) -> None:
        assert DonorPolicy.model_validate(body).model_dump_json() == dump

    @_RECORDED
    def test_it_keeps_its_cache_key(self, body: dict[str, object], dump: str, key: str) -> None:
        assert DonorPolicy.model_validate(body).cache_discriminator() == key

    @_RECORDED
    def test_its_stored_dump_reads_back_to_the_same_bytes(
        self, body: dict[str, object], dump: str, key: str
    ) -> None:
        assert DonorPolicy.model_validate_json(dump).model_dump_json() == dump

    @_RECORDED
    def test_the_new_keys_sent_as_null_read_as_unset(
        self, body: dict[str, object], dump: str, key: str
    ) -> None:
        policy = DonorPolicy.model_validate(
            {**body, "donor_set_id": None, "evidence_channels": None}
        )
        assert policy.model_dump_json() == dump
        assert policy.cache_discriminator() == key

    @pytest.mark.parametrize(
        "model", [PredictGOTermsPayload, PredictGOTermsBatchPayload], ids=["predict", "batch"]
    )
    @_RECORDED
    def test_it_dumps_the_same_inside_a_payload(
        self, model: _Predict, body: dict[str, object], dump: str, key: str
    ) -> None:
        payload = model.model_validate({**_body_of(model), "donor_policy": body})
        assert payload.model_dump(mode="json")["donor_policy"] == json.loads(dump)
        assert payload.donor_policy.cache_discriminator() == key


class TestTheDonorSet:
    """``donor_set_id``: admit only the donors a declared set of photo members lists."""

    def test_it_is_unset_by_default(self) -> None:
        assert DonorPolicy().donor_set_id is None

    def test_setting_it_restricts_the_pool(self) -> None:
        assert DonorPolicy(donor_set_id="set-a").is_permissive is False

    def test_it_keys_its_own_cache(self) -> None:
        assert DonorPolicy(donor_set_id="set-a").cache_discriminator() == (
            "reviewed=0|codes=*|norefs=*|donors=set-a"
        )
        assert (
            DonorPolicy(donor_set_id="set-a").cache_discriminator()
            != DonorPolicy(donor_set_id="set-b").cache_discriminator()
        )

    def test_it_is_in_the_dump_once_set_and_out_of_it_while_unset(self) -> None:
        assert DonorPolicy(donor_set_id="set-a").model_dump()["donor_set_id"] == "set-a"
        assert "donor_set_id" not in DonorPolicy().model_dump(mode="json")

    @pytest.mark.parametrize("set_id", ["", "   "])
    def test_an_empty_id_is_refused(self, set_id: str) -> None:
        with pytest.raises(ValidationError, match="donor_set_id must be a non-empty string"):
            DonorPolicy(donor_set_id=set_id)

    def test_an_id_is_read_without_surrounding_spaces_as_the_other_ids_are(self) -> None:
        assert DonorPolicy(donor_set_id=" set-a ").cache_discriminator() == (
            DonorPolicy(donor_set_id="set-a").cache_discriminator()
        )

    def test_a_non_string_id_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            DonorPolicy.model_validate({"donor_set_id": 7})

    @_BOTH_PAYLOADS
    def test_it_survives_validation_on_both_payloads(
        self, model: _Predict, body: dict[str, object]
    ) -> None:
        payload = model.model_validate({**body, "donor_policy": {"donor_set_id": "set-a"}})
        assert payload.donor_policy.donor_set_id == "set-a"
        assert payload.donor_policy.is_permissive is False
        assert payload.model_dump(mode="json")["donor_policy"] == {
            "reviewed_only": False,
            "evidence_codes": None,
            "exclude_reference_prefixes": [],
            "donor_set_id": "set-a",
        }

    def test_the_dump_round_trips(self) -> None:
        policy = DonorPolicy(donor_set_id="set-a", admitted_by_release=211)
        assert DonorPolicy.model_validate(policy.model_dump(mode="json")) == policy
        assert DonorPolicy.model_validate_json(policy.model_dump_json()) == policy


class TestTheEvidenceChannels:
    """``evidence_channels``: admit only annotations whose channel at the cut is listed."""

    def test_it_is_unset_by_default(self) -> None:
        assert DonorPolicy().evidence_channels is None

    def test_the_vocabulary_is_the_partitions_seven_channels_in_order(self) -> None:
        assert get_args(EvidenceChannel) == _CHANNELS

    @pytest.mark.parametrize("channel", _CHANNELS)
    def test_every_channel_is_accepted_alone(self, channel: str) -> None:
        policy = DonorPolicy.model_validate({"evidence_channels": [channel]})
        assert policy.evidence_channels == [channel]
        assert policy.cache_discriminator() == f"reviewed=0|codes=*|norefs=*|channels={channel}"

    def test_setting_it_restricts_the_pool(self) -> None:
        assert DonorPolicy(evidence_channels=["truth"]).is_permissive is False

    def test_it_keys_its_own_cache(self) -> None:
        assert DonorPolicy(evidence_channels=["truth", "curated"]).cache_discriminator() == (
            "reviewed=0|codes=*|norefs=*|channels=curated,truth"
        )

    def test_the_key_does_not_depend_on_declaration_order(self) -> None:
        """Two orders of one list must not build two pools."""
        a = DonorPolicy(evidence_channels=["truth", "curated", "phylogenetic"])
        b = DonorPolicy(evidence_channels=["phylogenetic", "truth", "curated"])
        assert a.cache_discriminator() == b.cache_discriminator()

    def test_the_dump_keeps_the_order_it_was_given_as_the_codes_do(self) -> None:
        policy = DonorPolicy(evidence_channels=["truth", "curated"])
        assert policy.model_dump()["evidence_channels"] == ["truth", "curated"]

    def test_different_lists_get_different_keys(self) -> None:
        keys = {
            DonorPolicy(evidence_channels=["truth"]).cache_discriminator(),
            DonorPolicy(evidence_channels=["truth", "curated"]).cache_discriminator(),
            DonorPolicy(evidence_channels=list(_CHANNELS[:5])).cache_discriminator(),
            DonorPolicy(evidence_channels=list(_CHANNELS[:6])).cache_discriminator(),
        }
        assert len(keys) == 4

    def test_it_is_in_the_dump_once_set_and_out_of_it_while_unset(self) -> None:
        assert DonorPolicy(evidence_channels=["truth"]).model_dump()["evidence_channels"] == [
            "truth"
        ]
        assert "evidence_channels" not in DonorPolicy().model_dump(mode="json")

    def test_an_empty_list_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="at least one channel"):
            DonorPolicy(evidence_channels=[])

    def test_a_repeated_channel_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="lists truth more than once"):
            DonorPolicy(evidence_channels=["truth", "curated", "truth"])

    @pytest.mark.parametrize("channel", ["experimental", "Truth", "IEA", "signature", ""])
    def test_an_unknown_channel_is_refused(self, channel: str) -> None:
        with pytest.raises(ValidationError):
            DonorPolicy.model_validate({"evidence_channels": ["truth", channel]})

    def test_with_evidence_codes_both_restrictions_are_kept(self) -> None:
        policy = DonorPolicy(evidence_codes=["EXP"], evidence_channels=["truth"])
        assert policy.cache_discriminator() == "reviewed=0|codes=EXP|norefs=*|channels=truth"

    @_BOTH_PAYLOADS
    def test_it_survives_validation_on_both_payloads(
        self, model: _Predict, body: dict[str, object]
    ) -> None:
        payload = model.model_validate(
            {**body, "donor_policy": {"evidence_channels": ["truth", "curated"]}}
        )
        assert payload.donor_policy.evidence_channels == ["truth", "curated"]
        assert payload.donor_policy.is_permissive is False
        assert payload.model_dump(mode="json")["donor_policy"] == {
            "reviewed_only": False,
            "evidence_codes": None,
            "exclude_reference_prefixes": [],
            "evidence_channels": ["truth", "curated"],
        }

    def test_the_dump_round_trips(self) -> None:
        policy = DonorPolicy(evidence_channels=["truth", "curated"], reviewed_only=True)
        assert DonorPolicy.model_validate(policy.model_dump(mode="json")) == policy
        assert DonorPolicy.model_validate_json(policy.model_dump_json()) == policy


#: Each restriction of the policy, set alone.
_EACH_RESTRICTION_ALONE: dict[str, dict[str, object]] = {
    "reviewed": {"reviewed_only": True},
    "codes": {"evidence_codes": ["EXP"]},
    "prefixes": {"exclude_reference_prefixes": ["GO_REF:0000002"]},
    "membership": {"admitted_by_release": 211},
    "donor-set": {"donor_set_id": "set-a"},
    "channels": {"evidence_channels": ["truth"]},
}


class TestEveryRestrictionTogether:
    """The six restrictions, alone and together, each with a pool of its own."""

    @pytest.mark.parametrize("name", list(_EACH_RESTRICTION_ALONE))
    def test_each_alone_restricts_the_pool(self, name: str) -> None:
        policy = DonorPolicy.model_validate(_EACH_RESTRICTION_ALONE[name])
        assert policy.is_permissive is False

    def test_each_alone_keys_a_pool_of_its_own(self) -> None:
        keys = {
            DonorPolicy.model_validate(body).cache_discriminator()
            for body in _EACH_RESTRICTION_ALONE.values()
        }
        assert len(keys) == len(_EACH_RESTRICTION_ALONE)
        assert "" not in keys

    def test_together_they_key_in_a_fixed_order(self) -> None:
        policy = DonorPolicy(
            reviewed_only=True,
            evidence_codes=["IDA", "EXP"],
            exclude_reference_prefixes=["GO_REF:0000002"],
            admitted_by_release=211,
            donor_set_id="set-a",
            evidence_channels=["truth", "curated"],
        )
        assert policy.cache_discriminator() == (
            "reviewed=1|codes=EXP,IDA|norefs=GO_REF:0000002|admitted<=211"
            "|donors=set-a|channels=curated,truth"
        )
        assert DonorPolicy.model_validate_json(policy.model_dump_json()) == policy
