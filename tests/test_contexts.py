"""Tests for protea_contracts.contexts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest

from protea_contracts.contexts import (
    ExportContext,
    ExportSink,
    FeatureBuildContext,
    KnnContext,
)


class TestKnnContext:
    def test_minimal_inference(self) -> None:
        ctx = KnnContext(
            query_accessions=["P12345", "Q67890"],
            query_embeddings=np.zeros((2, 480), dtype=np.float32),
        )
        assert ctx.query_accessions == ["P12345", "Q67890"]
        assert ctx.query_embeddings.shape == (2, 480)
        assert ctx.query_known_gos is None
        assert ctx.ref_data is None
        assert ctx.neighbors is None

    def test_training_path(self) -> None:
        ctx = KnnContext(
            query_accessions=["P12345"],
            query_embeddings=np.zeros((1, 320)),
            query_known_gos={"P12345": {"GO:0008150"}},
        )
        assert ctx.query_known_gos == {"P12345": {"GO:0008150"}}

    def test_with_precomputed_neighbors(self) -> None:
        ctx = KnnContext(
            query_accessions=["P1"],
            query_embeddings=np.zeros((1, 320)),
            neighbors=[[("R1", 0.12), ("R2", 0.18)]],
        )
        assert ctx.neighbors is not None
        assert ctx.neighbors[0][0] == ("R1", 0.12)

    def test_frozen(self) -> None:
        ctx = KnnContext(
            query_accessions=["P12345"],
            query_embeddings=np.zeros((1, 320)),
        )
        with pytest.raises(FrozenInstanceError):
            ctx.query_accessions = ["Q1"]  # type: ignore[misc]

    def test_slots_no_dict(self) -> None:
        ctx = KnnContext(
            query_accessions=["P12345"],
            query_embeddings=np.zeros((1, 320)),
        )
        with pytest.raises(AttributeError):
            _ = ctx.__dict__


class TestFeatureBuildContext:
    def test_all_defaults(self) -> None:
        ctx = FeatureBuildContext()
        assert ctx.ia_weights is None
        assert ctx.pca_state is None
        assert ctx.embedding_pool is None
        assert ctx.pivot_go_ids is None
        assert ctx.parent_map is None
        assert ctx.go_id_map is None
        assert ctx.aspect_map is None
        assert ctx.gt_pairs is None

    def test_pca_state_pair_shapes(self) -> None:
        mean = np.zeros((480,), dtype=np.float32)
        components = np.eye(64, 480, dtype=np.float32)
        ctx = FeatureBuildContext(pca_state=(mean, components))
        assert ctx.pca_state is not None
        assert ctx.pca_state[0].shape == (480,)
        assert ctx.pca_state[1].shape == (64, 480)

    def test_pivot_set_is_frozenset(self) -> None:
        ctx = FeatureBuildContext(pivot_go_ids=frozenset({"GO:0008150"}))
        assert isinstance(ctx.pivot_go_ids, frozenset)

    def test_parent_map_strings(self) -> None:
        parent_map = {"GO:0008150": frozenset({"GO:0003674"})}
        ctx = FeatureBuildContext(parent_map=parent_map)
        assert ctx.parent_map is not None
        assert "GO:0008150" in ctx.parent_map

    def test_frozen(self) -> None:
        ctx = FeatureBuildContext()
        with pytest.raises(FrozenInstanceError):
            ctx.ia_weights = {}  # type: ignore[misc]


def _export_ctx() -> ExportContext:
    return ExportContext(
        dump_dir=Path("/tmp/out"),
        name="reranker-v18",
        k=5,
        embedding_config_id="ec-1",
        ontology_snapshot_id="onto-220",
        annotation_source="goa",
        split_files={"train": [Path("train.parquet")]},
        valid_split_versions=[(220, 221)],
        test_files={"test": Path("test.parquet")},
        test_old_v=228,
        test_new_v=229,
    )


class TestExportContext:
    def test_construct(self) -> None:
        ctx = _export_ctx()
        assert ctx.k == 5
        assert ctx.test_new_v == 229
        assert ctx.split_files["train"][0].name == "train.parquet"

    def test_test_files_optional_value(self) -> None:
        ctx = ExportContext(
            dump_dir=Path("/tmp/out"),
            name="r",
            k=5,
            embedding_config_id="ec",
            ontology_snapshot_id="onto",
            annotation_source="goa",
            split_files={"train": []},
            valid_split_versions=[],
            test_files={"test": None},
            test_old_v=0,
            test_new_v=1,
        )
        assert ctx.test_files["test"] is None

    def test_frozen(self) -> None:
        ctx = _export_ctx()
        with pytest.raises(FrozenInstanceError):
            ctx.k = 10  # type: ignore[misc]


class TestExportSink:
    def test_default(self) -> None:
        sink = ExportSink()
        assert sink.key_prefix == ""
        assert sink.producer_version is None
        assert sink.producer_git_sha is None

    def test_with_provenance(self) -> None:
        sink = ExportSink(
            key_prefix="datasets/v18/",
            producer_version="0.8.0",
            producer_git_sha="abc1234",
        )
        assert sink.key_prefix == "datasets/v18/"
        assert sink.producer_version == "0.8.0"
        assert sink.producer_git_sha == "abc1234"

    def test_frozen(self) -> None:
        sink = ExportSink()
        with pytest.raises(FrozenInstanceError):
            sink.key_prefix = "x"  # type: ignore[misc]


class TestExportSeparation:
    """ExportContext and ExportSink are deliberately separate.

    The same source-side ``ExportContext`` should be re-usable across
    different sinks (local vs MinIO, dev vs prod), without copy-paste.
    """

    def test_same_ctx_different_sinks(self) -> None:
        ctx = _export_ctx()
        sink_local = ExportSink(key_prefix="local/")
        sink_minio = ExportSink(
            key_prefix="s3://bucket/datasets/",
            producer_version="0.8.0",
        )
        assert sink_local is not sink_minio
        assert sink_local.producer_version is None
        assert sink_minio.producer_version == "0.8.0"
        assert ctx.k == 5
