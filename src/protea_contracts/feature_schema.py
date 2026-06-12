"""Feature schema and compute_schema_sha helpers.

This module is the **canonical** definition of the feature column set
used by both ``protea-core`` (inference) and ``protea-runners.lightgbm``
(training). Bumping any field here forces a major version of
``protea-contracts`` and re-training of every downstream booster
because the trained models hard-bind to the column order.

The hash format follows the lab convention (``"|".join(sorted(...))``)
because that is the formula the existing boosters were trained with.
A compatibility column (``schema_sha_v2``) was added to the
``Dataset`` and ``RerankerModel`` rows during T1.6 so legacy rows
trained against the older PROTEA-side hash (json.dumps with the
unsorted list) can still be loaded.
"""

from __future__ import annotations

from protea_contracts._hashing import short_sha

#: Bumping any of the constants below or this version forces a major
#: ``protea-contracts`` release.
SCHEMA_VERSION = "v3"

#: Numeric features computed per (query, candidate GO term).
#: ``k_context`` is injected at pool-stage time (not in parquet); it
#: encodes the KNN neighbourhood size used to retrieve the candidate.
NUMERIC_FEATURES: list[str] = [
    "distance",
    # NW alignment
    "identity_nw",
    "similarity_nw",
    "alignment_score_nw",
    "gaps_pct_nw",
    "alignment_length_nw",
    # SW alignment
    "identity_sw",
    "similarity_sw",
    "alignment_score_sw",
    "gaps_pct_sw",
    "alignment_length_sw",
    # Lengths
    "length_query",
    "length_ref",
    # Taxonomy
    "taxonomic_distance",
    "taxonomic_common_ancestors",
    # KNN-derived re-ranker features
    "vote_count",
    "k_position",
    "go_term_frequency",
    "ref_annotation_density",
    "neighbor_distance_std",
    # Consensus features (per candidate term, computed over voting neighbors)
    "neighbor_vote_fraction",
    "neighbor_min_distance",
    "neighbor_mean_distance",
    # Anc2Vec semantic-coherence features (GO release 2020-10-06 pretrained)
    "anc2vec_neighbor_cos",
    "anc2vec_neighbor_maxcos",
    "anc2vec_has_emb",
    # Query-side Anc2Vec: candidate vs query's pre-cutoff annotations.
    "anc2vec_query_known_cos",
    "anc2vec_query_known_maxcos",
    "anc2vec_query_known_count",
    # Taxonomic consensus across voting neighbors.
    "tax_voters_same_frac",
    "tax_voters_close_frac",
    "tax_voters_mean_common_ancestors",
    # Multi-source pooling context: KNN neighbourhood size used to
    # retrieve the candidate. Injected at stage time per manifest source;
    # absent from the raw parquet dumps.
    "k_context",
    # Sequence-embedding PCA: 16-dim query projection. NaN when disabled,
    # LightGBM treats them as missing.
    "emb_pca_query_0",
    "emb_pca_query_1",
    "emb_pca_query_2",
    "emb_pca_query_3",
    "emb_pca_query_4",
    "emb_pca_query_5",
    "emb_pca_query_6",
    "emb_pca_query_7",
    "emb_pca_query_8",
    "emb_pca_query_9",
    "emb_pca_query_10",
    "emb_pca_query_11",
    "emb_pca_query_12",
    "emb_pca_query_13",
    "emb_pca_query_14",
    "emb_pca_query_15",
    # InterPro signature->GO mapping features. Computed per
    # (query protein, candidate GO term) from the InterPro member-DB
    # signatures that map onto the candidate term. Bool/int/float are
    # treated as numeric by LightGBM (same convention as anc2vec_has_emb).
    "interpro_hit",
    "interpro_score",
    "interpro_n_signatures",
    # Member-DB one-hots: which signature databases supplied a mapping.
    "interpro_db_pfam",
    "interpro_db_panther",
    "interpro_db_superfamily",
    "interpro_db_smart",
    "interpro_db_cdd",
    "interpro_db_prosite",
    # Presence flags: whether each evidence source contributed a
    # candidate at all for this (protein, go_id). Used to tell a true
    # zero apart from an absent source when pooling KNN + InterPro.
    "knn_present",
    "interpro_present",
]

#: Embedding-PCA projection dimensionality. Must equal the number of
#: ``emb_pca_query_*`` entries in :data:`NUMERIC_FEATURES`.
EMBEDDING_PCA_DIM = 16

#: Categorical features. The lab encodes these once and the codes ride
#: alongside in the parquet so the booster sees stable integer codes.
#: ``plm_id`` is injected at pool-stage time (not in parquet); it
#: encodes which protein language model produced the embeddings used for
#: KNN retrieval. See FEATURE_LEAKAGE_AUDIT.md for the GO/NO-GO ruling
#: on this column.
CATEGORICAL_FEATURES: list[str] = [
    "qualifier",
    "evidence_code",
    "taxonomic_relation",
    "aspect",
    "plm_id",
]

#: Concatenation of numeric + categorical, in the order LightGBM expects
#: at training and inference time.
ALL_FEATURES: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

