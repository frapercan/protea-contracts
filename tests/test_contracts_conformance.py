"""Self-conformance suite for the protea-contracts package.

The plugin repos (protea-runners, protea-sources, protea-backends) each
ship a ``tests/test_contract_compliance.py`` that loads their
``entry_points`` and asserts every plugin satisfies the corresponding
ABC from this package. protea-contracts itself has no plugins to load;
the symmetric guard here is that every ABC it ships must carry a
non-empty docstring on the class itself AND on every abstract method,
so the surface stays self-documenting even as new ABCs land.

This is the dual of ``test_feature_producer_coverage.py``: that one
catches drift in the column set, this one catches drift in the API
surface. Both run in O(1) seconds and fail loud on the contracts PR
rather than waiting for a downstream consumer to break.
"""

from __future__ import annotations

import inspect
from abc import ABC

import protea_contracts
from protea_contracts.annotation_source import AnnotationSource
from protea_contracts.embedding_backend import EmbeddingBackend
from protea_contracts.experiment_runner import ExperimentRunner
from protea_contracts.feature_registry import FeatureRegistry

#: ABCs that downstream plugin packs implement. Pin-test target: if a
#: new ABC is added to the contracts surface, add it here so the
#: docstring sweep covers it.
PUBLIC_ABCS: tuple[type[ABC], ...] = (
    AnnotationSource,
    EmbeddingBackend,
    ExperimentRunner,
    FeatureRegistry,
)

#: Stack-side packages that consume the contracts. The conformance test
#: asserts each is referenced somewhere in the contracts source so a
#: future "dead ABC" rot (ABC removed from the stack but still shipped
#: here) is at least flagged in the README / module docstrings.
EXPECTED_CONSUMERS: tuple[str, ...] = (
    "protea-runners",
    "protea-sources",
    "protea-backends",
)


def test_every_public_abc_has_class_docstring() -> None:
    """Every ABC in PUBLIC_ABCS must carry a non-empty class docstring.

    Catches the case where a new ABC lands without any consumer-facing
    semantics; downstream plugin authors need the docstring to know
    what they are subclassing.
    """
    for abc_cls in PUBLIC_ABCS:
        doc = inspect.getdoc(abc_cls)
        assert doc and doc.strip(), (
            f"{abc_cls.__name__} has no class docstring; "
            "plugin authors need it to understand the contract."
        )


def test_every_abstract_method_has_docstring() -> None:
    """Every ``@abstractmethod`` on the public ABCs must be documented.

    Catches the case where a new abstract method is added without
    semantics; downstream plugins would have to read the source of
    the abstract method to know what to implement.
    """
    missing: list[str] = []
    for abc_cls in PUBLIC_ABCS:
        for name in getattr(abc_cls, "__abstractmethods__", frozenset()):
            method = getattr(abc_cls, name, None)
            if method is None:
                missing.append(f"{abc_cls.__name__}.{name} (not found)")
                continue
            doc = inspect.getdoc(method)
            if not doc or not doc.strip():
                missing.append(f"{abc_cls.__name__}.{name}")
    assert not missing, (
        "Abstract methods missing docstrings: "
        + ", ".join(missing)
        + ". Plugin authors rely on these docs to know what to implement."
    )


def test_every_public_abc_is_exported_at_package_root() -> None:
    """Every ABC must be re-exported from the top-level ``protea_contracts``.

    Catches the case where a new ABC is shipped in a submodule but
    forgotten from ``__init__.py``; consumers would have to import
    by submodule path, which the canonical examples (LightgbmRunner,
    EsmBackend, GoaSource) do not do.
    """
    for abc_cls in PUBLIC_ABCS:
        attr = getattr(protea_contracts, abc_cls.__name__, None)
        assert attr is abc_cls, (
            f"{abc_cls.__name__} is not re-exported from protea_contracts; "
            "add it to src/protea_contracts/__init__.py."
        )
        assert abc_cls.__name__ in protea_contracts.__all__, (
            f"{abc_cls.__name__} is not in protea_contracts.__all__; "
            "add it so star-imports and IDEs surface the symbol."
        )


def test_expected_consumers_are_referenced_in_source() -> None:
    """Every EXPECTED_CONSUMERS package name must appear in the contracts surface.

    Pin-test that catches "dead ABC" rot: if the contracts package ever
    drops mention of a consumer (e.g., protea-backends is removed from
    the stack), this test fails and the deletion of the corresponding
    ABC + its entry_points group should be considered. Implemented as a
    source-grep so it doesn't require importing the consumer packages
    (they are not test-time deps of protea-contracts).
    """
    src_root = inspect.getsourcefile(protea_contracts)
    assert src_root is not None
    from pathlib import Path

    contracts_dir = Path(src_root).parent
    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in contracts_dir.rglob("*.py")
    )
    for consumer in EXPECTED_CONSUMERS:
        # Module docstrings reference consumers as ``protea-runners`` /
        # ``protea_runners``; tolerate either spelling.
        underscore = consumer.replace("-", "_")
        assert consumer in blob or underscore in blob, (
            f"Consumer {consumer!r} is not referenced anywhere in the "
            "protea-contracts source; either re-document the ABC it "
            "feeds or remove the ABC + entry_points group as dead code."
        )
