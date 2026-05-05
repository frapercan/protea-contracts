FeatureRegistry
===============

Contract for the per-candidate feature registry that backs the
re-ranker. Unlike the other three ABCs this one is not implemented in
a separate plugin repository: the registry lives inside
``protea-core/protea/core/features/`` and is wired into
``parquet_export`` and ``predict_go_terms`` from F2B.1 onwards.

Operational role
----------------

The registry is the canonical source of truth for which features are
computed per candidate annotation. The KNN runner queries the registry
to assemble feature rows; the export operation iterates the registry
to write training parquets; the inference path applies the registry
in the same order to keep the schema fingerprint stable.

Each ``Feature`` carries:

- a ``name`` (the column name that ends up in parquet);
- a ``family`` (e.g. ``"alignment"``, ``"taxonomy"``, ``"anc2vec"``,
  ``"emb_pca"``, ``"annotation_meta"``);
- a ``dtype`` (numeric, categorical, or vector with explicit length);
- a compute callable that receives a per-candidate context.

The registry total is fingerprinted by
:func:`protea_contracts.compute_schema_sha`, which the re-ranker
uses to refuse boosters whose schema has drifted from the live
pipeline.

API reference
-------------

.. automodule:: protea_contracts.feature_registry
   :members:
   :show-inheritance:
   :member-order: bysource
