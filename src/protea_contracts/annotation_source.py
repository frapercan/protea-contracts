"""Contract for annotation source plugins.

A plugin in ``protea-sources`` (e.g. ``goa``, ``quickgo``, ``uniprot``)
implements ``AnnotationSource`` and registers itself via the
``protea.sources`` ``entry_points`` group. ``protea-core`` discovers
the plugin at startup and dispatches load requests by ``name``.

Example::

    from protea_contracts.annotation_source import AnnotationSource

    class GOASource(AnnotationSource):
        name = "goa"
        version = "GOA/UniProt-230"

        def load(self, session, payload, *, emit):
            # Download the GAF, parse, populate AnnotationSet rows...
            return {"rows_inserted": 12345}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AnnotationSource(ABC):
    """Contract for a plugin that loads annotations into the platform.

    Implementations live in ``protea-sources``. Each plugin provides
    a stable ``name`` (used for routing), a human-readable ``version``
    (used in audit logs and dataset manifests), and a ``load`` method
    that runs the source-specific download / parse / insert pipeline.

    Subclasses MUST set ``name`` as a class attribute. ``version`` may
    be a class attribute or a property when the version is resolved
    dynamically (e.g. read from a downloaded release header).
    """

    name: str
    """Stable string identifier used by ``protea-core`` to dispatch."""

    version: str
    """Human-readable version of the source (e.g. ``"GOA/UniProt-230"``).

    Stored in ``AnnotationSet.source_version`` so a prediction set can
    always be traced back to the exact source release that produced it.
    """

    @abstractmethod
    def load(
        self,
        session: Any,
        payload: dict[str, Any],
        *,
        emit: Any,
    ) -> dict[str, Any]:
        """Run the load pipeline for this source.

        Args:
            session: SQLAlchemy session passed by ``protea-core``.
                Typed as ``Any`` here because ``protea-contracts``
                cannot import sqlalchemy. Implementations narrow it to
                ``sqlalchemy.orm.Session``.
            payload: Source-specific configuration validated by the
                implementation (typically a pydantic model dump).
            emit: Structured-event callback the platform provides; same
                signature as ``protea-core``'s ``EmitFn``. Implementations
                use it to surface progress.

        Returns:
            Free-form dict with summary statistics (counts, timings,
            anomalies) that ``protea-core`` stores as the resulting
            ``Job.meta``.
        """
        raise NotImplementedError
