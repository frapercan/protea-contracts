"""Tests for the AnnotationSource ABC."""

from __future__ import annotations

from protea_contracts import AnnotationSource


class _FakeSource(AnnotationSource):
    """Minimal valid implementation used to exercise the contract."""

    name = "fake"
    version = "0.0.0-test"


class TestAnnotationSourceContract:
    def test_concrete_subclass_can_be_instantiated(self) -> None:
        src = _FakeSource()
        assert src.name == "fake"
        assert src.version == "0.0.0-test"

    def test_isinstance_check_recognises_subclass(self) -> None:
        # The ABC is a marker after D-MIGR-06: no abstract methods,
        # so any subclass setting name + version qualifies as an
        # AnnotationSource for dispatch / discovery purposes.
        assert isinstance(_FakeSource(), AnnotationSource)

    def test_class_attributes_typed(self) -> None:
        # Both attributes are declared but not enforced at instantiation
        # (Python doesn't run class-attribute annotations as runtime
        # assertions). The contract relies on subclasses setting them.
        src = _FakeSource()
        assert isinstance(src.name, str)
        assert isinstance(src.version, str)
