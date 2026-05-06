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


class UniProtFastaStreamPayload(BaseModel):
    """Input payload for :meth:`protea_sources.uniprot.UniProtSource.stream_fasta`.

    UniProt's REST search endpoint (``/uniprotkb/search?format=fasta``)
    returns paginated FASTA data with cursor-based pagination via the
    ``Link: ...; rel="next"`` HTTP header. The plugin handles the
    cursor extraction and HTTP retry/backoff with jitter; the operation
    owns batching policy, deduplication, and persistence.

    The retry knobs (``max_retries``, ``backoff_base_seconds``,
    ``backoff_max_seconds``, ``jitter_seconds``) are part of the
    plugin contract because UniProt's rate-limit and 5xx-error
    behaviour vary by query and time of day; production runs need
    to tune them per workload.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    search_criteria: str
    """UniProtKB search query (e.g. ``"reviewed:true AND organism_id:9606"``)."""

    page_size: int = Field(default=500, gt=0)
    """Records per page (UniProt caps at ~500 for FASTA format)."""

    timeout_seconds: int = Field(default=60, gt=0)
    """HTTP request timeout."""

    include_isoforms: bool = True
    """When True, adds ``includeIsoform=true`` to the query string so
    UniProt returns ``<canonical>-<n>`` accessions alongside canonicals."""

    compressed: bool = False
    """When True, requests gzip-compressed FASTA via ``compressed=true``
    and decompresses on receipt."""

    max_retries: int = Field(default=6, gt=0)
    """Maximum retry attempts on 429 / 5xx / network errors."""

    backoff_base_seconds: float = Field(default=0.8, ge=0.0)
    """Exponential-backoff base; wait grows as ``base * 2**(attempt-1)``."""

    backoff_max_seconds: float = Field(default=20.0, ge=0.0)
    """Cap on backoff wait so a long retry doesn't dominate the run."""

    jitter_seconds: float = Field(default=0.4, ge=0.0)
    """Random uniform jitter added to each backoff sleep."""

    user_agent: str = "protea-sources/uniprot (contact: you@example.org)"
    """User-Agent header (UniProt asks integrators to identify themselves)."""

    base_url: str = "https://rest.uniprot.org/uniprotkb/search"
    """Search endpoint URL. Override only for testing or mirrors."""


class UniProtProteinRecord(BaseModel):
    """One protein record parsed from a UniProt FASTA response.

    Field set mirrors the canonical UniProt FASTA header layout
    (``sp|<accession>|<entry_name> <description> OS=... OX=... GN=...``)
    plus the sequence body. The plugin handles isoform splitting via
    :func:`protea_contracts.parse_isoform` and sequence hashing via
    :func:`protea_contracts.compute_sequence_hash` so the record is
    immediately persistable by the operation without further computation.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    accession: str
    """UniProt accession (canonical or isoform form)."""

    entry_name: str | None = None
    """UniProt entry name (e.g. ``"FOO_HUMAN"``); None for malformed headers."""

    canonical_accession: str
    """Canonical accession (always the bare ID without the ``-N`` suffix)."""

    is_canonical: bool
    """True iff ``accession == canonical_accession``."""

    isoform_index: int | None = None
    """Isoform number when the accession matches ``<canonical>-<n>``."""

    organism: str | None = None
    """Organism string from the ``OS=`` marker."""

    taxonomy_id: str | None = None
    """NCBI taxonomy ID from the ``OX=`` marker."""

    gene_name: str | None = None
    """Gene symbol from the ``GN=`` marker."""

    reviewed: bool
    """True iff the FASTA header starts with ``sp|`` (Swiss-Prot)."""

    sequence: str
    """Amino-acid sequence (whitespace stripped, uppercase as received)."""

    length: int = Field(gt=0)
    """Length of ``sequence`` in residues."""

    sequence_hash: str
    """MD5 hex digest of the sequence (32 chars). Dedup key for the
    sequence table; computed via :func:`compute_sequence_hash`."""


class UniProtMetadataStreamPayload(BaseModel):
    """Input payload for :meth:`protea_sources.uniprot.UniProtSource.stream_metadata`.

    UniProt's REST search endpoint serves TSV via
    ``format=tsv&fields=<comma-separated-list>``. The plugin owns
    cursor-based pagination and HTTP retries (sharing the same
    ``_http.py`` retry client as :meth:`stream_fasta`); the operation
    owns the field list (it's a persistence concern: which TSV columns
    map to which DB columns) and the per-row column-to-DB-col mapping.

    The ``fields`` knob accepts the UniProt field names verbatim
    (e.g. ``"accession"``, ``"protein_name"``, ``"ft_act_site"``) —
    not the human header names (``"Entry"``, ``"Protein names"``,
    ``"Active site"``). UniProt's TSV header row carries the human
    names; the operation maps them via its ``FIELD_MAP`` constant.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    search_criteria: str
    """UniProtKB search query (e.g. ``"reviewed:true AND organism_id:9606"``)."""

    fields: list[str]
    """List of UniProt field identifiers to request (e.g.
    ``["accession", "reviewed", "protein_name", ...]``). Determines the
    TSV column set; the operation maps human-readable headers back to
    DB columns via its persistence-side mapping."""

    page_size: int = Field(default=500, gt=0)
    """Records per page."""

    timeout_seconds: int = Field(default=60, gt=0)
    """HTTP request timeout."""

    compressed: bool = True
    """When True, requests gzip-compressed TSV. Default ``True`` here
    (vs ``False`` for FASTA) because UniProt TSV responses are large
    and compression typically wins by ~5x."""

    max_retries: int = Field(default=6, gt=0)
    backoff_base_seconds: float = Field(default=0.8, ge=0.0)
    backoff_max_seconds: float = Field(default=20.0, ge=0.0)
    jitter_seconds: float = Field(default=0.4, ge=0.0)
    user_agent: str = "protea-sources/uniprot (contact: you@example.org)"
    base_url: str = "https://rest.uniprot.org/uniprotkb/search"


class UniProtMetadataRecord(BaseModel):
    """One TSV row parsed from a UniProt metadata response.

    The ``accession`` field carries the literal ``Entry`` cell (UniProt
    accession, possibly an isoform). ``raw_fields`` is a flow-through
    dict of all columns the request asked for, keyed by the
    human-readable TSV header (e.g. ``"Active site"``,
    ``"Protein names"``). The operation does the (TSV header → DB
    column) mapping itself because that mapping is a persistence
    detail, not a parser detail.

    The record stays minimal on purpose: a more typed shape (dedicated
    fields per metadata column) would couple the contract to the
    operation's ``FIELD_MAP`` constant, breaking the boundary the
    F2A.6-real plan establishes.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    accession: str
    """TSV column ``Entry`` — UniProt accession (canonical or isoform)."""

    raw_fields: dict[str, str]
    """All TSV columns of the row, keyed by the human-readable TSV
    header. Empty cells are normalised to ``""``, never ``None``."""


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