#: Logical groupings used to switch families on/off at training time.
#: Each family lists the column names it contributes to ``ALL_FEATURES``.
FEATURE_FAMILIES: dict[str, list[str]] = {
    "knn": [
        "distance",
        "k_position",
        "vote_count",
        "neighbor_vote_fraction",
        "neighbor_min_distance",
        "neighbor_mean_distance",
        "neighbor_distance_std",
    ],
    "knn_distance": [
        "distance",
        "neighbor_min_distance",
        "neighbor_mean_distance",
        "neighbor_distance_std",
    ],
    "knn_vote": ["k_position", "vote_count", "neighbor_vote_fraction"],
    "alignment_nw": [
        "identity_nw",
        "similarity_nw",
        "alignment_score_nw",
        "gaps_pct_nw",
        "alignment_length_nw",
    ],
    "alignment_sw": [
        "identity_sw",
        "similarity_sw",
        "alignment_score_sw",
        "gaps_pct_sw",
        "alignment_length_sw",
    ],
    "length": ["length_query", "length_ref"],
    "taxonomy_pair": [
        "taxonomic_distance",
        "taxonomic_common_ancestors",
        "taxonomic_relation",
    ],
    "taxonomy_voters": [
        "tax_voters_same_frac",
        "tax_voters_close_frac",
        "tax_voters_mean_common_ancestors",
    ],
    "go_context": ["go_term_frequency", "ref_annotation_density"],
    "anc2vec_neighbor": [
        "anc2vec_neighbor_cos",
        "anc2vec_neighbor_maxcos",
        "anc2vec_has_emb",
    ],
    "anc2vec_query": [
        "anc2vec_query_known_cos",
        "anc2vec_query_known_maxcos",
        "anc2vec_query_known_count",
    ],
    "emb_pca": [f"emb_pca_query_{i}" for i in range(EMBEDDING_PCA_DIM)],
    "annotation_meta": ["qualifier", "evidence_code", "aspect"],
    # Multi-source pooling context features (v3+).
    # plm_id: which PLM produced the embeddings used for KNN retrieval.
    # Injected at pool-stage time; absent from raw parquet dumps.
    # See FEATURE_LEAKAGE_AUDIT.md for GO/NO-GO ruling.
    "plm_context": ["plm_id"],
    # k_context: KNN neighbourhood size (K) for this manifest source.
    # Injected at pool-stage time; absent from raw parquet dumps.
    "k_neighborhood": ["k_context"],
    # InterPro signature->GO mapping family (vNext reranker). Computed
    # from the InterPro member-DB signatures that map onto the candidate
    # term, plus the per-source presence flags used when pooling KNN and
    # InterPro candidates.
    "interpro": [
        "interpro_hit",
        "interpro_score",
        "interpro_n_signatures",
        "interpro_db_pfam",
        "interpro_db_panther",
        "interpro_db_superfamily",
        "interpro_db_smart",
        "interpro_db_cdd",
        "interpro_db_prosite",
        "knn_present",
        "interpro_present",
    ],
}

#: Reserved column names: present in every parquet dump alongside the
#: feature columns. The label column is included so the producer and
#: consumer agree on naming without a separate constant.
RESERVED_COLUMNS: tuple[str, ...] = (
    "protein_accession",
    "go_term_id",
    "label",
    "category",
    "aspect",
    "snapshot_pair",
)

#: Single source of truth for the label column name (mirrors lab usage).
LABEL_COLUMN = "label"


def compute_schema_sha(columns: list[str]) -> str:
    """Stable 12-hex digest of a column set.

    Format follows the lab convention: ``"|".join(sorted(columns))``
    UTF-8 encoded, SHA-256, truncated to 12 hex chars. The legacy
    PROTEA formula (``json.dumps(columns, sort_keys=True)``) is
    intentionally NOT used; a compatibility column ``schema_sha_v2``
    was added during T1.6 of master plan v3 so old rows can still be
    loaded.

    Two callers must agree on this exact bytes-for-bytes formula
    or the booster cache invalidation breaks silently. The golden
    test in ``tests/test_feature_schema.py`` pins the digest of
    ``ALL_FEATURES`` so any rename / reorder / addition forces a
    SemVer major bump on this package.
    """
    blob = "|".join(sorted(columns)).encode()
    return short_sha(blob)


def compute_feature_schema_sha(
    families: list[str],
    drop: list[str] | None = None,
) -> str:
    """Family-aware schema fingerprint.

    Binds the selected family names AND their column lists together,
    so a rename or semantic change of a family's columns changes the
    sha even if the final selected column set happens to collide.

    Args:
        families: family names (must be keys of :data:`FEATURE_FAMILIES`).
        drop: explicit feature names to exclude from the fingerprint
            (matches the booster training ``drop_features``).

    Raises:
        KeyError: if any family is unknown.
    """
    parts: list[str] = []
    for fam in sorted(families):
        cols = FEATURE_FAMILIES[fam]
        parts.append(f"{fam}={','.join(sorted(cols))}")
    if drop:
        parts.append("drop=" + ",".join(sorted(drop)))
    blob = "|".join(parts).encode()
    return short_sha(blob)


def required_columns(
    families: list[str] | None = None,
    drop: list[str] | None = None,
) -> list[str]:
    """Return the column names a parquet must carry to be loadable.

    Always starts with :data:`RESERVED_COLUMNS`, then appends the
    feature columns selected by ``families`` and ``drop``.

    Args:
        families: ``None`` keeps all of :data:`ALL_FEATURES`; otherwise
            only the union of the listed families.
        drop: explicit feature names to exclude.
    """
    drop_set = set(drop or [])
    if families is None:
        feats = list(ALL_FEATURES)
    else:
        feats = []
        for fam in families:
            feats.extend(FEATURE_FAMILIES[fam])
    seen: set[str] = set()
    out: list[str] = []
    for col in (*RESERVED_COLUMNS, *feats):
        if col in drop_set or col in seen:
            continue
        seen.add(col)
        out.append(col)
    return out
