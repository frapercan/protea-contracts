"""Dataset spec and build manifest for frozen reranker dumps.

These are the contract artifacts written by the dataset producer
(``protea-core`` ``export_research_dataset`` operation) and consumed
by the lab side (``protea-runners.lightgbm``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from protea_contracts.feature_schema import FEATURE_FAMILIES, SCHEMA_VERSION


class DatasetSpec(BaseModel):
    """Hashable description of what the producer was asked to build.

    The hash of a :class:`DatasetSpec` is the canonical reproducibility
    key for a dump: the same spec on the same protea-contracts version
    must rebuild a parquet with an identical ``schema_sha``.
    """

    name: str
    source_manifest: Path
    enabled_feature_families: list[str] | None = None
    drop_features: list[str] = Field(default_factory=list)
    train_snapshot_pairs: list[str] | None = None
    eval_snapshot_pair: str | None = None
    format: Literal["parquet"] = "parquet"
    seed: int = 42

    model_config = ConfigDict(frozen=True)

    @field_validator("enabled_feature_families")
    @classmethod
    def _check_families(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        unknown = set(v) - set(FEATURE_FAMILIES)
        if unknown:
            raise ValueError(f"unknown feature families: {sorted(unknown)}")
        return v

    def hash(self) -> str:
        """Return a 12-hex digest of the spec for reproducibility logs.

        ``source_manifest`` and ``name`` are excluded so a dataset
        produced from the same upstream + parameters but with a
        different file path or human-readable name still hashes identically.
        """
        payload = self.model_dump(exclude={"source_manifest", "name"}, mode="json")
        blob = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]


class ManifestV1(BaseModel):
    """Written to ``<dataset_dir>/manifest.json`` after each successful build.

    The lab's ``pull_dataset.py`` resolves a dataset by id or name,
    downloads the parquets, validates this manifest against the
    expected schema_sha, and trains.
    """

    schema_version: str = SCHEMA_VERSION
    name: str
    k: int
    embedding_config_id: str
    ontology_snapshot_id: str
    annotation_source: str | None = None
    train_snapshot_pairs: list[str]
    eval_snapshot_pair: str
    schema_sha: str
    n_train_rows: int | None = None
    n_eval_rows: int | None = None
    format: Literal["parquet"] = "parquet"
    spec_hash: str | None = None
    parent_schema_sha: str | None = None
    feature_families: list[str] | None = None
    producer_version: str | None = None
    producer_git_sha: str | None = None

    model_config = ConfigDict(extra="ignore")

    @classmethod
    def load(cls, path: str | Path) -> ManifestV1:
        data: dict[str, Any] = json.loads(Path(path).read_text())
        data.setdefault("schema_version", SCHEMA_VERSION)
        return cls.model_validate(data)

    def dump(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2))
