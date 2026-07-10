Feature documentation registry
==============================

Where :doc:`schema` owns the canonical feature *names* and the fingerprint,
this page answers, for the technician who deploys and operates the stack, what
each column *measures*, how it is *computed*, *who produces it*, and whether a
producer actually runs in the default export today.

The whole table below is generated at build time from
:data:`protea_contracts.feature_docs.FEATURE_DOCS`. It is never written by
hand: edit a :class:`~protea_contracts.feature_docs.FeatureDoc` in
``src/protea_contracts/feature_docs.py`` and this page follows. A drift lint
(``scripts/check_feature_docs.py`` plus ``tests/test_feature_docs.py``) fails
if a declared feature loses its doc, if a doc names an undeclared column, or if
a doc's family disagrees with ``FEATURE_FAMILIES``.

Status legend
-------------

:PRODUCED: A wired producer fills the column with a real value in the export
   (some features sit behind a performance flag that the canonical export
   enables; see the feature's notes).
:DECLARED_ABSENT: The column is a first-class member of the schema and a
   producer exists, but no producer runs in the default export, so the export
   emits ``NaN``. The six LAFA columns are in this state per ADR-D45.
:POOL_INJECTED: The PROTEA dump does not write the column; the lab's pooled
   multi-manifest loader injects it as a per-source constant at stage time.
:BROKEN: The column is produced but a defect that can be pointed at in code or
   data makes it carry no signal. Used only where that defect is verifiable
   from the source tree.

The registry
------------

.. feature-docs-table::

Programmatic access
-------------------

.. automodule:: protea_contracts.feature_docs
   :members:
   :member-order: bysource
   :no-index:
