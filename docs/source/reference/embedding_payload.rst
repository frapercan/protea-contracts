Embedding payload
=================

The typed payload used to transport embedding matrices across the
embedding backend boundary. ``EmbeddingPayload`` wraps the numpy array
returned by a backend's ``embed_batch`` together with provenance metadata
(model name, pooling strategy, layer).

.. automodule:: protea_contracts.embedding_payload
   :members:
   :show-inheritance:
   :member-order: bysource
