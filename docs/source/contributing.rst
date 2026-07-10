Evolving the contract package
==============================

``protea-contracts`` is the most disruptive package in the stack: a
SemVer-significant change here ripples through every consumer
(``protea-core``, ``protea-method``, ``protea-sources``,
``protea-runners``, ``protea-backends``, ``protea-reranker-lab``).

SemVer policy
-------------

- **Patch (``x.y.Z``)**: docstrings, type-hint refinements that do
  not change runtime behaviour, internal helpers.
- **Minor (``x.Y.0``)**: new pydantic fields with a default, new
  optional ABC method, new feature added to ``ALL_FEATURES`` (changes
  the schema sha, so boosters retrain).
- **Major (``X.0.0``)**: removed pydantic fields, renamed feature
  names, ABC method signature changes, removed re-export.

The package is past ``1.0``, so SemVer applies strictly: a minor bump
is a compatibility promise and any breaking change forces a major.
The public surface (re-exports in ``__all__``, ``CANONICAL_AXIS_KEYS``,
payload field names, ABC method shapes) is frozen within a major line.

Adding a feature to ``ALL_FEATURES``
------------------------------------

The schema sha is byte-stable across re-orderings (the implementation
sorts before hashing). Adding a feature still changes the digest
because the sorted list is longer. Every booster trained against the
old digest will refuse to load against the new one. That is the
intended behaviour.

Procedure:

1. Add the feature to the relevant family list in
   ``feature_schema.py`` (``NUMERIC_FEATURES`` or
   ``CATEGORICAL_FEATURES``) and to ``FEATURE_FAMILIES``.
2. Update the golden test that pins the canonical sha to the new
   value (``tests/test_feature_schema.py``).
3. Bump the package minor version (e.g. ``1.0.1`` to ``1.1.0``).
4. In ``protea-core``: add the matching feature to the registry,
   update the parity test ``test_feature_contract.py`` and re-run the
   golden parquet bit-exact test.
5. Re-train the canonical re-ranker against the new schema before
   merging anything that consumes the new feature in production.

Adding an ABC method
--------------------

For an additive change that does not break old plugins, add the
method with a default implementation that calls
``raise NotImplementedError`` and document it as ``required from
version X``. Plugins shipped before X will fail loud at the call site
rather than silently. Bump the package minor.

For a breaking change to an existing signature, write the new ABC
alongside the old one (``EmbeddingBackendV2``) and migrate consumers
explicitly. Drop the old ABC in a major bump once all consumers are
on V2.

Adding a payload field
----------------------

Pydantic makes optional fields with a default cheap. Add a field
with ``Optional[T] = None``, document the semantics, bump minor. Old
clients keep working.

Removing or renaming a field requires a deprecation cycle: introduce
the new name, leave the old one accepting input via
``model_validator``, log a warning, and drop the old name on the
following major.

Documentation
-------------

Whenever a public symbol is added or its semantics change, update the
matching ``.rst`` page (or add one if a new module is introduced).
Sphinx autodoc reads docstrings directly, so keep the canonical
explanation in the source rather than in the page body.

Build the docs locally with::

    poetry install --with docs
    cd docs && make html

The ``docs`` group is optional (``optional = true`` in
``pyproject.toml``); default ``poetry install`` does not pull
Sphinx.
