Concepts
========

``protea-contracts`` is the seam that holds the PROTEA stack together.
Every other repository (``protea-core``, ``protea-method``,
``protea-sources``, ``protea-runners``, ``protea-backends``,
``protea-reranker-lab``) imports it, and nothing in it imports them.
This page is the mental model: what the contract surface is for, how it
enables the plugin architecture, and how its fingerprints keep the
platform and the lab in agreement.

One contract surface
--------------------

The package is a single, dependency-light place to declare the shapes
that cross repository and process boundaries. Three reasons drove the
split out of ``protea-core`` (ADR D1):

1. **Plugin extensibility.** New annotation sources, embedding backends
   and experiment runners must be addable as out-of-tree contributions.
   Without a stable contract package each plugin would re-import private
   symbols from ``protea-core``, recreating the monolith it was meant to
   break apart.

2. **Reproducibility.** The feature schema fingerprint
   (:func:`~protea_contracts.feature_schema.compute_schema_sha`) decides
   whether a re-ranker booster trained yesterday can be applied today.
   That
   fingerprint must have a single source of truth, not two parallel
   definitions in ``protea-core`` and the lab. Past silent drift between
   two copies cost one non-reproducible study run (ADR D10).

3. **Inference shipping.** ``protea-method``, the pure inference path,
   can be published to PyPI without the platform stack precisely because
   every contract it touches lives here and pulls only ``pydantic``,
   ``numpy`` and ``pyarrow``.

The dependency-light discipline is the load-bearing rule: the moment
this package imports ``sqlalchemy``, ``fastapi``, ``torch`` or
``protea-core``, every downstream consumer inherits that weight and the
inference path stops being shippable on its own.

Plugins through ABCs and entry points
-------------------------------------

Three of the four plugin layers are discovered, not wired in. A plugin
package subclasses one :doc:`abstract base class <abcs/index>`, sets its
``name`` attribute, and advertises the class under a Python
``entry_points`` group:

.. list-table::
   :header-rows: 1
   :widths: 34 24 42

   * - ABC
     - Entry-point group
     - Resolved by
   * - :class:`~protea_contracts.annotation_source.AnnotationSource`
     - ``protea.sources``
     - payload ``source`` name
   * - :class:`~protea_contracts.embedding_backend.EmbeddingBackend`
     - ``protea.backends``
     - ``EmbeddingConfig.model_backend``
   * - :class:`~protea_contracts.experiment_runner.ExperimentRunner`
     - ``protea.runners``
     - ``RerankerSpec.runner``

``protea-core`` enumerates the entry points at startup and looks a
plugin up by ``name`` when a job references it. The ABC types objects
that ``protea-contracts`` cannot import (SQLAlchemy sessions, torch
models) as ``Any`` and lets the implementation narrow them, so plugin
discovery stays free of the heavy stack. The fourth contract,
:class:`~protea_contracts.feature_registry.FeatureRegistry`, is not an
entry-point plugin: it lives inside ``protea-core`` and is instantiated
directly, but it is an ABC for the same reason, to pin the shape the
re-ranker depends on.

Typed data across boundaries
----------------------------

Once a plugin is running, the data it exchanges with the platform is
also contract-typed, so a malformed message fails at construction rather
than deep inside a consumer:

- **Payloads** (:doc:`reference/payloads`) validate the body of HTTP
  requests and RabbitMQ queue messages. Every Job's ``payload`` JSONB
  must validate against one of these models before a worker dispatches
  the operation. They are ``frozen=True, strict=True, extra="forbid"``:
  no silent coercion, no unexpected keys.
- **Records** (:doc:`reference/records`) are the immutable rows a source
  plugin streams out of a release. They flow one way: plugins yield
  them, operations consume them, and they never travel back across the
  boundary.
- **Contexts** (:doc:`reference/contexts`) carry the inputs a plugin
  callback needs without exposing ORM sessions or internal platform
  types.

The schema fingerprint guards drift
-----------------------------------

The re-ranker booster is a trained model that hard-binds to an exact,
ordered set of feature columns.
:func:`~protea_contracts.feature_schema.compute_schema_sha` reduces that
column set to a stable 12-hex digest. The pipeline compares the live
digest against the one a booster was trained with before applying it: if
the registry ever produces features in a different order, or with
different names, the digest changes and the booster is rejected rather
than silently scoring on misaligned columns. Adding a feature to
``ALL_FEATURES`` deliberately moves the digest, which forces every stale
booster to retrain. The digest is pinned by a golden test,
so any rename, reorder or addition that moves it is caught in CI and
forces a SemVer-major release.

One identity per benchmark cell
-------------------------------

Finally, the contract gives every benchmark cell a single identity. An
*axis tuple* (the protein language model, the KNN ``k``, the reranker
spec, the feature schema sha, the eval set, propagation and ensemble
spec) names one cell, and
:func:`~protea_contracts.axis_tuple.axis_tuple_shortid` collapses it to a stable
12-hex id. That id is the join key between PROTEA's ``ExperimentRun``
rows and the lab's experiment catalog. Both sides must compute a
byte-identical id or the membership join silently drops rows, so the
formula is golden-vector pinned and a change to it forces a major bump,
exactly like the schema sha.

Where to go next
----------------

- :doc:`quickstart` builds a plugin end to end, from subclass to
  registered entry point.
- :doc:`abcs/index` documents the full lifecycle of each plugin
  contract.
- :doc:`schema` covers the schema, payloads, manifest, records and axis
  keys in one place.
- :doc:`reference/index` is the per-symbol autodoc reference.
