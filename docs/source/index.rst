protea-contracts
================

The contract surface for the PROTEA stack: abstract base classes that
plugin repositories implement, the canonical feature schema with its
versioned content fingerprint, and the pydantic payloads that flow
through the platform's queues and HTTP boundaries.

.. note::

   This package is deliberately dependency-light. It depends only on
   ``pydantic``, ``numpy`` and ``pyarrow``. It must **never** import
   ``sqlalchemy``, ``fastapi``, ``torch``, or anything from
   ``protea-core``. Downstream consumers (the lab, the runners, the
   backends, the sources) install this package without dragging the
   platform stack along.

What lives here
---------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Module
     - Role
   * - :doc:`abcs/annotation_source`
     - Plugin contract for annotation sources (``goa``, ``quickgo``,
       ``uniprot``, ``interpro``).
   * - :doc:`abcs/embedding_backend`
     - Plugin contract for protein language model backends (``esm``,
       ``t5``, ``ankh``, ``esm3c``).
   * - :doc:`abcs/experiment_runner`
     - Plugin contract for experiment runners (``lightgbm``, ``knn``,
       ``baseline``, future ``gnn``, ``retrieval_neural``).
   * - :doc:`abcs/feature_registry`
     - Plugin contract for the per-candidate feature registry that
       backs the re-ranker.
   * - :doc:`schema`
     - Canonical feature schema (``ALL_FEATURES``, families,
       ``compute_schema_sha``), pydantic payloads, parquet manifest,
       streaming records.

Why a separate contracts package
--------------------------------

Three reasons drove the split (ADR D1):

1. **Plugin extensibility.** New annotation sources, embedding
   backends and experiment runners must be addable as out-of-tree
   contributions. Without a stable contract package each plugin would
   re-import private symbols from ``protea-core``, recreating the
   monolith.

2. **Reproducibility.** The feature schema fingerprint
   (``compute_schema_sha``) gates whether a re-ranker booster trained
   yesterday can be applied today. The fingerprint must be a single
   source of truth, not two parallel definitions in ``protea-core``
   and the lab. Past silent drift cost one non-reproducible study run
   (D10).

3. **Inference shipping.** ``protea-method``, the pure inference
   path, can be PyPI-published without the platform stack precisely
   because every contract it touches lives here.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Concepts

   abcs/index
   schema

.. toctree::
   :maxdepth: 2
   :caption: API reference

   reference/index

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
