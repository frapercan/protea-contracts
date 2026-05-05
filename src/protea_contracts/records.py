"""Source-side data contracts: stream payloads and parsed-record types.

This module hosts the two kinds of pydantic types that cross the
plugin/operation boundary in ``protea-sources``:

* **Stream payloads** (e.g. :class:`GoaStreamPayload`): typed inputs
  to a plugin's ``stream(payload, *, emit)`` method. They replace the
  fragile ``dict[str, Any]`` payloads used during early F2A.6 dry-runs
  with a contract that catches typos at construction time.

* **Parsed records** (e.g. :class:`GoaAnnotationRecord`): immutable
  outputs yielded by the plugin and consumed by PROTEA's persistence
  adapter (``LoadGOAAnnotationsOperation`` etc.).

All types in this module share three properties:

* **Frozen + strict + extra="forbid"**: any drift between caller
  expectations and the plugin contract fails loud at the boundary.
* **String fields, no rich domain types**: payloads carry URLs and
  knobs; records carry the *literal* shape returned by the source
  format. Date parsing, ECO mapping, and FK resolution are the
  operation's job.
* **Sensible defaults**: payloads default to production values
  (300s timeout etc.); record optional fields default to None.

Future sources add their pair (``<Name>StreamPayload``,
``<Name>Record``) here as the F2A.6-real migration extracts each
parser (see ``f2a6_real_migration_design.md`` for the full plan).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GoaStreamPayload(BaseModel):
    """Input payload for :meth:`protea_sources.goa.GoaSource.stream`.

    Replaces the early ``dict[str, Any]`` shape with a typed contract.
    The PROTEA operation constructs it from its richer
    ``LoadGOAAnnotationsPayload`` (which also carries ``page_size``,
    ``commit_every_page``, etc. that are operation-level concerns and
    do not belong in the plugin payload).
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    gaf_url: str
    """URL of the GAF file. ``.gz`` suffix triggers gzip decompression."""

    timeout_seconds: int = Field(default=300, gt=0)
    """HTTP timeout in seconds. Must be positive."""


class QuickGoStreamPayload(BaseModel):
    """Input payload for :meth:`protea_sources.quickgo.QuickGoSource.stream`.

    QuickGO's bulk-download endpoint returns paginated TSV. The plugin
    handles batching on ``gene_product_ids`` to dodge URL-length 400
    errors; the operation owns the upstream decision of *which* IDs to
    feed (typically the canonical-accession universe from PROTEA's DB).
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    quickgo_base_url: str = (
        "https://www.ebi.ac.uk/QuickGO/services/annotation/downloadSearch"
    )
    """QuickGO bulk-download endpoint URL."""

    gene_product_ids: list[str] | None = None
    """Subset of accession IDs to filter on. ``None`` = full database
    (single unbatched request)."""

    gene_product_batch_size: int = Field(default=200, gt=0)
    """Per-batch size for ``geneProductId`` URL parameter. QuickGO
    rejects very long URLs with 400; 200 keeps the URL bounded."""

    timeout_seconds: int = Field(default=300, gt=0)
    """HTTP timeout in seconds."""


class EcoMappingPayload(BaseModel):
    """Input payload for :meth:`protea_sources.quickgo.QuickGoSource.fetch_eco_mapping`.

    The ECO-to-evidence-code map is an auxiliary fetch (D-MIGR-05): a
    small file (< 100 KB), single shot, returns an in-memory dict the
    operation can cache for the duration of a load.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    url: str
    """URL of the GAF ECO-mapping file (space-separated lines:
    ``ECO:XXXXXXX  CODE``)."""

    timeout_seconds: int = Field(default=60, gt=0)
    """HTTP timeout. Smaller default than stream() — this is a small
    file, not a multi-million-line stream."""


class QuickGoAnnotationRecord(BaseModel):
    """One annotation row parsed from a QuickGO TSV.

    Field names are the clean Python form of the QuickGO TSV column
    headers. The mapping is documented in
    :func:`protea_sources.quickgo.parse_quickgo_row`. The ``eco_id``
    field carries the raw ``ECO:XXXXXXX`` identifier; the operation
    resolves it to a CAFA evidence code (``IDA``, ``IEA``...) via the
    ECO mapping (or stores the raw ECO when no mapping is provided).
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    accession: str
    """TSV column ``GENE PRODUCT ID``."""

    go_id: str
    """TSV column ``GO TERM``."""

    qualifier: str | None = None
    """TSV column ``QUALIFIER`` (``enables``, ``involved_in``, ...)."""

    eco_id: str | None = None
    """TSV column ``ECO ID``. Raw form. Operation maps to
    ``evidence_code`` via ECO mapping fetch."""

    db_reference: str | None = None
    """TSV column ``REFERENCE``."""

    with_from: str | None = None
    """TSV column ``WITH/FROM``."""

    assigned_by: str | None = None
    """TSV column ``ASSIGNED BY``."""

    annotation_date: str | None = None
    """TSV column ``DATE``. Operation parses to date type."""


class GoaAnnotationRecord(BaseModel):
    """One annotation row parsed from a GAF (UniProt-GOA) line.

    Field names mirror the GAF 2.x column meanings (see
    http://geneontology.org/docs/go-annotation-file-gaf-format-2.2/);
    column indices live in the GoaSource parser, not here. The
    operation does the (accession ∈ valid_accessions) filter and the
    (go_id → go_term_id) resolution before bulk insert.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    accession: str
    """GAF column 2 — DB Object ID (UniProt accession or canonical form)."""

    go_id: str
    """GAF column 5 — GO term identifier (e.g. ``GO:0000123``)."""

    qualifier: str | None = None
    """GAF column 4 — qualifier (``involved_in``, ``contributes_to``, ...)."""

    evidence_code: str | None = None
    """GAF column 7 — three-letter evidence code (``IDA``, ``IEA``, ...).

    Already resolved on the GAF side. QuickGO records carry ``eco_id``
    instead and require operation-side mapping.
    """

    db_reference: str | None = None
    """GAF column 6 — supporting reference (``PMID:12345``, ``GO_REF:0000033``)."""

    with_from: str | None = None
    """GAF column 8 — with/from field (curator-specified context)."""

    assigned_by: str | None = None
    """GAF column 15 — annotation source database (``UniProtKB``, ``GO_Central``)."""

    annotation_date: str | None = None
    """GAF column 14 — date in ``YYYYMMDD`` form (operation parses to date)."""
