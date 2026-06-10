Quickstart for plugin authors
=============================

``protea-contracts`` is what you import to extend the PROTEA stack
without depending on the platform core. This page walks a plugin author
from install to a registered, discoverable plugin.

Install
-------

.. code-block:: bash

   pip install protea-contracts

The package pulls only ``pydantic``, ``numpy`` and ``pyarrow``. It never
imports ``sqlalchemy``, ``fastapi``, ``torch`` or ``protea-core``, so it
stays importable in any consumer environment.

Verify the install and print the live feature-schema fingerprint:

.. code-block:: bash

   python -c "from protea_contracts import ALL_FEATURES, compute_schema_sha; print(compute_schema_sha(ALL_FEATURES))"

Pick the contract for your plugin layer
---------------------------------------

The stack has four plugin layers, each backed by one abstract base
class and one entry-point group:

.. list-table::
   :header-rows: 1
   :widths: 26 24 50

   * - You are building
     - Subclass
     - Register under
   * - An annotation source (GAF, TSV, FASTA feed)
     - :class:`~protea_contracts.annotation_source.AnnotationSource`
     - ``protea.sources``
   * - A protein language model backend
     - :class:`~protea_contracts.embedding_backend.EmbeddingBackend`
     - ``protea.backends``
   * - A training / evaluation runner
     - :class:`~protea_contracts.experiment_runner.ExperimentRunner`
     - ``protea.runners``
   * - An in-process feature registry
     - :class:`~protea_contracts.feature_registry.FeatureRegistry`
     - n/a (instantiated directly)

Implement the ABC
-----------------

Set the ``name`` class attribute (it must match the entry-point name)
and implement the abstract methods. An embedding backend, for example:

.. code-block:: python

   import numpy as np
   from protea_contracts.embedding_backend import EmbeddingBackend


   class MyBackend(EmbeddingBackend):
       name = "my_backend"

       def load_model(self, model_name, device, emit):
           model = ...      # load weights onto `device`
           tokenizer = ...
           return model, tokenizer

       def embed_batch(self, model, tokenizer, sequences, *, emit,
                       layers=None, layer_agg="mean", pooling="mean"):
           # Run inference, mean-pool, return a (B, D) float16 matrix.
           return np.asarray(vectors, dtype=np.float16)

Register via entry points
-------------------------

Advertise the plugin in your package metadata so ``protea-core``
discovers it at startup. In ``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."protea.backends"]
   my_backend = "my_package.backend:MyBackend"

The key (``my_backend``) must equal the class ``name`` attribute. PROTEA
resolves the plugin by that name when a job references it.

Build typed payloads and records
--------------------------------

Payloads validate the body of HTTP requests and queue messages; records
are the immutable rows a source plugin yields. Both fail loud at
construction, so a typo never reaches the consumer:

.. code-block:: python

   from protea_contracts import GoaStreamPayload, GoaAnnotationRecord

   payload = GoaStreamPayload(gaf_url="https://example.com/x.gaf.gz")
   record = GoaAnnotationRecord(accession="P12345", go_id="GO:0008150")

All payloads and records are ``frozen=True, strict=True,
extra="forbid"``: no silent type coercion, no unexpected keys.

Guard reproducibility with the schema sha
-----------------------------------------

A reranker booster is only valid against the exact feature set it was
trained on. Compare the fingerprint before applying one:

.. code-block:: python

   from protea_contracts import ALL_FEATURES, compute_schema_sha

   live_sha = compute_schema_sha(ALL_FEATURES)
   if live_sha != booster.feature_schema_sha:
       raise RuntimeError("schema drift: refusing to score on misaligned columns")

Next steps
----------

- :doc:`abcs/index` for the full lifecycle of each plugin contract.
- :doc:`schema` for payloads, manifest, records and axis keys.
- :doc:`contributing` before you change a public symbol (SemVer rules).
