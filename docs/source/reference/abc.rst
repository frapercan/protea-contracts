Plugin ABCs
===========

The four abstract base classes that structure the four plugin layers of
the PROTEA stack. Plugin packages (``protea-sources``, ``protea-backends``,
``protea-runners``) subclass exactly one of these and register via Python
``entry_points``.

.. rubric:: AnnotationSource

Contract for annotation source plugins. Implementations live in
``protea-sources`` (``goa``, ``quickgo``, ``uniprot``) and register
through the ``protea.sources`` ``entry_points`` group.

.. automodule:: protea_contracts.annotation_source
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:

.. rubric:: EmbeddingBackend

Contract for protein language model embedding backends. Implementations
live in ``protea-backends`` and register through ``protea.backends``.

.. automodule:: protea_contracts.embedding_backend
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:

.. rubric:: ExperimentRunner

Contract for experiment runner plugins. Implementations live in
``protea-runners`` (``lightgbm``, ``knn``, ``baseline``) and register
through ``protea.runners``.

.. automodule:: protea_contracts.experiment_runner
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:

.. rubric:: FeatureRegistry

In-process plugin contract used by the re-ranker pipeline. Not
discovered via entry-points; instantiated directly by PROTEA operations.

.. automodule:: protea_contracts.feature_registry
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:
