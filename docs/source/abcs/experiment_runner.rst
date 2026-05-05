ExperimentRunner
================

Contract for experiment runner plugins. Implementations live in
``protea-runners`` (``knn``, ``lightgbm``, ``baseline``, future
``gnn``, ``retrieval_neural``) and register through the
``protea.runners`` ``entry_points`` group.

Operational role
----------------

The runner abstraction unifies three lifecycle methods: ``fit`` (train
or otherwise prepare the model from a dataset), ``evaluate``
(produce metrics on a held-out split) and ``export`` (persist the
trained artefact for later inference). The ``RunResult`` and
``EvalResult`` dataclasses normalise the return shapes so
``protea-core`` can record provenance uniformly across runners.

In ``protea-core`` the runner contract is consumed by
``protea/core/operations/export_research_dataset.py`` (which builds
the dataset that ``fit`` consumes) and by
``protea-runners/lightgbm`` (which absorbs the offline LightGBM
trainer in F2A.7 of the master plan).

API reference
-------------

.. automodule:: protea_contracts.experiment_runner
   :members:
   :show-inheritance:
   :member-order: bysource
