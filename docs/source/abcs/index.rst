Plugin contracts (ABCs)
========================

Four abstract base classes structure the four plugin layers of the
PROTEA stack.

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - ABC
     - Plugin group
     - Implemented in
   * - :doc:`AnnotationSource <annotation_source>`
     - ``protea.sources``
     - ``protea-sources/{goa,quickgo,uniprot}``
   * - :doc:`EmbeddingBackend <embedding_backend>`
     - ``protea.backends``
     - ``protea-backends/{esm,t5,ankh,esm3c}``
   * - :doc:`ExperimentRunner <experiment_runner>`
     - ``protea.runners``
     - ``protea-runners/{knn,lightgbm,baseline}``
   * - :doc:`FeatureRegistry <feature_registry>`
     - n/a (in-process)
     - ``protea-core/protea/core/features/`` (F2B.1 and onwards)

Each ABC carries:

- a class attribute ``name`` matching the entry-point name (or, for
  ``FeatureRegistry``, the family identifier);
- a small set of abstract methods covering the lifecycle of the
  plugin (load, run, embed, fit / evaluate / export, etc.);
- type annotations using ``Any`` for objects that ``protea-contracts``
  cannot import (SQLAlchemy sessions, torch models). Implementations
  narrow the types in their docstrings.

.. toctree::
   :maxdepth: 1

   annotation_source
   embedding_backend
   experiment_runner
   feature_registry
