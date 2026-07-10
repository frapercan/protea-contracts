"""Canonical axis-tuple shortid shared by PROTEA and protea-reranker-lab.

Every benchmark cell in the F-EXP-RESET re-benchmark is identified by an
*axis tuple* of the form
``(plm, k, reranker_spec_id, feature_schema_sha, eval_set_name,
eval_set_manifest_sha, propagation, ensemble_spec)``. To collapse the
historical provenance-JSONB-only access pattern into typed columns,
:class:`protea.infrastructure.orm.models.ExperimentRun` gains a
``axis_tuple_shortid`` column with a UNIQUE constraint.

The shortid formula is

.. code-block:: python

    sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]

which mirrors :meth:`protea_reranker_lab.experiment.ExperimentSpec.hash`
(lines 108-111 of ``experiment.py`` in protea-reranker-lab). The lab
method will delegate to this helper in a follow-up slice; the shared
formula prevents the two implementations drifting in the meantime.

Two callers MUST agree on the byte-for-byte formula or PROTEA's row
membership join with the lab catalog breaks silently. The golden vector
test in ``tests/test_axis_tuple.py`` pins the digest of a known payload
so any change to the formula forces a SemVer-major bump on this package.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from protea_contracts._hashing import short_sha

#: Canonical axis-tuple key set, in human-readable order. The order here
#: does NOT affect the digest (``json.dumps(..., sort_keys=True)``
#: serialises alphabetically). It exists so code that constructs the
#: mapping has a single, reviewed reference for what counts as an axis.
CANONICAL_AXIS_KEYS: tuple[str, ...] = (
    "plm",
    "k",
    "reranker_spec_id",
    "feature_schema_sha",
    "eval_set_name",
    "eval_set_manifest_sha",
    "propagation",
    "ensemble_spec",
)

#: Length of the truncated hex digest returned by
#: :func:`axis_tuple_shortid`. Matches the lab convention
#: (``ExperimentSpec.hash()`` truncates to the same width).
SHORTID_HEX_LEN = 12


def axis_tuple_shortid(axis_tuple: Mapping[str, Any]) -> str:
    """Return the canonical 12-hex shortid for an axis tuple.

    Args:
        axis_tuple: mapping of axis name to value. Every value must be
            JSON-encodable by the standard ``json`` module without a
            custom ``default``. Path / UUID / datetime objects must be
            pre-stringified by the caller (mirrors the lab path's
            ``pydantic.model_dump(mode="json")`` step).

    Returns:
        12 lowercase hex chars (``[0-9a-f]{12}``).

    Raises:
        TypeError: when a value in ``axis_tuple`` is not JSON-encodable.
            Surfaced as a hard error so schema drift is caught at the
            call site rather than producing a silent shortid mismatch.

    The function is intentionally pure: same input -> same output, no
    hidden state, no environment lookup. Order of keys in ``axis_tuple``
    is irrelevant (``json.dumps(..., sort_keys=True)`` canonicalises).
    """
    try:
        blob = json.dumps(dict(axis_tuple), sort_keys=True).encode()
    except TypeError as exc:
        raise TypeError(
            "axis_tuple values must be JSON-encodable without a custom "
            "default; pre-stringify Path / UUID / datetime before "
            f"calling axis_tuple_shortid. underlying error: {exc}"
        ) from exc
    return short_sha(blob, SHORTID_HEX_LEN)


__all__ = [
    "CANONICAL_AXIS_KEYS",
    "SHORTID_HEX_LEN",
    "axis_tuple_shortid",
]
