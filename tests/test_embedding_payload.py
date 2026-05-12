"""Tests for the EmbeddingPayload contract (MIL.1a).

Covers the granularity ↔ shape invariants enforced by the pydantic
validator. The contract is consumed by the ``protea-backends``
plugins (ESM in MIL.1a; T5, Ankh, ESM-C in MIL.1b) and by downstream
MIL pooling heads in PROTEA.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from protea_contracts import EmbeddingPayload, Granularity


class TestMeanPoolPayload:
    def test_minimal_valid_matrix(self) -> None:
        emb = np.zeros((3, 8), dtype=np.float16)
        p = EmbeddingPayload(granularity="mean_pool", embeddings=emb)
        assert p.granularity == "mean_pool"
        assert p.embeddings is emb
        assert p.residues is None
        assert p.attention_mask is None

    def test_default_granularity_is_mean_pool(self) -> None:
        p = EmbeddingPayload(embeddings=np.zeros((1, 4), dtype=np.float16))
        assert p.granularity == "mean_pool"

    def test_rejects_non_ndarray(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(granularity="mean_pool", embeddings=[[1.0, 2.0]])

    def test_rejects_non_2d_matrix(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="mean_pool",
                embeddings=np.zeros((3,), dtype=np.float16),
            )

    def test_rejects_residues_on_mean_pool(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="mean_pool",
                embeddings=np.zeros((1, 4), dtype=np.float16),
                residues=[np.zeros((5, 4), dtype=np.float16)],
            )


class TestPerResiduePayload:
    def _good_payload(self) -> EmbeddingPayload:
        residues = [
            np.zeros((5, 8), dtype=np.float16),
            np.zeros((3, 8), dtype=np.float16),
        ]
        masks = [np.ones((5,), dtype=bool), np.ones((3,), dtype=bool)]
        return EmbeddingPayload(
            granularity="per_residue",
            residues=residues,
            attention_mask=masks,
        )

    def test_valid_per_residue(self) -> None:
        p = self._good_payload()
        assert p.granularity == "per_residue"
        assert p.embeddings is None
        assert isinstance(p.residues, list) and len(p.residues) == 2
        assert isinstance(p.attention_mask, list) and len(p.attention_mask) == 2

    def test_residues_must_be_2d(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="per_residue",
                residues=[np.zeros((5,), dtype=np.float16)],
                attention_mask=[np.ones((5,), dtype=bool)],
            )

    def test_mask_must_be_1d(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="per_residue",
                residues=[np.zeros((5, 8), dtype=np.float16)],
                attention_mask=[np.ones((5, 1), dtype=bool)],
            )

    def test_residue_and_mask_lengths_must_match(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="per_residue",
                residues=[np.zeros((5, 8), dtype=np.float16)],
                attention_mask=[np.ones((4,), dtype=bool)],
            )

    def test_list_lengths_must_match(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="per_residue",
                residues=[np.zeros((5, 8), dtype=np.float16)],
                attention_mask=[
                    np.ones((5,), dtype=bool),
                    np.ones((3,), dtype=bool),
                ],
            )

    def test_rejects_embeddings_matrix_on_per_residue(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="per_residue",
                embeddings=np.zeros((2, 8), dtype=np.float16),
                residues=[np.zeros((5, 8), dtype=np.float16)],
                attention_mask=[np.ones((5,), dtype=bool)],
            )

    def test_requires_lists_not_arrays(self) -> None:
        # Passing a single ndarray instead of a list of ndarrays should
        # fail loud rather than silently iterating row-wise.
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="per_residue",
                residues=np.zeros((2, 5, 8), dtype=np.float16),  # not a list
                attention_mask=[np.ones((5,), dtype=bool)],
            )


class TestAsMatrix:
    def test_mean_pool_returns_matrix_unchanged(self) -> None:
        emb = np.arange(12, dtype=np.float16).reshape(3, 4)
        p = EmbeddingPayload(granularity="mean_pool", embeddings=emb)
        out = p.as_matrix()
        assert out is emb

    def test_per_residue_collapses_to_mean(self) -> None:
        residues = [
            np.array([[1, 2], [3, 4]], dtype=np.float16),
            np.array([[5, 6], [7, 8], [9, 10]], dtype=np.float16),
        ]
        masks = [np.ones((2,), dtype=bool), np.ones((3,), dtype=bool)]
        p = EmbeddingPayload(
            granularity="per_residue",
            residues=residues,
            attention_mask=masks,
        )
        out = p.as_matrix()
        assert out.shape == (2, 2)
        assert out.dtype == np.float16
        # Row 0: mean of [[1,2],[3,4]] = [2, 3]
        # Row 1: mean of [[5,6],[7,8],[9,10]] = [7, 8]
        assert np.allclose(out, np.array([[2, 3], [7, 8]], dtype=np.float16))


class TestGranularityLiteral:
    def test_invalid_granularity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingPayload(
                granularity="token",  # type: ignore[arg-type]
                embeddings=np.zeros((1, 4), dtype=np.float16),
            )

    def test_granularity_type_alias_exports(self) -> None:
        # Smoke check that the type alias is importable and Literal-ish.
        # (We can't assert get_args(Granularity) easily across pythons,
        # but importing it without an AttributeError is enough.)
        assert Granularity is not None
