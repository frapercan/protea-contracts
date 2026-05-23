Payloads
========

Pydantic models (``frozen=True, strict=True, extra="forbid"``) that
validate the body of HTTP requests and RabbitMQ queue messages crossing
package boundaries. Field typos and missing required fields fail at
construction time with ``ValidationError``, not silently at consumption.

**SemVer policy:** adding a new field with a default is a minor bump;
removing or renaming a field is a major bump.

.. automodule:: protea_contracts.payloads
   :members:
   :show-inheritance:
   :member-order: bysource
   :no-index:
