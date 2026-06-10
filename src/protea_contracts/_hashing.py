"""Internal SHA-256 short-digest helper.

Private module (leading underscore): NOT part of the public contract
surface and intentionally absent from :data:`protea_contracts.__all__`.

Several public helpers reduce a byte blob to a truncated hex digest
with the exact same formula
(``hashlib.sha256(blob).hexdigest()[:length]``):

* :func:`protea_contracts.axis_tuple.axis_tuple_shortid`
* :func:`protea_contracts.feature_schema.compute_schema_sha`
* :func:`protea_contracts.feature_schema.compute_feature_schema_sha`
* :meth:`protea_contracts.manifest.DatasetSpec.hash`

These digests are golden-vector pinned in the test suite, so the
formula must never drift. Centralising it here guarantees the four
call sites stay byte-for-byte identical: a change to the digest
recipe touches one line, not four.
"""

from __future__ import annotations

import hashlib

#: Default truncated-digest width (hex chars) used across the package.
DEFAULT_DIGEST_LEN = 12


def short_sha(blob: bytes, length: int = DEFAULT_DIGEST_LEN) -> str:
    """Return the first ``length`` hex chars of ``sha256(blob)``.

    Args:
        blob: pre-serialised bytes to hash.
        length: number of leading hex characters to keep (default 12).

    Returns:
        ``length`` lowercase hex chars (``[0-9a-f]``).
    """
    return hashlib.sha256(blob).hexdigest()[:length]
