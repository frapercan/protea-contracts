"""Tests for the EmbeddingBackend ABC."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from protea_contracts import EmbeddingBackend


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
        assert out.shape == (3, 8)
        assert out.dtype == np.float16

    def test_optional_kwargs_have_defaults(self) -> None:
        backend = _FakeBackend()
        # Don't pass layers / layer_agg / pooling: defaults must work.
        out = backend.embed_batch(
            "m", "t", ["MSEQ"], emit=lambda *a, **kw: None
        )
        assert out.shape == (1, 8)
