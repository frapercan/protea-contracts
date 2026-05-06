"""Contract for annotation source plugins.

A plugin in ``protea-sources`` (e.g. ``goa``, ``quickgo``, ``uniprot``)
implements ``AnnotationSource`` and registers itself via the
``protea.sources`` ``entry_points`` group. ``protea-core`` discovers
the plugin at startup and dispatches load requests by ``name``.

The ABC is a *marker* contract: subclasses set ``name`` and ``version``
class attributes and add their own modality-specific methods (e.g.
:meth:`GoaSource.stream`, :meth:`UniProtSource.stream_fasta`,
:meth:`UniProtSource.stream_metadata`). There is intentionally no
single ``stream``/``load`` abstract method here because UniProt has
two distinct modalities (FASTA + metadata) and forcing a uniform
dispatch interface across all plugins would either obscure that fact
or push polymorphism overhead down the call path. Callers dispatch
via the plugin's class — :class:`isinstance` checks against the ABC
preserve "is this an annotation source plugin?" semantics without
requiring a shared method shape.

Example::

    from protea_contracts.annotation_source import AnnotationSource

    class MySource(AnnotationSource):
        name = "my_source"
        version = "1.0"

        def stream(self, payload, *, emit):
            # Source-specific yield-records implementation...
            ...
"""

from __future__ import annotations

from abc import ABC


class AnnotationSource(ABC):
    """Marker contract for an annotation source plugin.

    Subclasses MUST set ``name`` as a class attribute (used by
    ``protea-core`` to dispatch). ``version`` may be a class attribute
    or a property when the version is resolved dynamically (e.g. read
    from a downloaded release header).

    The ABC was reduced to a marker shape in D-MIGR-06 of master plan
    v3 once the F2A.6-real migration replaced the legacy ``load()``
    method with per-source modality-specific methods (``stream``,
    ``stream_fasta``, ``stream_metadata``, ``fetch_eco_mapping``).
    """

    name: str
    """Stable string identifier used by ``protea-core`` to dispatch."""

    version: str
    """Human-readable version of the source (e.g. ``"GOA/UniProt-230"``).

    Stored in ``AnnotationSet.source_version`` so a prediction set can
    always be traced back to the exact source release that produced it.
    """
