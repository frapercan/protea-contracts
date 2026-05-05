"""Tests for protea_contracts.manifest (T1.3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from protea_contracts import (
    SCHEMA_VERSION,
    DatasetSpec,
    ManifestV1,
)


class TestDatasetSpec:
    def _build(self, **overrides: object) -> DatasetSpec:
        defaults: dict[str, object] = {
            "name": "study_v_thesis",
            "source_manifest": Path("/tmp/manifest.json"),
        }
        defaults.update(overrides)
        return DatasetSpec.model_validate(defaults)

    def test_defaults(self) -> None:
        s = self._build()
        assert s.format == "parquet"
        assert s.seed == 42
        assert s.enabled_feature_families is None
        assert s.drop_features == []

    def test_unknown_family_raises(self) -> None:
        with pytest.raises(ValidationError):
            self._build(enabled_feature_families=["does_not_exist"])

    def test_known_family_accepted(self) -> None:
        s = self._build(enabled_feature_families=["knn", "alignment_nw"])
        assert s.enabled_feature_families == ["knn", "alignment_nw"]

    def test_hash_excludes_name_and_source_manifest(self) -> None:
        a = self._build(name="alpha", source_manifest=Path("/tmp/a.json"))
        b = self._build(name="beta", source_manifest=Path("/tmp/b.json"))
        # Same logical spec, different label / path: same hash.
        assert a.hash() == b.hash()

    def test_hash_changes_with_seed(self) -> None:
        a = self._build(seed=42)
        b = self._build(seed=43)
        assert a.hash() != b.hash()

    def test_hash_returns_12_hex(self) -> None:
        s = self._build()
        h = s.hash()
        assert len(h) == 12
        int(h, 16)

    def test_frozen(self) -> None:
        s = self._build()
        with pytest.raises(ValidationError):
            s.seed = 99  # type: ignore[misc]


class TestManifestV1:
    def _build(self, **overrides: object) -> ManifestV1:
        defaults: dict[str, object] = {
            "name": "study_v_thesis",
            "k": 5,
            "embedding_config_id": "00000000-0000-0000-0000-000000000001",
            "ontology_snapshot_id": "00000000-0000-0000-0000-000000000002",
            "train_snapshot_pairs": ["220-221", "221-222"],
            "eval_snapshot_pair": "229-230",
            "schema_sha": "145592ed186c",
        }
        defaults.update(overrides)
        return ManifestV1.model_validate(defaults)

    def test_defaults(self) -> None:
        m = self._build()
        assert m.schema_version == SCHEMA_VERSION
        assert m.format == "parquet"
        assert m.n_train_rows is None
        assert m.spec_hash is None

    def test_extra_fields_ignored(self) -> None:
        m = ManifestV1.model_validate(
            {
                "name": "x",
                "k": 5,
                "embedding_config_id": "ec",
                "ontology_snapshot_id": "os",
                "train_snapshot_pairs": ["a"],
                "eval_snapshot_pair": "b",
                "schema_sha": "abc",
                # Extra fields a future version might add: should be silently ignored.
                "future_field": "ignored",
            }
        )
        assert m.k == 5

    def test_dump_and_load_roundtrip(self, tmp_path: Path) -> None:
        m = self._build()
        out = tmp_path / "manifest.json"
        m.dump(out)
        loaded = ManifestV1.load(out)
        assert loaded.name == m.name
        assert loaded.schema_sha == m.schema_sha
        assert loaded.train_snapshot_pairs == m.train_snapshot_pairs

    def test_load_supplies_default_schema_version(self, tmp_path: Path) -> None:
        out = tmp_path / "manifest.json"
        out.write_text(
            '{"name": "x", "k": 5, "embedding_config_id": "ec", '
            '"ontology_snapshot_id": "os", "train_snapshot_pairs": ["a"], '
            '"eval_snapshot_pair": "b", "schema_sha": "abc"}'
        )
        loaded = ManifestV1.load(out)
        assert loaded.schema_version == SCHEMA_VERSION
