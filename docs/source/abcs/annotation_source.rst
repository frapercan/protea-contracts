AnnotationSource
================

Contract for annotation source plugins. Implementations live in
``protea-sources`` (``goa``, ``quickgo``, ``uniprot``, future
``interproscan``) and register through the ``protea.sources``
``entry_points`` group.

Operational role
----------------

``protea-core`` dispatches load requests by ``name``: a job arrives
on the ``protea.jobs`` queue with a payload identifying the source,
the worker resolves the matching plugin via ``entry_points``, and
calls ``load(session, payload, emit=...)``. The plugin is responsible
for downloading or streaming the source release, parsing it, and
inserting the rows into the relational data model.

Source releases are tracked via the ``version`` attribute, which is
persisted to ``AnnotationSet.source_version`` so any prediction set
can be traced back to the exact upstream release.

API reference
-------------

.. automodule:: protea_contracts.annotation_source
   :members:
   :show-inheritance:
   :member-order: bysource
