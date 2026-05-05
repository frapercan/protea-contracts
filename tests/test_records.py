"""Tests for source-side data contracts (stream payloads + records)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from protea_contracts.records import (
    EcoMappingPayload,
    GoaAnnotationRecord,
    GoaStreamPayload,
    QuickGoAnnotationRecord,
    QuickGoStreamPayload,
)


class TestQuickGoStreamPayload:
    def test_minimal_construct_defaults(self) -> None:
        payload = QuickGoStreamPayload()
        assert payload.gene_product_ids is None
        assert payload.gene_product_batch_size == 200
        assert payload.timeout_seconds == 300
        assert "ebi.ac.uk" in payload.quickgo_base_url

    def test_with_gp_ids(self) -> None:
        payload = QuickGoStreamPayload(
            gene_product_ids=["P12345", "Q99999"], gene_product_batch_size=50
        )
        assert payload.gene_product_ids == ["P12345", "Q99999"]
        assert payload.gene_product_batch_size == 50

    def test_payload_is_frozen(self) -> None:
        payload = QuickGoStreamPayload()
        with pytest.raises(ValidationError):
            payload.timeout_seconds = 9999  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            QuickGoStreamPayload(
                page_size=100,  # type: ignore[call-arg]
            )

    def test_zero_batch_size_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QuickGoStreamPayload(gene_product_batch_size=0)

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QuickGoStreamPayload(timeout_seconds=0)


class TestEcoMappingPayload:
    def test_required_url(self) -> None:
        payload = EcoMappingPayload(url="https://example.com/eco.txt")
        assert payload.url == "https://example.com/eco.txt"
        assert payload.timeout_seconds == 60

    def test_explicit_timeout(self) -> None:
        payload = EcoMappingPayload(url="x", timeout_seconds=30)
        assert payload.timeout_seconds == 30

    def test_payload_is_frozen(self) -> None:
        payload = EcoMappingPayload(url="x")
        with pytest.raises(ValidationError):
            payload.url = "y"  # type: ignore[misc]

    def test_missing_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EcoMappingPayload()  # type: ignore[call-arg]

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EcoMappingPayload(url="x", timeout_seconds=0)


class TestQuickGoAnnotationRecord:
    def test_minimal_required_fields(self) -> None:
        rec = QuickGoAnnotationRecord(accession="P12345", go_id="GO:0000001")
        assert rec.accession == "P12345"
        assert rec.eco_id is None

    def test_full_fields(self) -> None:
        rec = QuickGoAnnotationRecord(
            accession="P12345",
            go_id="GO:0000001",
            qualifier="enables",
            eco_id="ECO:0000314",
            db_reference="PMID:99999",
            with_from="UniProtKB:Q11111",
            assigned_by="UniProtKB",
            annotation_date="20240115",
        )
        assert rec.eco_id == "ECO:0000314"

    def test_record_is_frozen(self) -> None:
        rec = QuickGoAnnotationRecord(accession="P12345", go_id="GO:0000001")
        with pytest.raises(ValidationError):
            rec.accession = "Q67890"  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            QuickGoAnnotationRecord(
                accession="P12345",
                go_id="GO:0000001",
                evidence_code="IDA",  # type: ignore[call-arg]
            )

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QuickGoAnnotationRecord(accession="P12345")  # type: ignore[call-arg]


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
