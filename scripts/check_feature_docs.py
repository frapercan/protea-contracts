#!/usr/bin/env python3
"""Drift lint for the feature documentation registry.

Fails when :data:`protea_contracts.feature_docs.FEATURE_DOCS` and the canonical
feature schema disagree, so a new column can never ship without an operator-
facing :class:`~protea_contracts.feature_docs.FeatureDoc`, and a doc can never
name a column that no longer exists.

Checks:
  1. Coverage: every column in ``feature_schema.ALL_FEATURES`` has a doc.
  2. No orphans: every doc names a column that is declared in ``ALL_FEATURES``.
  3. Key integrity: each doc's mapping key equals ``doc.name``.
  4. Family agreement: each ``doc.family`` is a key of
     ``feature_schema.FEATURE_FAMILIES`` whose column list contains ``doc.name``.

Usage:
  python scripts/check_feature_docs.py
"""

from __future__ import annotations

import sys


def check() -> list[str]:
    """Return a list of human-readable drift errors (empty when clean)."""
    from protea_contracts.feature_docs import FEATURE_DOCS
    from protea_contracts.feature_schema import ALL_FEATURES, FEATURE_FAMILIES

    declared = set(ALL_FEATURES)
    documented = set(FEATURE_DOCS)
    errors: list[str] = []

    for col in sorted(declared - documented):
        errors.append(f"declared feature has no FeatureDoc: {col!r}")

    for col in sorted(documented - declared):
        errors.append(
            f"FeatureDoc names a column that is not declared in ALL_FEATURES: {col!r}"
        )

    for key, doc in sorted(FEATURE_DOCS.items()):
        if key != doc.name:
            errors.append(
                f"FeatureDoc mapping key {key!r} does not match doc.name {doc.name!r}"
            )
        family_cols = FEATURE_FAMILIES.get(doc.family)
        if family_cols is None:
            errors.append(
                f"{doc.name!r}: family {doc.family!r} is not a key of FEATURE_FAMILIES"
            )
        elif doc.name not in family_cols:
            errors.append(
                f"{doc.name!r}: family {doc.family!r} does not contain this column "
                "(FEATURE_FAMILIES disagreement)"
            )

    return errors


def main() -> int:
    errors = check()
    if errors:
        print("feature-docs drift check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "\nFix: add/adjust a FeatureDoc in "
            "src/protea_contracts/feature_docs.py so it covers exactly "
            "ALL_FEATURES with families that agree with FEATURE_FAMILIES.",
            file=sys.stderr,
        )
        return 1
    from protea_contracts.feature_docs import FEATURE_DOCS

    print(
        f"feature-docs drift check OK: {len(FEATURE_DOCS)} features documented, "
        "zero drift."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
