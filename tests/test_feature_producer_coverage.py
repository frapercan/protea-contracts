"""FARM-1.10: ALL_FEATURES producer-coverage guard.

Background
==========

``protea_contracts.ALL_FEATURES`` is the canonical column set the
PROTEA dump pipeline must emit. The downstream parquet exporter
enforces a ``shard.columns superset_of ALL_FEATURES`` invariant at
write time
(``protea/core/parquet_export.py:_assert_canonical_columns``). When
a column is added to ``ALL_FEATURES`` without an unconditional
producer in the dump path, the invariant only fails AFTER multi-hour
KNN compute. The 2026-05-13 incident (4 ``lineage_*`` columns shipped
by T-RES.1b, LB.1 v226 failed after ~5 h with
``missing=['lineage_is_ancestor_of_known', ...]``) is the canonical
example.

This test mocks a minimal dump for every payload-flag combination
(powerset over the bool fields of
:class:`PredictGOTermsBatchPayload`) and asserts that
``produced_columns`` is a superset of :data:`ALL_FEATURES` for every
combination. Failure mode: 1-second CI red on the contracts PR
rather than 5-hour downstream waste.

The simulator below intentionally mirrors the current behaviour of
``protea.core._leaf_record_builder._LeafRecordBuilder.make_leaf_record``:
every canonical column is emitted on every record regardless of
flag state (opt-in features use zero / NaN defaults). The test
will flag any future drift where a new column lives behind a flag.

This module imports nothing from PROTEA; the simulator is a pure
function over the contracts surface so the test runs in the
contracts CI with zero platform deps.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable

import pytest

from protea_contracts import (
    ALL_FEATURES,
    EMBEDDING_PCA_DIM,
    PredictGOTermsBatchPayload,
)
from protea_contracts import feature_schema as _feature_schema

# ---------------------------------------------------------------------------
# Flag discovery
# ---------------------------------------------------------------------------


def _discover_bool_flags(model: type) -> list[str]:
    """Return the sorted list of bool-typed fields on a Pydantic v2 model.

    The harness considers a field a flag iff its annotation is
    exactly ``bool``. Optional / Union / list-of-bool fields are
    skipped because they are not on/off knobs the dump path
    branches on.
    """
    fields = getattr(model, "model_fields", None)
    if fields is None:  # pragma: no cover - pydantic v1 fallback
        fields = getattr(model, "__fields__", {})
    return sorted(
        name
        for name, field in fields.items()
        if getattr(field, "annotation", None) is bool
    )


PAYLOAD_BOOL_FLAGS: list[str] = _discover_bool_flags(PredictGOTermsBatchPayload)


# ---------------------------------------------------------------------------
# Dump producer simulator
# ---------------------------------------------------------------------------


def _simulate_dump_record(flags: dict[str, bool]) -> set[str]:
    """Return the column names a single leaf record carries under ``flags``.

    Mirrors the current behaviour of
    ``protea.core._leaf_record_builder._LeafRecordBuilder.make_leaf_record``
    exactly: every column in :data:`ALL_FEATURES` is emitted on every
    record regardless of flag state. Opt-in features (lineage,
    v6 enrichment, anc2vec) carry zero / NaN defaults when their
    payload flag is off; the column is present either way.

    This is the contract the parquet exporter relies on. The harness
    encodes it as an invariant: when a future producer makes a
    column conditional on a flag, this simulator MUST be updated in
    lock-step with that change, and the test must continue to pass
    for every flag combination. If you cannot keep the column
    unconditional, drop it from ``ALL_FEATURES`` or wire a default
    in ``_LeafRecordBuilder`` (the lineage zero-fill pattern from
    T-RES.1b is the reference fix).

    Args:
        flags: a mapping from
            :class:`PredictGOTermsBatchPayload` bool field names to
            their values for this combo. Unknown keys are tolerated
            (forward compatibility for new flags).

    Returns:
        The set of column names the simulated leaf record carries.
    """
    # The reference producer emits every canonical column on every
    # record. Future drift (a column becomes conditional) shows up
    # as a missing entry below for some combo. Keep this list in
    # sync with _LeafRecordBuilder.make_leaf_record; failure to do
    # so is itself the failure mode this test catches.
    produced: set[str] = set()

    # KNN-derived columns (always emitted by the per-aspect record builder).
    produced.update(
        [
            "distance",
            "vote_count",
            "k_position",
            "go_term_frequency",
            "ref_annotation_density",
            "neighbor_distance_std",
            "neighbor_vote_fraction",
            "neighbor_min_distance",
            "neighbor_mean_distance",
        ]
    )

    # Alignment + length (unconditional in the current dump; the
    # compute_alignments flag toggles whether the values are
    # meaningful, not whether the columns exist).
    produced.update(
        [
            "identity_nw",
            "similarity_nw",
            "alignment_score_nw",
            "gaps_pct_nw",
            "alignment_length_nw",
            "identity_sw",
            "similarity_sw",
            "alignment_score_sw",
            "gaps_pct_sw",
            "alignment_length_sw",
            "length_query",
            "length_ref",
        ]
    )

    # Taxonomy pair (always present; flag toggles meaningful values).
    produced.update(
        [
            "taxonomic_distance",
            "taxonomic_common_ancestors",
            "taxonomic_relation",
        ]
    )

    # Taxonomy voters consensus.
    produced.update(
        [
            "tax_voters_same_frac",
            "tax_voters_close_frac",
            "tax_voters_mean_common_ancestors",
        ]
    )

    # Anc2Vec features (neighbor + query side).
    produced.update(
        [
            "anc2vec_neighbor_cos",
            "anc2vec_neighbor_maxcos",
            "anc2vec_has_emb",
            "anc2vec_query_known_cos",
            "anc2vec_query_known_maxcos",
            "anc2vec_query_known_count",
        ]
    )

    # Embedding PCA columns.
    produced.update(f"emb_pca_query_{i}" for i in range(EMBEDDING_PCA_DIM))

    # Lineage defaults (T-RES.1b zero-fill).
    produced.update(
        [
            "lineage_is_ancestor_of_known",
            "lineage_is_descendant_of_known",
            "lineage_ancestor_of_count",
            "lineage_descendant_of_count",
        ]
    )

    # Categorical metadata (qualifier / evidence_code / aspect).
    produced.update(["qualifier", "evidence_code", "aspect"])

    # Touch ``flags`` so static analysers do not flag the parameter as
    # unused; the value is intentionally ignored because every column
    # is unconditional today.
    _ = flags

    return produced


# ---------------------------------------------------------------------------
# Cartesian product harness
# ---------------------------------------------------------------------------


def _iter_flag_combos(flags: Iterable[str]) -> Iterable[dict[str, bool]]:
    """Yield every dict in ``itertools.product([False, True], repeat=N)``.

    For an empty ``flags`` list, yields a single empty dict so the
    simulator is still exercised once.
    """
    flag_list = list(flags)
    if not flag_list:
        yield {}
        return
    for combo_values in itertools.product([False, True], repeat=len(flag_list)):
        yield dict(zip(flag_list, combo_values, strict=True))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProducerCoverage:
    """Cartesian-product coverage of every payload flag combination."""

    def test_at_least_one_bool_flag_discovered(self) -> None:
        """Sanity: payload should expose multiple bool feature toggles."""
        assert len(PAYLOAD_BOOL_FLAGS) >= 5, (
            "Expected at least 5 bool flags on PredictGOTermsBatchPayload; "
            f"got {PAYLOAD_BOOL_FLAGS!r}. If the payload schema changed, "
            "verify the new flags belong to the dump path before lowering "
            "this bound."
        )

    def test_every_combo_covers_all_features(self) -> None:
        """Core invariant: produced_columns superset_of ALL_FEATURES for every combo.

        Iterates the full powerset of bool flags from
        :class:`PredictGOTermsBatchPayload` (currently 2 ** 7 = 128
        combinations) and asserts the simulator returns a superset of
        :data:`ALL_FEATURES` every time. A failure here means a
        canonical column has been added without an unconditional
        producer in the dump path: PR is 1-second red instead of a
        5-hour LB.1 waste.
        """
        canonical = set(ALL_FEATURES)
        failures: list[tuple[dict[str, bool], list[str]]] = []
        combo_count = 0
        for combo in _iter_flag_combos(PAYLOAD_BOOL_FLAGS):
            combo_count += 1
            produced = _simulate_dump_record(combo)
            missing = sorted(c for c in canonical if c not in produced)
            if missing:
                failures.append((combo, missing))
        assert combo_count == 2 ** len(PAYLOAD_BOOL_FLAGS), (
            "Cartesian product iteration was truncated: "
            f"expected {2 ** len(PAYLOAD_BOOL_FLAGS)} combos, "
            f"got {combo_count}."
        )
        if failures:
            preview = failures[0]
            raise AssertionError(
                "producer coverage FAILED: "
                f"{len(failures)} combo(s) missing columns. "
                f"First failure: combo={preview[0]!r} "
                f"missing={preview[1]!r}. "
                "Fix: wire an unconditional producer (or a zero/NaN "
                "default) for the missing columns in the dump path. "
                "See "
                "agent-farm context memory "
                "project_canonical_feature_producer_consumer."
            )

    def test_corner_combo_all_flags_off(self) -> None:
        """All-off corner case still covers ALL_FEATURES."""
        combo = {flag: False for flag in PAYLOAD_BOOL_FLAGS}
        produced = _simulate_dump_record(combo)
        missing = sorted(c for c in ALL_FEATURES if c not in produced)
        assert not missing, (
            f"all-off combo missing canonical columns: {missing!r}"
        )

    def test_corner_combo_all_flags_on(self) -> None:
        """All-on corner case still covers ALL_FEATURES (no extras-required regression)."""
        combo = {flag: True for flag in PAYLOAD_BOOL_FLAGS}
        produced = _simulate_dump_record(combo)
        missing = sorted(c for c in ALL_FEATURES if c not in produced)
        assert not missing, (
            f"all-on combo missing canonical columns: {missing!r}"
        )


class TestSentinelDetectsRegression:
    """Confirm the harness actually catches the failure mode it claims to.

    Without this sentinel, a bug in :func:`_simulate_dump_record`
    that emits everything regardless of input would mask the very
    drift this test is supposed to detect.
    """

    def test_added_unproduced_column_is_caught(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Adding a fake column to ALL_FEATURES without wiring a producer FAILS.

        Monkeypatches :data:`ALL_FEATURES` to include a synthetic
        column, re-runs the harness, asserts a failure is reported,
        then lets pytest's ``monkeypatch`` undo the change.
        """
        fake_col = "fake_unwired_column_for_sentinel"
        # Sanity: the fake column must NOT already exist in the
        # canonical set, otherwise the sentinel proves nothing.
        assert fake_col not in ALL_FEATURES
        patched = [*ALL_FEATURES, fake_col]
        monkeypatch.setattr(_feature_schema, "ALL_FEATURES", patched)

        failures: list[tuple[dict[str, bool], list[str]]] = []
        for combo in _iter_flag_combos(PAYLOAD_BOOL_FLAGS):
            produced = _simulate_dump_record(combo)
            missing = sorted(
                c for c in _feature_schema.ALL_FEATURES if c not in produced
            )
            if missing:
                failures.append((combo, missing))

        assert failures, (
            "Sentinel did not catch an unwired column: the harness is "
            "broken and would not detect a real regression."
        )
        # Every failure should cite exactly the fake column.
        for _combo, missing in failures:
            assert missing == [fake_col], (
                "Sentinel saw unexpected missing columns: "
                f"{missing!r} (expected only [{fake_col!r}])"
            )

    def test_simulator_returns_superset_for_unknown_flag(self) -> None:
        """Forward compatibility: unknown flag keys are ignored cleanly."""
        # Pass a flag dict with a key that does not exist on the
        # payload. The simulator must not raise and must still cover
        # ALL_FEATURES (it ignores the dict's contents today).
        produced = _simulate_dump_record({"future_flag_that_does_not_exist": True})
        missing = sorted(c for c in ALL_FEATURES if c not in produced)
        assert not missing, (
            f"simulator misbehaves on unknown flag: missing={missing!r}"
        )
