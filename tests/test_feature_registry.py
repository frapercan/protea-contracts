"""Tests for the FeatureRegistry ABC and Feature dataclass."""

from __future__ import annotations

from typing import Any

import pytest

from protea_contracts import Feature, FeatureRegistry


class _DictRegistry(FeatureRegistry):
    """Trivial in-memory registry used to validate the contract."""

    def __init__(self) -> None:
        self._features: dict[str, Feature] = {}

    def register(self, feature: Feature) -> None:
        if feature.name in self._features:
            raise ValueError(f"feature already registered: {feature.name}")
        self._features[feature.name] = feature

    def get(self, name: str) -> Feature:
        return self._features[name]

    def names(self) -> list[str]:
        return list(self._features.keys())

    def families(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for f in self._features.values():
            out.setdefault(f.family, []).append(f.name)
        return out

    def selected(
        self,
        active_families: list[str],
        drop: list[str] | None = None,
    ) -> list[Feature]:
        drop_set = set(drop or [])
        return [
            f
            for f in self._features.values()
            if f.family in active_families and f.name not in drop_set
        ]


def _noop(_ctx: Any, _preds: Any) -> None:
    pass


class TestFeatureDataclass:
    def test_fields_and_frozen(self) -> None:
        f = Feature(name="distance", family="knn", dtype="numeric", compute=_noop)
        assert f.name == "distance"
        assert f.dtype == "numeric"
        with pytest.raises((AttributeError, TypeError)):
            f.name = "other"  # type: ignore[misc]


class TestFeatureRegistryContract:
    def test_subclass_must_implement_methods(self) -> None:
        class Partial(FeatureRegistry):
            def register(self, feature: Feature) -> None:
                pass

        with pytest.raises(TypeError):
            Partial()  # type: ignore[abstract]

    def test_register_and_get(self) -> None:
        reg = _DictRegistry()
        f = Feature(name="distance", family="knn", dtype="numeric", compute=_noop)
        reg.register(f)
        assert reg.get("distance") is f

    def test_double_register_raises(self) -> None:
        reg = _DictRegistry()
        f = Feature(name="distance", family="knn", dtype="numeric", compute=_noop)
        reg.register(f)
        with pytest.raises(ValueError):
            reg.register(f)

    def test_families_grouping(self) -> None:
        reg = _DictRegistry()
        reg.register(Feature("distance", "knn", "numeric", _noop))
        reg.register(Feature("k_position", "knn", "numeric", _noop))
        reg.register(Feature("identity_nw", "alignment", "numeric", _noop))
        fams = reg.families()
        assert set(fams.keys()) == {"knn", "alignment"}
        assert len(fams["knn"]) == 2
        assert fams["alignment"] == ["identity_nw"]

    def test_selected_filters_by_family_and_drop(self) -> None:
        reg = _DictRegistry()
        reg.register(Feature("distance", "knn", "numeric", _noop))
        reg.register(Feature("k_position", "knn", "numeric", _noop))
        reg.register(Feature("identity_nw", "alignment", "numeric", _noop))

        knn_only = reg.selected(["knn"])
        assert {f.name for f in knn_only} == {"distance", "k_position"}

        no_kpos = reg.selected(["knn"], drop=["k_position"])
        assert {f.name for f in no_kpos} == {"distance"}

        all_active = reg.selected(["knn", "alignment"])
        assert len(all_active) == 3
