"""Embedding output payload: mean-pool vs per-residue granularity.

The :class:`EmbeddingPayload` type is what an
:class:`protea_contracts.EmbeddingBackend` returns from
``embed_batch`` when the caller asks for richer (per-residue) output
than the historical ``(B, D)`` mean-pooled matrix.

Two granularities are supported:

* ``"mean_pool"`` (default, retro-compat): ``embeddings`` is a single
  ``(B, D)`` float16 ndarray, one row per input sequence. ``residues``
  and ``attention_mask`` are ``None``. Existing callers that expect
  the matrix can keep using :func:`as_matrix` or read
  ``payload.embeddings`` directly.

* ``"per_residue"``: ``residues`` is a list of ``B`` float16 ndarrays,
  one per input sequence, each shaped ``(L_i, D)`` after CLS/EOS
  stripping. ``attention_mask`` is a parallel list of boolean ndarrays
  of shape ``(L_i,)`` (all ``True`` once special tokens have been
  stripped; reserved for future masked-token use-cases such as MLM
  reconstruction or padded-batch outputs). ``embeddings`` is ``None``
  because the per-sequence shapes are ragged.

The granularity is part of the payload so downstream consumers
(KNN index builders, MIL pooling heads, reranker feature extractors)
can validate the shape they receive at the boundary.

Heavy ML deps (torch, transformers) live in
:mod:`protea_backends`; this module only depends on numpy and
pydantic, in line with the contracts-package rule.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator

#: Allowed granularity values. ``"mean_pool"`` returns a ``(B, D)``
#: matrix (one row per sequence). ``"per_residue"`` returns ``B``
#: ragged ``(L_i, D)`` tensors plus matching attention masks.
Granularity = Literal["mean_pool", "per_residue"]


class EmbeddingPayload(BaseModel):
    """Pydantic-typed output of :meth:`EmbeddingBackend.embed_batch`.

    Carries the embeddings tensor (or list of tensors) plus the
    granularity tag so callers can branch on shape at the boundary.

    Attributes:
        granularity: ``"mean_pool"`` or ``"per_residue"``.
        embeddings: ``(B, D)`` float16 ndarray for ``mean_pool``;
            ``None`` for ``per_residue`` (ragged shapes go through
            :attr:`residues` instead).
        residues: list of ``B`` float16 ndarrays of shape ``(L_i, D)``
            for ``per_residue``; ``None`` for ``mean_pool``. Each entry
            is one sequence's residue-level embedding, CLS/EOS already
            stripped by the backend so that index ``j`` in
            ``residues[i]`` corresponds to the ``j``-th amino acid of
            ``sequences[i]``.
        attention_mask: list of ``B`` bool ndarrays of shape ``(L_i,)``
            for ``per_residue``; ``None`` for ``mean_pool``. Currently
            all-ones once special tokens have been stripped (kept as a
            field for forward-compat with future padded-batch or
            masked-token consumers).
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
        extra="forbid",
    )

    granularity: Granularity = "mean_pool"
    embeddings: Any = None
    residues: Any = None
    attention_mask: Any = None

    @model_validator(mode="after")
    def _check_shape_invariants(self) -> EmbeddingPayload:
        """Dispatch to per-granularity invariant checks."""
        if self.granularity == "mean_pool":
            _check_mean_pool(self.embeddings, self.residues, self.attention_mask)
        else:
            _check_per_residue(self.embeddings, self.residues, self.attention_mask)
        return self

    def as_matrix(self) -> np.ndarray[Any, Any]:
        """Return the ``(B, D)`` matrix when ``mean_pool``, else mean-pool now.

        Convenience helper for downstream callers that want a flat
        matrix regardless of granularity (e.g., KNN index builders
        that operate on protein-level vectors). For ``per_residue``
        payloads this collapses each sequence's residue tensor to its
        column-wise mean, mirroring the backend's mean-pool path.
        """
        if self.granularity == "mean_pool":
            return self.embeddings  # type: ignore[no-any-return]
        pooled = [r.mean(axis=0) for r in self.residues]
        return np.stack(pooled).astype(np.float16)


def _check_mean_pool(
    embeddings: Any, residues: Any, attention_mask: Any
) -> None:
    """Validate the mean_pool granularity invariants."""
    if not isinstance(embeddings, np.ndarray):
        raise ValueError(
            "EmbeddingPayload(granularity='mean_pool') requires "
            "embeddings to be a numpy ndarray"
        )
    if embeddings.ndim != 2:
        raise ValueError(
            "EmbeddingPayload(granularity='mean_pool') requires "
            f"a 2-D embeddings array, got shape {embeddings.shape}"
        )
    if residues is not None or attention_mask is not None:
        raise ValueError(
            "EmbeddingPayload(granularity='mean_pool') must not "
            "carry residues / attention_mask"
        )


def _check_per_residue(
    embeddings: Any, residues: Any, attention_mask: Any
) -> None:
    """Validate the per_residue granularity invariants."""
    if embeddings is not None:
        raise ValueError(
            "EmbeddingPayload(granularity='per_residue') must not "
            "carry the (B, D) embeddings matrix; use the residues "
            "list instead"
        )
    if not isinstance(residues, list) or not isinstance(attention_mask, list):
        raise ValueError(
            "EmbeddingPayload(granularity='per_residue') requires "
            "residues and attention_mask to be lists of ndarrays"
        )
    if len(residues) != len(attention_mask):
        raise ValueError(
            "residues and attention_mask must have the same length, "
            f"got {len(residues)} and {len(attention_mask)}"
        )
    for i, (r, m) in enumerate(zip(residues, attention_mask, strict=True)):
        _check_residue_entry(i, r, m)


def _check_residue_entry(i: int, r: Any, m: Any) -> None:
    """Validate a single ``(residues[i], attention_mask[i])`` pair."""
    if not isinstance(r, np.ndarray) or r.ndim != 2:
        raise ValueError(
            f"residues[{i}] must be a 2-D ndarray, got {type(r)}"
        )
    if not isinstance(m, np.ndarray) or m.ndim != 1:
        raise ValueError(
            f"attention_mask[{i}] must be a 1-D ndarray, got {type(m)}"
        )
    if r.shape[0] != m.shape[0]:
        raise ValueError(
            f"residues[{i}] leading dim ({r.shape[0]}) must match "
            f"attention_mask[{i}] length ({m.shape[0]})"
        )
