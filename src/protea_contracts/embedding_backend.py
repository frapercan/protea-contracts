"""Contract for embedding backend plugins.

A plugin in ``protea-backends`` (e.g. ``esm``, ``t5``, ``ankh``,
``esm3c``) implements ``EmbeddingBackend`` and registers itself via
the ``protea.backends`` ``entry_points`` group. ``protea-core``
discovers the plugin at startup and dispatches embedding requests
by ``EmbeddingConfig.model_backend``.

Two output modes are supported:

* :meth:`embed_batch` returns a mean-pooled ``(B, D)`` ``float16``
  matrix. This is the historical entry-point, unchanged.
* :meth:`embed_batch_per_residue` returns an :class:`EmbeddingPayload`
  with ragged per-residue tensors plus matching attention masks. The
  base implementation raises ``NotImplementedError`` so backends opt
  in explicitly; ESM wires this in MIL.1a, the remaining backends in
  MIL.1b.

Example::

    import numpy as np
    from protea_contracts.embedding_backend import EmbeddingBackend

    class EsmBackend(EmbeddingBackend):
        name = "esm"

        def load_model(self, model_name, device, emit):
            from transformers import AutoModel, AutoTokenizer
            model = AutoModel.from_pretrained(model_name).to(device)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            return model, tokenizer

        def embed_batch(self, model, tokenizer, sequences, *, emit):
            ...
            return np.asarray(embeddings, dtype=np.float16)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from protea_contracts.embedding_payload import EmbeddingPayload


class EmbeddingBackend(ABC):
    """Contract for a plugin that materialises sequence embeddings.

    Implementations live in ``protea-backends``. The platform passes
    the resolved ``EmbeddingConfig`` (model name, layers, pooling) as
    free-form kwargs and expects a half-precision matrix back from
    :meth:`embed_batch`, or an :class:`EmbeddingPayload` carrying
    ragged per-residue tensors from
    :meth:`embed_batch_per_residue`.
    """

    name: str
    """Stable string identifier used to match ``EmbeddingConfig.model_backend``."""

    @abstractmethod
    def load_model(
        self,
        model_name: str,
        device: str,
        emit: Any,
    ) -> tuple[Any, Any]:
        """Load (or fetch from cache) the model + tokenizer for this backend.

        Args:
            model_name: HuggingFace identifier or local path resolved by
                ``EmbeddingConfig.model_name``.
            device: e.g. ``"cuda:0"`` or ``"cpu"``.
            emit: structured-event callback.

        Returns:
            ``(model, tokenizer)`` pair. Types are ``Any`` here because
            ``protea-contracts`` does not depend on ``torch``.
        """
        raise NotImplementedError

    @abstractmethod
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
        """Run inference on a batch of sequences (mean-pool path).

        Args:
            model: returned by :meth:`load_model`.
            tokenizer: returned by :meth:`load_model`.
            sequences: amino-acid strings.
            emit: structured-event callback.
            layers: which transformer layers to extract; ``None`` means
                last layer only.
            layer_agg: aggregation across selected layers
                (``"mean"`` / ``"sum"`` / ``"concat"``).
            pooling: per-sequence aggregation across residues
                (``"mean"`` / ``"max"`` / ``"cls"``).

        Returns:
            ``(batch_size, dim)`` ``np.float16`` matrix.
        """
        raise NotImplementedError

    def embed_batch_per_residue(
        self,
        model: Any,
        tokenizer: Any,
        sequences: list[str],
        *,
        emit: Any,
        layers: list[int] | None = None,
    ) -> EmbeddingPayload:
        """Run inference and return per-residue embeddings (no pooling).

        Returns an :class:`EmbeddingPayload` with
        ``granularity="per_residue"`` carrying ``B`` ragged ``(L_i, D)``
        ``float16`` tensors and matching boolean attention masks (CLS
        and EOS already stripped by the backend so that index ``j`` in
        the residue tensor corresponds to the ``j``-th amino acid of
        ``sequences[i]``).

        Default implementation raises ``NotImplementedError``; concrete
        backends override it when they wire their per-residue path
        (ESM in MIL.1a; T5, Ankh, ESM-C in MIL.1b).

        Args:
            model: returned by :meth:`load_model`.
            tokenizer: returned by :meth:`load_model`.
            sequences: amino-acid strings.
            emit: structured-event callback.
            layers: which transformer layers to extract; ``None`` means
                last layer only. ``layer_agg`` is implicitly ``"mean"``
                in this contract; per-layer concatenation for
                per-residue output is a MIL.2 concern (multi-layer
                feature stacking).
        """
        raise NotImplementedError(
            f"Backend {self.name!r} does not implement embed_batch_per_residue; "
            "wire it in MIL.1b (see executor PLAN.md)."
        )
