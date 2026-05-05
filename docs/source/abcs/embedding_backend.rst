EmbeddingBackend
================

Contract for protein language model embedding plugins. Implementations
live in ``protea-backends`` (``esm``, ``t5``, ``ankh``, ``esm3c``) and
register through the ``protea.backends`` ``entry_points`` group.

Operational role
----------------

``protea-core`` discovers backends at startup and dispatches embedding
work by ``name`` from
``protea/core/operations/compute_embeddings.py``. Heavy ML
dependencies (``torch``, ``transformers``, ``sentencepiece``, ``esm``)
are imported lazily inside ``load_model`` and ``embed_batch`` so plugin
discovery is free even on machines without the heavy stack installed.

Each backend returns float16 embeddings of shape
``(batch_size, hidden_dim)`` with the special tokens (``CLS``, ``EOS``,
``BOS``, prefix tokens) stripped before pooling. Pooling defaults to
mean over residues; per-layer aggregation is supported for backends
whose hidden states are exposed.

API reference
-------------

.. automodule:: protea_contracts.embedding_backend
   :members:
   :show-inheritance:
   :member-order: bysource
