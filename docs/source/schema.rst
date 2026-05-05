Schema, payloads, manifest, records
====================================

The non-ABC half of ``protea-contracts``: the canonical feature
schema, the pydantic payloads that travel through HTTP and queue
boundaries, the parquet manifest, and the streaming record types.

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
study run in 2026-05-01. ADR D10 documents the v2 migration that
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
is the canonical shape; future versions add a discriminated ``v``
field rather than mutating ``v1`` in place.

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
