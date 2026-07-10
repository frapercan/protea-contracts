"""Tests for the feature documentation registry (feature_docs.py).

The core test asserts zero drift between ``FEATURE_DOCS`` and the canonical
feature schema, so a missing or orphaned doc fails in ``pytest`` as well as in
``scripts/check_feature_docs.py``.
"""

from __future__ import annotations

from protea_contracts import FEATURE_DOCS, FeatureDoc, FeatureStatus
from protea_contracts.feature_schema import ALL_FEATURES, FEATURE_FAMILIES


class TestNoDrift:
    def test_every_declared_feature_has_a_doc(self) -> None:
        missing = sorted(set(ALL_FEATURES) - set(FEATURE_DOCS))
        assert not missing, f"declared features without a FeatureDoc: {missing}"

    def test_no_doc_names_an_undeclared_column(self) -> None:
        orphans = sorted(set(FEATURE_DOCS) - set(ALL_FEATURES))
        assert not orphans, f"FeatureDocs naming undeclared columns: {orphans}"

    def test_coverage_is_exact(self) -> None:
        assert set(FEATURE_DOCS) == set(ALL_FEATURES)

    def test_mapping_key_matches_doc_name(self) -> None:
        for key, doc in FEATURE_DOCS.items():
            assert key == doc.name

    def test_family_agrees_with_feature_families(self) -> None:
        for doc in FEATURE_DOCS.values():
            assert doc.family in FEATURE_FAMILIES, (
                f"{doc.name}: family {doc.family!r} is not a FEATURE_FAMILIES key"
            )
            assert doc.name in FEATURE_FAMILIES[doc.family], (
                f"{doc.name}: not listed under family {doc.family!r}"
            )

    def test_lint_reports_zero_errors(self) -> None:
        # Import the drift lint as the CI/pre-commit entrypoint does and
        # assert it agrees there is no drift.
        import importlib.util
        from pathlib import Path

        script = Path(__file__).resolve().parents[1] / "scripts" / "check_feature_docs.py"
        spec = importlib.util.spec_from_file_location("check_feature_docs", script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.check() == []


class TestDocContent:
    def test_all_docs_are_frozen_dataclasses(self) -> None:
        for doc in FEATURE_DOCS.values():
            assert isinstance(doc, FeatureDoc)

    def test_required_prose_fields_are_nonempty(self) -> None:
        for doc in FEATURE_DOCS.values():
            assert doc.summary.strip(), f"{doc.name}: empty summary"
            assert doc.definition.strip(), f"{doc.name}: empty definition"
            assert doc.producer.strip(), f"{doc.name}: empty producer"
            assert isinstance(doc.status, FeatureStatus)

    def test_six_lafa_columns_are_declared_absent(self) -> None:
        lafa = {
            "classifier_score",
            "classifier_present",
            "self_prior_score",
            "association_total",
            "association_cross",
            "association_present",
        }
        for name in lafa:
            assert FEATURE_DOCS[name].status is FeatureStatus.DECLARED_ABSENT, (
                f"{name} should be DECLARED_ABSENT per ADR-D45"
            )

    def test_docs_are_immutable(self) -> None:
        import dataclasses

        import pytest

        doc = next(iter(FEATURE_DOCS.values()))
        with pytest.raises(dataclasses.FrozenInstanceError):
            doc.summary = "mutated"  # type: ignore[misc]
