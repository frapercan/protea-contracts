"""Pure-function biology utilities.

This module hosts string-level helpers used by both PROTEA's ORM
layer and ``protea-sources`` plugins:

* :func:`parse_isoform` — split a UniProt accession like ``"P12345-2"``
  into ``(canonical, is_canonical, isoform_index)``.
* :func:`compute_sequence_hash` — MD5 dedup hash for a protein
  sequence string.

Both functions are pure (no I/O, no DB, no globals). They live in
``protea-contracts`` so the FASTA parser in ``protea-sources`` can
populate ``UniProtProteinRecord.canonical_accession`` and
``.sequence_hash`` without inverting the C-stack dependency direction.

The canonical authority for these computations was previously
``Protein.parse_isoform`` and ``Sequence.compute_hash`` on PROTEA's
ORM models. Those classmethods now forward to the functions here, so
existing call sites keep working unchanged.

Why ``protea-contracts`` and not a new ``protea-biotools`` package
(D-MIGR-04 of master plan v3): the function set is small (today
two functions, one-year horizon ~100-300 LOC) and tightly coupled
with the records that consume them. A separate package would be
overhead for the volume. The escape hatch is cheap — if this module
grows past ~300 LOC or starts needing non-trivial deps (biopython,
etc.), extraction is one ``poetry add`` plus a single import-line
bump per consumer.
"""

from __future__ import annotations

import hashlib


def parse_isoform(accession: str) -> tuple[str, bool, int | None]:
    """Split a UniProt accession into canonical, is-canonical, isoform-index.

    The UniProt isoform pattern is ``<canonical>-<n>`` where ``n`` is
    a positive integer (e.g. ``"P12345-2"``). Plain accessions
    (``"P12345"``) are treated as canonical with isoform index ``None``.

    Edge cases:

    * ``"P12345-X"`` (non-numeric suffix): treated as a plain
      accession, *not* an isoform. Canonical is the full string.
    * ``"P12345-2-3"`` (multiple dashes): ``rsplit("-", 1)`` consumes
      only the last segment. If ``"3"`` is numeric, this is parsed
      as canonical=``"P12345-2"``, isoform_index=3. This matches the
      legacy ``Protein.parse_isoform`` behaviour.

    Returns:
        A 3-tuple ``(canonical_accession, is_canonical, isoform_index)``
        where ``isoform_index`` is ``None`` when ``is_canonical`` is
        ``True``.
    """
    if "-" in accession:
        left, right = accession.rsplit("-", 1)
        if right.isdigit():
            return left, False, int(right)
    return accession, True, None


def compute_sequence_hash(seq: str) -> str:
    """Return the MD5 dedup hash of a protein sequence string.

    The hash is the dedup key for the protein-sequence table; it is
    *not* a security primitive. MD5 collision resistance is irrelevant
    here — we only need a stable 32-hex digest. ``usedforsecurity=False``
    silences hash-related security linters.
    """
    return hashlib.md5(seq.encode("utf-8"), usedforsecurity=False).hexdigest()
