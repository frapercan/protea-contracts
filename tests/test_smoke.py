"""Smoke tests for the protea-contracts bootstrap."""

from __future__ import annotations

import protea_contracts


def test_version_is_string() -> None:
    assert isinstance(protea_contracts.__version__, str)


def test_version_is_semver_compatible() -> None:
    parts = protea_contracts.__version__.split(".")
    assert len(parts) == 3
    for p in parts:
        assert p.isdigit(), f"non-numeric SemVer component: {p!r}"


def test_no_platform_imports_leak() -> None:
    """Hard rule: importing protea_contracts must not pull in
    sqlalchemy / fastapi / torch / protea-core."""
    import sys

    forbidden = {"sqlalchemy", "fastapi", "torch", "protea_core"}
    leaked = forbidden & set(sys.modules)
    assert not leaked, f"Forbidden modules leaked into sys.modules: {leaked}"
