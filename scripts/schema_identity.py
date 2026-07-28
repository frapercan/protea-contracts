"""Print the schema identity of a checkout: version, column count, digest.

Used by the fork guard to compare two branches without installing either.
Kept dependency-free on purpose so the guard needs no install step, and
separate from the workflow so it can be exercised locally.

Usage::

    PYTHONPATH=src python scripts/schema_identity.py
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from protea_contracts.feature_schema import (
            ALL_FEATURES,
            SCHEMA_VERSION,
            compute_schema_sha,
        )
    except ImportError as exc:  # pragma: no cover - guard-side diagnostics
        print(f"could not import the feature schema: {exc}", file=sys.stderr)
        return 2
    print(SCHEMA_VERSION, len(ALL_FEATURES), compute_schema_sha(ALL_FEATURES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
