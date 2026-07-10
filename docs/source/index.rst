protea-contracts
================

The contract surface for the PROTEA stack: the abstract base classes
that plugin repositories implement, the canonical feature schema with
its versioned content fingerprint, the pydantic payloads and records
that cross the platform's queue and HTTP boundaries, and the axis-tuple
identity that joins the platform to the lab. Every other repository in
the stack imports this package; nothing in it imports them.

.. note::

   This package is deliberately dependency-light. It depends only on
   ``pydantic``, ``numpy`` and ``pyarrow``. It must **never** import
   ``sqlalchemy``, ``fastapi``, ``torch``, or anything from
   ``protea-core``. Downstream consumers (the lab, the runners, the
   backends, the sources, the inference path) install this package
   without dragging the platform stack along.

New here? Read :doc:`concepts` for the mental model, then
:doc:`quickstart` to build a plugin end to end.

What lives here
---------------

The documentation follows the contract from idea to reference:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Section
     - What it covers
   * - :doc:`concepts`
     - The mental model: why a separate contract surface, how ABCs plus
       entry points enable the plugin architecture, and how the schema
       fingerprint guards drift.
   * - :doc:`quickstart`
     - A plugin author's path from install to a registered, discoverable
       plugin: subclass an ABC, set ``name``, expose it via entry points.
   * - :doc:`abcs/index`
     - The four plugin contracts (``AnnotationSource``,
       ``EmbeddingBackend``, ``ExperimentRunner``, ``FeatureRegistry``)
       and their operational roles.
   * - :doc:`schema`
     - The non-ABC half: canonical feature schema and ``schema_sha``,
       pydantic payloads, the parquet manifest, streaming records, and
       the axis-tuple provenance key.
   * - :doc:`reference/index`
     - Per-module autodoc for every public symbol.
   * - :doc:`contributing`
     - SemVer rules for evolving the contract without breaking every
       consumer.

.. toctree::
   :hidden:
   :caption: Getting started

   concepts
   quickstart

.. toctree::
   :hidden:
   :caption: The contract model

   abcs/index
   schema

.. toctree::
   :hidden:
   :caption: API reference

   reference/index

.. toctree::
   :hidden:
   :caption: Development

   contributing
