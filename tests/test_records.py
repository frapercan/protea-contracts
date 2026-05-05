"""Tests for source-side data contracts (stream payloads + records)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from protea_contracts.records import GoaAnnotationRecord, GoaStreamPayload


class TestGoaStreamPayload:
    def test_minimal_required_fields_construct(self) -> None:
        payload = GoaStreamPayload(gaf_url="https://example.com/x.gaf")
        assert payload.gaf_url == "https://example.com/x.gaf"
        assert payload.timeout_seconds == 300

    def test_explicit_timeout(self) -> None:
        payload = GoaStreamPayload(
            gaf_url="https://example.com/x.gaf.gz", timeout_seconds=600
        )
        assert payload.timeout_seconds == 600

    def test_payload_is_frozen(self) -> None:
        payload = GoaStreamPayload(gaf_url="https://example.com/x.gaf")
        with pytest.raises(ValidationError):
            payload.gaf_url = "https://other.com/x.gaf"  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            GoaStreamPayload(
                gaf_url="https://example.com/x.gaf",
                gaf_uri="oops typo",  # type: ignore[call-arg]
            )

    def test_missing_gaf_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoaStreamPayload()  # type: ignore[call-arg]

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoaStreamPayload(gaf_url="x", timeout_seconds=0)

    def test_negative_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoaStreamPayload(gaf_url="x", timeout_seconds=-5)


class TestGoaAnnotationRecord:
    def test_minimal_required_fields_construct(self) -> None:
        record = GoaAnnotationRecord(accession="P12345", go_id="GO:0000001")
        assert record.accession == "P12345"
        assert record.go_id == "GO:0000001"
        assert record.qualifier is None
        assert record.evidence_code is None

    def test_full_fields_construct(self) -> None:
        record = GoaAnnotationRecord(
            accession="P12345",
            go_id="GO:0000001",
            qualifier="involved_in",
            evidence_code="IDA",
            db_reference="PMID:12345",
            with_from="UniProtKB:Q99999",
            assigned_by="UniProtKB",
            annotation_date="20240115",
        )
        assert record.evidence_code == "IDA"
        assert record.assigned_by == "UniProtKB"

    def test_record_is_frozen(self) -> None:
        record = GoaAnnotationRecord(accession="P12345", go_id="GO:0000001")
        with pytest.raises(ValidationError):
            record.accession = "Q67890"  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            GoaAnnotationRecord(
                accession="P12345",
                go_id="GO:0000001",
                unknown_field="x",  # type: ignore[call-arg]
            )

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoaAnnotationRecord(accession="P12345")  # type: ignore[call-arg]

    def test_strict_type_enforcement(self) -> None:
        # strict mode rejects implicit coercion; ints don't auto-convert to str.
        with pytest.raises(ValidationError):
            GoaAnnotationRecord(accession=12345, go_id="GO:0000001")  # type: ignore[arg-type]

    def test_record_is_hashable(self) -> None:
        # frozen=True implies __hash__ is defined for set/dict membership.
        a = GoaAnnotationRecord(accession="P12345", go_id="GO:0000001")
        b = GoaAnnotationRecord(accession="P12345", go_id="GO:0000001")
        assert {a, b} == {a}

    def test_records_compare_by_value(self) -> None:
        a = GoaAnnotationRecord(accession="P12345", go_id="GO:0000001")
        b = GoaAnnotationRecord(accession="P12345", go_id="GO:0000001")
        c = GoaAnnotationRecord(accession="P99999", go_id="GO:0000001")
        assert a == b
        assert a != c
