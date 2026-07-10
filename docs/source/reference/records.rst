Records
=======

Streaming record types yielded by ``protea-sources`` plugins and consumed
by PROTEA operations. Records are leaves: plugin authors yield them from
``stream*()`` methods; consuming operations read them and never pass them
back across the package boundary. This keeps the dataflow one-way and
easy to audit.

All record types are ``frozen=True, strict=True, extra="forbid"`` pydantic
models.

.. automodule:: protea_contracts.records
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:
