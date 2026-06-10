Schema, payloads, manifest, records
====================================

The non-ABC half of ``protea-contracts``: the canonical feature
schema, the pydantic payloads that travel through HTTP and queue
boundaries, the parquet manifest, the streaming record types, and the
axis-tuple provenance key that joins the platform to the lab.

Feature schema
--------------

The feature schema is the load-bearing fingerprint of the re-ranker
pipeline. ``compute_schema_sha`` reduces a list of feature names to
a stable digest that the re-ranker compares before applying a booster:
if the registry produces features in a different order, or with
different names, the digest changes and the booster is rejected
rather than silently scoring on misaligned columns.

Past silent drift between two parallel definitions of
``compute_schema_sha`` (lab vs platform) cost one non-reproducible
study run in 2026-05-01. ADR D10 documents the migration that
brings every consumer onto a single source of truth.

.. automodule:: protea_contracts.feature_schema
   :members:
   :show-inheritance:
   :member-order: bysource

Payloads
--------

Pydantic models that validate the body of HTTP requests and queue
messages. Adding a new field to one of these is a SemVer minor bump;
removing or renaming a field is a major bump.

.. automodule:: protea_contracts.payloads
   :members:
   :show-inheritance:
   :member-order: bysource

Manifest
--------

The parquet manifest written by ``export_research_dataset`` and read
by ``protea-runners.lightgbm`` (and the legacy lab). ``ManifestV1``
is the canonical shape; future versions add a discriminated version
field rather than mutating the current class in place.

.. automodule:: protea_contracts.manifest
   :members:
   :show-inheritance:
   :member-order: bysource

Records
-------

Streaming record types for the GOA and QuickGO sources, plus their
ECO-evidence-code mapping payload. Used to type the page handlers
inside ``protea-sources.{goa,quickgo}`` without importing
SQLAlchemy.

.. automodule:: protea_contracts.records
   :members:
   :show-inheritance:
   :member-order: bysource

Axis keys and provenance
------------------------

Every benchmark cell in the re-benchmark is identified by an *axis
tuple*: the protein language model, the KNN ``k``, the reranker spec,
the feature schema sha, the eval set, propagation and ensemble spec.
:func:`~protea_contracts.axis_tuple.axis_tuple_shortid` reduces that
mapping to a stable 12-hex id, and
:data:`~protea_contracts.axis_tuple.CANONICAL_AXIS_KEYS` is the single
reviewed reference for what counts as an axis.

The shortid is the join key between PROTEA's ``ExperimentRun`` rows and
the lab's experiment catalog. Both sides must compute byte-identical
ids or the membership join silently drops rows, so the digest is
golden-vector pinned (``tests/test_axis_tuple.py``) and a change to the
formula forces a major version bump. Full autodoc lives in the
:doc:`API reference <reference/axis_tuple>`.
