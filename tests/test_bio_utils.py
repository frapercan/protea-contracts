"""Tests for the pure-function bio utilities."""

from __future__ import annotations

import hashlib

from protea_contracts.bio_utils import compute_sequence_hash, parse_isoform


class TestParseIsoform:
    def test_canonical_accession_returns_self_and_none(self) -> None:
        canonical, is_canonical, idx = parse_isoform("P12345")
        assert canonical == "P12345"
        assert is_canonical is True
        assert idx is None

    def test_isoform_pattern_splits(self) -> None:
        canonical, is_canonical, idx = parse_isoform("P12345-2")
        assert canonical == "P12345"
        assert is_canonical is False
        assert idx == 2

    def test_isoform_index_can_be_multidigit(self) -> None:
        canonical, _, idx = parse_isoform("Q9Y6K9-12")
        assert canonical == "Q9Y6K9"
        assert idx == 12

    def test_non_numeric_suffix_treated_as_canonical(self) -> None:
        # "P12345-X" is not a UniProt isoform — the suffix isn't a
        # positive integer. The accession is treated as canonical.
        canonical, is_canonical, idx = parse_isoform("P12345-X")
        assert canonical == "P12345-X"
        assert is_canonical is True
        assert idx is None

    def test_multiple_dashes_splits_only_last(self) -> None:
        # rsplit("-", 1) consumes only the trailing segment.
        canonical, is_canonical, idx = parse_isoform("ABC-DEF-3")
        assert canonical == "ABC-DEF"
        assert is_canonical is False
        assert idx == 3

    def test_dash_only_falls_back_to_canonical(self) -> None:
        # Pathological input: "-" alone. rsplit yields ("", ""); "" is
        # not isdigit, so this is treated as canonical.
        canonical, is_canonical, idx = parse_isoform("-")
        assert canonical == "-"
        assert is_canonical is True
        assert idx is None

    def test_empty_accession_treated_as_canonical(self) -> None:
        canonical, is_canonical, idx = parse_isoform("")
        assert canonical == ""
        assert is_canonical is True
        assert idx is None


class TestComputeSequenceHash:
    def test_returns_md5_hex_digest(self) -> None:
        result = compute_sequence_hash("MKTAYIAK")
        # Reference MD5 of the same bytes computed independently.
        expected = hashlib.md5(b"MKTAYIAK", usedforsecurity=False).hexdigest()
        assert result == expected
        assert len(result) == 32

    def test_deterministic(self) -> None:
        a = compute_sequence_hash("ACDEFGHIKLMNPQRSTVWY")
        b = compute_sequence_hash("ACDEFGHIKLMNPQRSTVWY")
        assert a == b

    def test_different_sequences_different_hashes(self) -> None:
        a = compute_sequence_hash("MKTAYIAK")
        b = compute_sequence_hash("MKTAYIAL")  # one residue diff
        assert a != b

    def test_empty_sequence_hashable(self) -> None:
        # Edge: empty sequences shouldn't crash; the dedup table can
        # still distinguish them by hash.
        result = compute_sequence_hash("")
        assert result == hashlib.md5(b"", usedforsecurity=False).hexdigest()

    def test_handles_non_ascii_residues(self) -> None:
        # Defensive: real protein sequences are ASCII, but the
        # function should not crash on UTF-8 input.
        result = compute_sequence_hash("MKTÄ")
        assert len(result) == 32
