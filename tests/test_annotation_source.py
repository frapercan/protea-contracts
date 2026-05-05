"""Tests for the AnnotationSource ABC."""

from __future__ import annotations

from typing import Any

import pytest

from protea_contracts import AnnotationSource


class _FakeSource(AnnotationSource):
    """Minimal valid implementation used to exercise the contract."""

    name = "fake"
    version = "0.0.0-test"

    def load(self, session: Any, payload: dict[str, Any], *, emit: Any) -> dict[str, Any]:
        return {"rows": 0}


class TestAnnotationSourceContract:
    def test_subclass_must_implement_load(self) -> None:
        class Bad(AnnotationSource):
            name = "bad"
            version = "0.0"

        with pytest.raises(TypeError):
            Bad()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        src = _FakeSource()
        assert src.name == "fake"
        assert src.version == "0.0.0-test"

    def test_load_returns_summary_dict(self) -> None:
        src = _FakeSource()
        out = src.load(session=None, payload={}, emit=lambda *a, **kw: None)
        assert isinstance(out, dict)
