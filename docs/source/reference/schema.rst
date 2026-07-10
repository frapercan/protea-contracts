Feature schema
==============

The canonical feature schema is the load-bearing fingerprint of the
re-ranker pipeline. ``compute_schema_sha`` reduces the ordered list of
feature names to a stable digest that the re-ranker compares before
applying a trained booster: if the registry produces features in a
different order, or with different names, the digest changes and the
booster is rejected rather than silently scoring on misaligned columns.

The digest is pinned in ``tests/test_feature_schema.py``. Any change
to ``ALL_FEATURES`` that moves the digest without an explicit update
to that golden test fails CI.

.. automodule:: protea_contracts.feature_schema
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:
