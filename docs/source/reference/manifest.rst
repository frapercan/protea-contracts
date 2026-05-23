Manifest
========

The parquet manifest written by ``export_research_dataset`` in PROTEA and
read by ``protea-runners.lightgbm`` during training. ``ManifestV1`` is the
canonical shape; future schema versions add a discriminated version field
rather than mutating the current class in place.

.. automodule:: protea_contracts.manifest
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:
