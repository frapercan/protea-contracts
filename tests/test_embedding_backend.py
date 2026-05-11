"""Tests for the EmbeddingBackend ABC."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from protea_contracts import EmbeddingBackend, EmbeddingPayload


class _FakeBackend(EmbeddingBackend):
    """Minimal in-memory backend used to exercise the contract."""

    name = "fake"

    def load_model(self, model_name: str, device: str, emit: Any) -> tuple[Any, Any]:
        return ("model", "tokenizer")

    def embed_batch(
        self,
        model: Any,
        tokenizer: Any,
        sequences: list[str],
        *,
        emit: Any,
        layers: list[int] | None = None,
        layer_agg: str = "mean",
        pooling: str = "mean",
    ) -> np.ndarray[Any, Any]:
        return np.zeros((len(sequences), 8), dtype=np.float16)

    def embed_batch_per_residue(
        self,
        model: Any,
        tokenizer: Any,
        sequences: list[str],
        *,
        emit: Any,
        layers: list[int] | None = None,
    ) -> EmbeddingPayload:
        residues = [
            np.zeros((max(len(s), 1), 8), dtype=np.float16) for s in sequences
        ]
        masks = [np.ones((r.shape[0],), dtype=bool) for r in residues]
        return EmbeddingPayload(
            granularity="per_residue",
            residues=residues,
            attention_mask=masks,
        )


class _MeanOnlyBackend(EmbeddingBackend):
    """Backend that has not wired per-residue (matches T5/Ankh/ESM-C state)."""

    name = "mean_only"

    def load_model(self, model_name: str, device: str, emit: Any) -> tuple[Any, Any]:
        return ("model", None)

    def embed_batch(
        self,
        model: Any,
        tokenizer: Any,
        sequences: list[str],
        *,
        emit: Any,
        layers: list[int] | None = None,
        layer_agg: str = "mean",
        pooling: str = "mean",
    ) -> np.ndarray[Any, Any]:
        return np.zeros((len(sequences), 4), dtype=np.float16)


class TestEmbeddingBackendContract:
    def test_subclass_must_implement_both_methods(self) -> None:
        class Incomplete(EmbeddingBackend):
            name = "incomplete"

            def load_model(self, model_name: str, device: str, emit: Any) -> tuple[Any, Any]:
                return ("m", "t")

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_returns_float16_matrix(self) -> None:
        backend = _FakeBackend()
        model, tokenizer = backend.load_model("m", "cpu", emit=lambda *a, **kw: None)
        out = backend.embed_batch(
            model, tokenizer, ["MSEQ", "QSEQ", "ASEQ"], emit=lambda *a, **kw: None
        )
        assert isinstance(out, np.ndarray)
        assert out.shape == (3, 8)
        assert out.dtype == np.float16

    def test_optional_kwargs_have_defaults(self) -> None:
        backend = _FakeBackend()
        # Don't pass layers / layer_agg / pooling: defaults must work.
        out = backend.embed_batch(
            "m", "t", ["MSEQ"], emit=lambda *a, **kw: None
        )
        assert isinstance(out, np.ndarray)
        assert out.shape == (1, 8)

    def test_per_residue_returns_embedding_payload(self) -> None:
        backend = _FakeBackend()
        out = backend.embed_batch_per_residue(
            "m",
            "t",
            ["MSEQ", "GG"],
            emit=lambda *a, **kw: None,
        )
        assert isinstance(out, EmbeddingPayload)
        assert out.granularity == "per_residue"
        assert out.residues is not None and len(out.residues) == 2
        assert out.attention_mask is not None and len(out.attention_mask) == 2
        assert out.residues[0].shape == (4, 8)
        assert out.residues[1].shape == (2, 8)

    def test_per_residue_default_raises_not_implemented(self) -> None:
        backend = _MeanOnlyBackend()
        with pytest.raises(NotImplementedError, match=r"MIL\.1b"):
            backend.embed_batch_per_residue(
                "m", None, ["MSEQ"], emit=lambda *a, **kw: None
            )
