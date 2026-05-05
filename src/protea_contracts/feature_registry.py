"""Contract for the feature registry used by KNN + reranker pipelines.

The feature registry centralises *what* features are computed and
*by which* family. Implementations live in ``protea-core`` and the
runners; this module owns only the contract so that the lab and the
platform agree on the canonical feature set without one importing
from the other.

Example::

    from protea_contracts.feature_registry import (
        Feature,
        FeatureRegistry,
    )

    REGISTRY = FeatureRegistry()
    REGISTRY.register(
        Feature(
            name="distance",
            family="knn",
            dtype="numeric",
            compute=lambda ctx, predictions: ...,
        )
    )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

FeatureDtype = Literal["numeric", "categorical"]


@dataclass(frozen=True)
class Feature:
    """A single column the platform may compute per (query, candidate) row.

    Attributes:
        name: column name as it appears in the parquet dump and in the
            booster's ``feature_name`` list.
        family: logical group (``"knn"``, ``"alignment"``, ``"taxonomy"``,
            ``"anc2vec"``, ``"emb_pca"``, ``"annotation_meta"``). The
            registry uses this to dispatch family-level on/off toggles.
        dtype: ``"numeric"`` or ``"categorical"``. Categorical features
            are encoded once on the lab side and the codes ride
            alongside.
        compute: callable that fills the column. Signature is intentionally
            loose: ``compute(ctx, predictions) -> None`` mutating
            ``predictions`` in place. ``ctx`` carries the query, the
            references, KNN result, anc2vec index, etc.
    """

    name: str
    family: str
    dtype: FeatureDtype
    compute: Callable[[Any, Any], None]


class FeatureRegistry(ABC):
    """Contract for the in-process feature registry.

    Implementations are typically a single global instance built at
    import time in ``protea-core/protea/core/features/registry.py``.
    """

    @abstractmethod
    def register(self, feature: Feature) -> None:
        """Add a feature to the registry. Re-registering an existing
        ``name`` should raise ``ValueError`` so a typo never silently
        shadows a canonical column."""
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str) -> Feature:
        """Return the :class:`Feature` registered under ``name``.

        Raises:
            KeyError: if ``name`` is not registered.
        """
        raise NotImplementedError

    @abstractmethod
    def names(self) -> list[str]:
        """All registered feature names, in registration order."""
        raise NotImplementedError

    @abstractmethod
    def families(self) -> dict[str, list[str]]:
        """Map each family to the list of feature names that belong to it."""
        raise NotImplementedError

    @abstractmethod
    def selected(
        self,
        active_families: list[str],
        drop: list[str] | None = None,
    ) -> list[Feature]:
        """Return the subset of features that should be computed.

        Args:
            active_families: families to include.
            drop: explicit feature names to exclude even if their
                family is active. ``None`` is equivalent to ``[]``.
        """
        raise NotImplementedError
