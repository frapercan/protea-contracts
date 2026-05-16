"""Tests for the canonical axis-tuple shortid helper (FARM-EXP.1).

The helper is consumed by PROTEA (ExperimentRun row identity) and by
protea-reranker-lab (cell catalog membership). Both callers must agree
on the byte-for-byte formula or row joins break silently, so the golden
vector here is load-bearing.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from protea_contracts import (
    CANONICAL_AXIS_KEYS,
    SHORTID_HEX_LEN,
    axis_tuple_shortid,
)
from protea_contracts.axis_tuple import axis_tuple_shortid as direct_import

# ---------------------------------------------------------------- format


def test_returns_lowercase_hex_of_fixed_length() -> None:
    out = axis_tuple_shortid({"plm": "esm2_t33", "k": 5})
    assert re.fullmatch(r"[0-9a-f]{12}", out)
    assert len(out) == SHORTID_HEX_LEN


def test_top_level_export_matches_module_export() -> None:
    payload = {"plm": "esm2_t33", "k": 5}
    assert axis_tuple_shortid(payload) == direct_import(payload)


# ---------------------------------------------------------------- canon


def test_canonical_axis_keys_matches_orm_spec() -> None:
    # FARM-EXP.1 acceptance: PROTEA ExperimentRun gains exactly these
    # columns. The CANONICAL_AXIS_KEYS tuple pins the documented set.
    assert CANONICAL_AXIS_KEYS == (
        "plm",
        "k",
        "reranker_spec_id",
        "feature_schema_sha",
        "eval_set_name",
        "eval_set_manifest_sha",
        "propagation",
        "ensemble_spec",
    )


# ---------------------------------------------------------------- stable


def test_golden_vector_pins_the_formula() -> None:
    # If you change this expected digest, you have broken the cross-repo
    # contract (PROTEA backfill + lab catalog will produce different
    # shortids for the same axis tuple). Bump protea-contracts MAJOR.
    payload = {
        "plm": "esm2_t33_650M",
        "k": 5,
        "reranker_spec_id": "lgbm-v6",
        "feature_schema_sha": "0123456789ab",
        "eval_set_name": "bench-v1-K5-v226",
        "eval_set_manifest_sha": "cafe1234beef",
        "propagation": "none",
        "ensemble_spec": None,
    }
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:12]
    assert axis_tuple_shortid(payload) == expected


def test_order_invariance() -> None:
    # json.dumps(sort_keys=True) canonicalises, so any input ordering
    # must yield the same digest.
    a = {"k": 5, "plm": "esm2"}
    b = {"plm": "esm2", "k": 5}
    assert axis_tuple_shortid(a) == axis_tuple_shortid(b)


def test_stability_across_calls() -> None:
    payload = {"plm": "esm2", "k": 5, "feature_schema_sha": "abc123"}
    first = axis_tuple_shortid(payload)
    second = axis_tuple_shortid(payload)
    third = axis_tuple_shortid(dict(payload))
    assert first == second == third


def test_value_sensitivity() -> None:
    # Changing any value flips the digest. This is the security
    # invariant: a benchmark cell with k=5 must not be confused with
    # k=10 because they got the same shortid.
    base = {"plm": "esm2", "k": 5}
    assert axis_tuple_shortid(base) != axis_tuple_shortid({"plm": "esm2", "k": 10})
    assert axis_tuple_shortid(base) != axis_tuple_shortid({"plm": "esm3", "k": 5})


def test_none_values_are_distinct_from_missing_keys() -> None:
    # JSON serialises None as null; an absent key drops from the dict.
    # So {"a": None} and {} must produce different shortids.
    a = axis_tuple_shortid({"propagation": None})
    b = axis_tuple_shortid({})
    assert a != b


# ---------------------------------------------------------------- errors


def test_unencodable_value_raises_typeerror() -> None:
    # A non-JSON-encodable value (e.g. a Path or a set) must raise so
    # the caller pre-stringifies, mirroring the lab
    # ``ExperimentSpec.model_dump(mode="json")`` step.
    with pytest.raises(TypeError, match="JSON-encodable"):
        axis_tuple_shortid({"plm": {1, 2, 3}})  # type: ignore[dict-item]


def test_accepts_mapping_not_just_dict() -> None:
    # The signature accepts Mapping[str, Any]; verify a non-dict mapping
    # works (defensive: callers in PROTEA build the payload row-by-row).
    from types import MappingProxyType

    view = MappingProxyType({"plm": "esm2", "k": 5})
    out = axis_tuple_shortid(view)
    assert re.fullmatch(r"[0-9a-f]{12}", out)


# ---------------------------------------------------------------- lab xref


def test_mirrors_experimentspec_hash_formula() -> None:
    # The lab ExperimentSpec.hash() at
    # protea-reranker-lab/src/protea_reranker_lab/experiment.py:108-111
    # uses sha256(json.dumps(payload, sort_keys=True))[:12]. This test
    # constructs a payload-shaped dict and checks the helper matches a
    # hand-rolled invocation of that exact formula.
    payload = {
        "schema_version": "v1",
        "name": "lgbm-v6-bench",
        "dataset": {"manifest": "/tmp/m.parquet"},
        "model": {"kind": "lgbm_reranker", "defaults": {}},
        "training": {
            "cell": "bp",
            "val_strategy": "temporal",
            "val_fraction": 0.2,
            "val_holdout_snapshot": "v226",
            "seed": 42,
            "propagate_labels": False,
            "neg_pos_ratio": None,
        },
        "sweep": {"backend": "none", "project": None, "config": None},
        "keep_staging": False,
    }
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:12]
    assert axis_tuple_shortid(payload) == expected
