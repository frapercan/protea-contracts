"""Contract for experiment runner plugins.

A plugin in ``protea-runners`` (e.g. ``lightgbm``, ``knn``, future
``gnn`` / ``retrieval_neural``) implements ``ExperimentRunner`` and
registers itself via the ``protea.runners`` ``entry_points`` group.
``protea-core`` looks up the runner by name when the user submits an
``ExperimentRun`` and dispatches the ``fit`` / ``evaluate`` /
``export`` lifecycle.

Example::

    from protea_contracts.experiment_runner import (
        ExperimentRunner,
        RunResult,
    )

    class LightgbmRunner(ExperimentRunner):
        name = "lightgbm"

        def fit(self, spec, dataset_uri, *, emit):
            # Pull dataset, train booster, save artefact, return URI...
            return RunResult(model_uri="s3://...", metrics={"val_auc": 0.85})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RunResult:
    """Outcome of a training or fit invocation.

    ``model_uri`` references the produced artefact in the configured
    store (local FS or MinIO). ``metrics`` is a free-form dict that
    the platform persists alongside the resulting ``RerankerModel`` /
    ``ExperimentRun`` row.
    """

    model_uri: str
    metrics: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalResult:
    """Outcome of an evaluation invocation.

    ``metrics`` carries the canonical CAFA-style numbers (Fmax, AuPRC,
    coverage, per-aspect breakdowns). ``extras`` is for runner-specific
    diagnostics that don't fit the canonical schema.
    """

    metrics: dict[str, Any]
    extras: dict[str, Any] = field(default_factory=dict)


class ExperimentRunner(ABC):
    """Contract for a plugin that runs a training / evaluation experiment."""

    name: str
    """Stable string identifier (e.g. ``"lightgbm"``, ``"knn"``)."""

    @abstractmethod
    def fit(
        self,
        spec: dict[str, Any],
        dataset_uri: str,
        *,
        emit: Any,
    ) -> RunResult:
        """Train a model from a frozen dataset.

        Args:
            spec: runner-specific hyperparameters and knobs (validated
                by the implementation, typically against a pydantic model).
            dataset_uri: opaque store URI resolved by ``ArtifactStore``
                (e.g. ``"s3://bucket/datasets/study_v_thesis/"``).
            emit: structured-event callback.

        Returns:
            :class:`RunResult` with the trained artefact URI plus any
            runner-side metrics.
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        model_uri: str,
        eval_dataset_uri: str,
        *,
        emit: Any,
    ) -> EvalResult:
        """Evaluate a trained model against a held-out dataset.

        Returns:
            :class:`EvalResult` whose ``metrics`` follow the canonical
            CAFA schema (``fmax``, ``auc_pr``, ``coverage`` per aspect).
        """
        raise NotImplementedError

    @abstractmethod
    def export(
        self,
        run_id: str,
        output_uri: str,
        *,
        emit: Any,
    ) -> dict[str, Any]:
        """Export training artefacts under ``output_uri`` for downstream consumers.

        Returns:
            Dict describing the exported files (URIs, sizes, content
            hashes). Exact shape is runner-specific but should be JSON
            serialisable.
        """
        raise NotImplementedError
