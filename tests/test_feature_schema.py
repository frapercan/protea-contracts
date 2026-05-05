"""Tests for protea_contracts.feature_schema (T1.2).

Includes the golden test that pins the SHA of ALL_FEATURES so any
rename, reorder, or addition forces a SemVer major bump.
"""

from __future__ import annotations

import pytest

from protea_contracts import (
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


class TestConstants:
    def test_schema_version(self) -> None:
        assert SCHEMA_VERSION == "v2"

    def test_label_column(self) -> None:
        assert LABEL_COLUMN == "label"

    def test_embedding_pca_dim(self) -> None:
        assert EMBEDDING_PCA_DIM == 16

    def test_emb_pca_columns_match_dim(self) -> None:
        emb_pca_cols = [c for c in NUMERIC_FEATURES if c.startswith("emb_pca_query_")]
        assert len(emb_pca_cols) == EMBEDDING_PCA_DIM

    def test_all_features_is_numeric_plus_categorical(self) -> None:
        assert ALL_FEATURES == NUMERIC_FEATURES + CATEGORICAL_FEATURES

    def test_no_duplicates_in_all_features(self) -> None:
        assert len(ALL_FEATURES) == len(set(ALL_FEATURES))

    def test_label_in_reserved(self) -> None:
        assert LABEL_COLUMN in RESERVED_COLUMNS


class TestFeatureFamilies:
    def test_every_family_member_lives_in_all_features(self) -> None:
        all_set = set(ALL_FEATURES)
        for family, cols in FEATURE_FAMILIES.items():
            for col in cols:
                assert col in all_set, f"{family}.{col} missing from ALL_FEATURES"

    def test_emb_pca_family_size(self) -> None:
        assert len(FEATURE_FAMILIES["emb_pca"]) == EMBEDDING_PCA_DIM


class TestComputeSchemaSha:
    def test_golden_all_features(self) -> None:
        """Golden digest of ALL_FEATURES.

        Pinned: any change to NUMERIC_FEATURES or CATEGORICAL_FEATURES
        breaks this assertion and forces:
          1. A SemVer major bump on protea-contracts.
          2. Re-training of every downstream LightGBM booster.

        Update the literal below intentionally as part of the bump.
        """
        sha = compute_schema_sha(ALL_FEATURES)
        assert sha == "145592ed186c", (
            f"ALL_FEATURES sha drifted from golden: got {sha}. "
            "If this change is intended, bump protea-contracts to "
            "the next major and update this golden literal."
        )

    def test_order_invariant(self) -> None:
        a = compute_schema_sha(ALL_FEATURES)
        shuffled = list(reversed(ALL_FEATURES))
        b = compute_schema_sha(shuffled)
        assert a == b

    def test_membership_sensitive(self) -> None:
        a = compute_schema_sha(ALL_FEATURES)
        b = compute_schema_sha([*ALL_FEATURES, "fake_extra"])
        assert a != b

    def test_returns_12_hex_chars(self) -> None:
        sha = compute_schema_sha(["a", "b"])
        assert len(sha) == 12
        int(sha, 16)  # raises if not hex


class TestComputeFeatureSchemaSha:
    def test_family_order_invariant(self) -> None:
        a = compute_feature_schema_sha(["knn", "alignment_nw"])
        b = compute_feature_schema_sha(["alignment_nw", "knn"])
        assert a == b

    def test_drop_changes_sha(self) -> None:
        a = compute_feature_schema_sha(["knn"])
        b = compute_feature_schema_sha(["knn"], drop=["distance"])
        assert a != b

    def test_unknown_family_raises(self) -> None:
        with pytest.raises(KeyError):
            compute_feature_schema_sha(["does_not_exist"])

    def test_returns_12_hex_chars(self) -> None:
        sha = compute_feature_schema_sha(["knn"])
        assert len(sha) == 12
        int(sha, 16)


class TestRequiredColumns:
    def test_default_includes_reserved_and_all_features(self) -> None:
        cols = required_columns()
        assert RESERVED_COLUMNS[0] in cols
        assert ALL_FEATURES[0] in cols

    def test_drop_excludes(self) -> None:
        cols = required_columns(drop=["distance"])
        assert "distance" not in cols
        # other reserved still present
        assert "protein_accession" in cols

    def test_family_filter(self) -> None:
        cols = required_columns(families=["knn"])
        # reserved always included
        assert "protein_accession" in cols
        assert "distance" in cols
        # alignment family not included
        assert "identity_nw" not in cols

    def test_unknown_family_raises(self) -> None:
        with pytest.raises(KeyError):
            required_columns(families=["does_not_exist"])

    def test_no_duplicates_in_output(self) -> None:
        cols = required_columns()
        assert len(cols) == len(set(cols))
