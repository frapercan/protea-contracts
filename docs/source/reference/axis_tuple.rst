Axis tuple
==========

The canonical axis-tuple shortid shared by PROTEA and
``protea-reranker-lab``. Every benchmark cell is identified by an axis
tuple (PLM, ``k``, reranker spec, feature schema sha, eval set,
propagation, ensemble spec); ``axis_tuple_shortid`` collapses that
mapping to a stable 12-hex id used as a join key across the platform
and the lab.

The digest is byte-stable and golden-vector pinned in
``tests/test_axis_tuple.py``: PROTEA's row-membership join with the lab
catalog breaks silently if the two sides ever compute a different id,
so any change to the formula forces a major version bump.

.. automodule:: protea_contracts.axis_tuple
   :members:
   :show-inheritance:
   :member-order: bysource
