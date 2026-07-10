"""Human-facing documentation for every canonical reranker feature.

This module is the **single source of truth** for what each column in
:data:`protea_contracts.feature_schema.ALL_FEATURES` *measures*, how it is
*computed* in words, *who produces it*, and whether a producer actually runs
in the default export today. :data:`feature_schema.py` owns the column *names*
and the fingerprint; this module owns their *meaning*.

The audience is the technician who deploys and operates the PROTEA stack,
possibly a stranger who cloned it and runs it alone. A reader must be able to
ask "what is ``neighbor_vote_fraction``, who computes it, and can I trust it
today" and get the answer from one place. Three renderers (this repo's Sphinx
reference table, PROTEA's docs, and the UI) are meant to read :data:`FEATURE_DOCS`
rather than restate feature meanings by hand; keeping the prose here means a
fix lands once and propagates.

Governance
==========

``scripts/check_feature_docs.py`` and ``tests/test_feature_docs.py`` fail if a
declared feature lacks a :class:`FeatureDoc`, if a doc names a column that is
not declared, or if a doc's ``family`` disagrees with
:data:`feature_schema.FEATURE_FAMILIES`. That drift lint is what keeps this
file honest as the schema evolves.

Provenance note (ADR-D45)
=========================

The six LAFA columns (``classifier_score``, ``classifier_present``,
``self_prior_score``, ``association_total``, ``association_cross``,
``association_present``) are :attr:`FeatureStatus.DECLARED_ABSENT`: they are
first-class members of the canonical schema, their producers exist, but no
producer runs in the default research-dataset export, so the export emits
``NaN`` for them (``protea.core._leaf_record_builder._LeafRecordBuilder._lafa_default_fields``).
See PROTEA ``docs/source/adr/D45-jsonb-blob-feature-governance.rst``. The
fingerprint pins column *names*, not values or producers, so a booster that
selects these families passes the schema-sha guard even though the columns
carry no measurement.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "FEATURE_DOCS",
    "FeatureDoc",
    "FeatureStatus",
]


class FeatureStatus(str, Enum):
    """Whether a declared column is actually filled with a real value today.

    Attributes:
        PRODUCED: a wired producer fills the column with a real value in the
            export (possibly behind a performance flag that the canonical
            export enables; see the feature's ``notes``).
        DECLARED_ABSENT: the column is declared in the canonical schema and a
            producer exists, but no producer runs in the default export, so
            the export emits ``NaN`` (LightGBM reads it as missing).
        POOL_INJECTED: the PROTEA dump does not write this column; the lab's
            pooled multi-manifest loader fills it with a per-source constant at
            stage time. Absent from the raw parquet dumps.
        BROKEN: the column is produced but a defect that can be pointed at in
            code or data makes it carry no signal. Used only where that defect
            is verifiable from the source tree, never for a measured-low-gain
            observation (which belongs to a run's results, not here).
    """

    PRODUCED = "PRODUCED"
    DECLARED_ABSENT = "DECLARED_ABSENT"
    POOL_INJECTED = "POOL_INJECTED"
    BROKEN = "BROKEN"


@dataclass(frozen=True)
class FeatureDoc:
    """Operator-facing documentation for one canonical feature column.

    Attributes:
        name: the column name; must match a member of
            :data:`feature_schema.ALL_FEATURES` exactly.
        family: the canonical family this doc files the column under; must be a
            key of :data:`feature_schema.FEATURE_FAMILIES` whose column list
            contains ``name``. A column that belongs to several families (for
            example a ``knn`` column that also appears in ``knn_distance``) is
            filed under its umbrella family here.
        summary: one sentence, what it measures, in operator vocabulary.
        definition: how it is computed, precisely enough to reimplement, in
            prose verified against the producer code.
        producer: the dotted path of the function that fills the column, or an
            explicit marker when no producer runs in the default export.
        status: see :class:`FeatureStatus`.
        unit: physical / logical unit, or ``None`` when dimensionless or a bare
            code.
        value_range: the range the value takes, or an explicit "unbounded" /
            "bare count" note, or ``None`` when not meaningful.
        notes: caveats. Never a gain number; measured importance belongs to a
            run's results, not to the registry.
    """

    name: str
    family: str
    summary: str
    definition: str
    producer: str
    status: FeatureStatus
    unit: str | None = None
    value_range: str | None = None
    notes: str | None = None


# Dotted-path shorthands used repeatedly below.
_LEAF = "protea.core._leaf_record_builder._LeafRecordBuilder"
_FENG = "protea.core.feature_engineering"

_DOCS: list[FeatureDoc] = [
    # ── KNN retrieval + reranker aggregates (family "knn") ──────────────────
    FeatureDoc(
        name="distance",
        family="knn",
        summary="Embedding distance from the query to the reference neighbour that voted this candidate term.",
        definition=(
            "The PLM-embedding distance returned by the KNN retrieval step for "
            "the (query, reference) pair whose annotation contributed this "
            "candidate GO term. Smaller is a closer neighbour. Assembled onto "
            "the leaf record from the KNN runner; the metric is the one the "
            "retrieval index was built with for the active PLM."
        ),
        producer=f"{_LEAF}.make_leaf_record (distance from protea.core._knn_transfer_runner._KnnTransferRunner)",
        status=FeatureStatus.PRODUCED,
        unit="embedding-distance",
        value_range="non-negative; scale depends on the retrieval metric and PLM",
    ),
    FeatureDoc(
        name="vote_count",
        family="knn",
        summary="How many of the query's KNN neighbours annotated this candidate GO term.",
        definition=(
            "Count of retrieved neighbours (within the K-neighbourhood) that "
            "carry this candidate term among their annotations. Defaults to 1 "
            "when no per-term tally is present."
        ),
        producer=f"{_LEAF}._reranker_fields (runner.rr_vote_count)",
        status=FeatureStatus.PRODUCED,
        unit="votes",
        value_range="bare count, 1..K",
    ),
    FeatureDoc(
        name="k_position",
        family="knn",
        summary="Rank of the closest neighbour that voted this candidate term.",
        definition=(
            "The 1-based position, in the distance-sorted neighbour list, of "
            "the nearest neighbour that annotated this candidate term. Lower "
            "means the term was proposed by a closer neighbour. Defaults to 1."
        ),
        producer=f"{_LEAF}._reranker_fields (runner.rr_k_position)",
        status=FeatureStatus.PRODUCED,
        unit="rank",
        value_range="bare count, 1..K",
    ),
    FeatureDoc(
        name="go_term_frequency",
        family="go_context",
        summary="How common the candidate GO term is across the reference pool.",
        definition=(
            "Corpus frequency of the candidate term over the reference "
            "annotation pool, used as a base-rate prior so a ubiquitous term is "
            "not treated like a specific one. Read from the runner's precomputed "
            "term-frequency map; defaults to 0 for an unseen term."
        ),
        producer=f"{_LEAF}._reranker_fields (runner.go_term_freq)",
        status=FeatureStatus.PRODUCED,
        unit="count",
        value_range="bare count, non-negative",
    ),
    FeatureDoc(
        name="ref_annotation_density",
        family="go_context",
        summary="How many annotations the voting reference protein carries.",
        definition=(
            "Annotation count of the reference protein that supplied this "
            "candidate, a proxy for how densely studied that reference is. Read "
            "from the runner's per-reference density map; defaults to 0."
        ),
        producer=f"{_LEAF}._reranker_fields (runner.ref_ann_density)",
        status=FeatureStatus.PRODUCED,
        unit="count",
        value_range="bare count, non-negative",
    ),
    FeatureDoc(
        name="neighbor_distance_std",
        family="knn",
        summary="Spread of the query's neighbour distances.",
        definition=(
            "Standard deviation of the distances of the query's retrieved "
            "neighbours. A per-query quantity (same for every candidate of that "
            "query) describing how tight or diffuse the neighbourhood is. "
            "Defaults to 0.0."
        ),
        producer=f"{_LEAF}._reranker_fields (runner.rr_distance_std)",
        status=FeatureStatus.PRODUCED,
        unit="embedding-distance",
        value_range="non-negative",
    ),
    FeatureDoc(
        name="neighbor_vote_fraction",
        family="knn",
        summary="Fraction of the K-neighbourhood that voted this candidate term.",
        definition=(
            "``vote_count`` divided by the retrieval neighbourhood size "
            "``runner.k_limit``. A normalised consensus strength: 1.0 means "
            "every neighbour in the K-neighbourhood annotated this term."
        ),
        producer=f"{_LEAF}._reranker_fields (vote_count / runner.k_limit)",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0",
    ),
    FeatureDoc(
        name="neighbor_min_distance",
        family="knn",
        summary="Distance of the closest neighbour that voted this candidate term.",
        definition=(
            "Minimum over the voting neighbours of their query distance, for "
            "this candidate term. Falls back to the row's own ``distance`` when "
            "no per-term minimum is recorded."
        ),
        producer=f"{_LEAF}._reranker_fields (runner.rr_vote_min_d)",
        status=FeatureStatus.PRODUCED,
        unit="embedding-distance",
        value_range="non-negative",
    ),
    FeatureDoc(
        name="neighbor_mean_distance",
        family="knn",
        summary="Mean distance of the neighbours that voted this candidate term.",
        definition=(
            "Sum of the voting neighbours' distances divided by ``vote_count`` "
            "(clamped to at least 1) for this candidate term. Falls back to the "
            "row's own ``distance`` when no per-term sum is recorded."
        ),
        producer=f"{_LEAF}._reranker_fields (runner.rr_vote_sum_d / vote_count)",
        status=FeatureStatus.PRODUCED,
        unit="embedding-distance",
        value_range="non-negative",
    ),
    # ── Needleman-Wunsch global alignment (family "alignment_nw") ───────────
    FeatureDoc(
        name="identity_nw",
        family="alignment_nw",
        summary="Sequence identity of the global (Needleman-Wunsch) alignment of query and reference.",
        definition=(
            "Fraction of identical positions (matches / alignment length) in the "
            "parasail Needleman-Wunsch global alignment of the query and "
            "reference sequences."
        ),
        producer=f"{_FENG}.compute_alignment (parasail NW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0",
        notes=(
            "Populated when the ``compute_alignments`` export flag is enabled; "
            "with the flag off the column is emitted null (LightGBM reads it as "
            "missing)."
        ),
    ),
    FeatureDoc(
        name="similarity_nw",
        family="alignment_nw",
        summary="Sequence similarity of the global (Needleman-Wunsch) alignment.",
        definition=(
            "Fraction of similar positions (parasail comparison line characters "
            "``|`` or ``:``) over the alignment length of the NW global "
            "alignment. Similarity counts conservative substitutions, so it is "
            ">= identity."
        ),
        producer=f"{_FENG}.compute_alignment (parasail NW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="alignment_score_nw",
        family="alignment_nw",
        summary="Raw score of the global (Needleman-Wunsch) alignment.",
        definition=(
            "The parasail substitution-matrix score of the NW global alignment "
            "of query and reference. An unnormalised score that grows with "
            "alignment length and similarity."
        ),
        producer=f"{_FENG}.compute_alignment (parasail NW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="alignment score",
        value_range="unbounded (matrix-dependent)",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="gaps_pct_nw",
        family="alignment_nw",
        summary="Gap percentage of the global (Needleman-Wunsch) alignment.",
        definition=(
            "Fraction of the NW alignment columns that are gaps in either "
            "sequence."
        ),
        producer=f"{_FENG}.compute_alignment (parasail NW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="alignment_length_nw",
        family="alignment_nw",
        summary="Length of the global (Needleman-Wunsch) alignment.",
        definition=(
            "Number of columns in the NW global alignment (matched positions "
            "plus gaps)."
        ),
        producer=f"{_FENG}.compute_alignment (parasail NW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="residues",
        value_range="bare count, non-negative",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    # ── Smith-Waterman local alignment (family "alignment_sw") ──────────────
    FeatureDoc(
        name="identity_sw",
        family="alignment_sw",
        summary="Sequence identity of the local (Smith-Waterman) alignment of query and reference.",
        definition=(
            "Fraction of identical positions (matches / alignment length) in the "
            "parasail Smith-Waterman local alignment of the query and reference "
            "sequences."
        ),
        producer=f"{_FENG}.compute_alignment (parasail SW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="similarity_sw",
        family="alignment_sw",
        summary="Sequence similarity of the local (Smith-Waterman) alignment.",
        definition=(
            "Fraction of similar positions (comparison-line ``|`` or ``:``) over "
            "the alignment length of the SW local alignment."
        ),
        producer=f"{_FENG}.compute_alignment (parasail SW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="alignment_score_sw",
        family="alignment_sw",
        summary="Raw score of the local (Smith-Waterman) alignment.",
        definition=(
            "The parasail substitution-matrix score of the SW local alignment of "
            "query and reference. Unnormalised."
        ),
        producer=f"{_FENG}.compute_alignment (parasail SW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="alignment score",
        value_range="unbounded (matrix-dependent)",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="gaps_pct_sw",
        family="alignment_sw",
        summary="Gap percentage of the local (Smith-Waterman) alignment.",
        definition="Fraction of the SW alignment columns that are gaps in either sequence.",
        producer=f"{_FENG}.compute_alignment (parasail SW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="alignment_length_sw",
        family="alignment_sw",
        summary="Length of the local (Smith-Waterman) alignment.",
        definition="Number of columns in the SW local alignment (matched positions plus gaps).",
        producer=f"{_FENG}.compute_alignment (parasail SW), assembled by {_LEAF}._alignment_fields",
        status=FeatureStatus.PRODUCED,
        unit="residues",
        value_range="bare count, non-negative",
        notes="Populated when the ``compute_alignments`` export flag is enabled; null otherwise.",
    ),
    # ── Sequence lengths (family "length") ──────────────────────────────────
    FeatureDoc(
        name="length_query",
        family="length",
        summary="Amino-acid length of the query protein.",
        definition="Residue count of the query sequence, carried on the pair-feature record.",
        producer=f"{_LEAF}._alignment_fields (from pair features)",
        status=FeatureStatus.PRODUCED,
        unit="residues",
        value_range="bare count, positive",
    ),
    FeatureDoc(
        name="length_ref",
        family="length",
        summary="Amino-acid length of the reference (neighbour) protein.",
        definition="Residue count of the reference sequence, carried on the pair-feature record.",
        producer=f"{_LEAF}._alignment_fields (from pair features)",
        status=FeatureStatus.PRODUCED,
        unit="residues",
        value_range="bare count, positive",
    ),
    # ── Taxonomy of the query/reference pair (family "taxonomy_pair") ───────
    FeatureDoc(
        name="taxonomic_distance",
        family="taxonomy_pair",
        summary="Tree distance between the query's and reference's NCBI taxa.",
        definition=(
            "Distance between the query and reference organisms in the NCBI "
            "taxonomy tree, computed from their lineages (0 when identical). "
            "Null when either taxon id is missing."
        ),
        producer=f"{_FENG}.compute_taxonomy, assembled by {_LEAF}._taxonomy_fields",
        status=FeatureStatus.PRODUCED,
        unit="tree edges",
        value_range="bare count, non-negative; null when a taxon id is absent",
        notes="Populated when the ``compute_taxonomy`` export flag is enabled; null otherwise.",
    ),
    FeatureDoc(
        name="taxonomic_common_ancestors",
        family="taxonomy_pair",
        summary="Number of shared lineage nodes between the query and reference taxa.",
        definition=(
            "Count of taxonomy nodes shared by the query and reference lineages "
            "(their common-ancestor path length). 1 when the taxa are the same, "
            "0 when unrelated / unknown."
        ),
        producer=f"{_FENG}.compute_taxonomy, assembled by {_LEAF}._taxonomy_fields",
        status=FeatureStatus.PRODUCED,
        unit="count",
        value_range="bare count, non-negative",
        notes="Populated when the ``compute_taxonomy`` export flag is enabled.",
    ),
    FeatureDoc(
        name="taxonomic_relation",
        family="taxonomy_pair",
        summary="Categorical relationship of the query and reference taxa.",
        definition=(
            "One of ``same``, ``ancestor``, ``descendant``, ``child``, "
            "``parent``, ``root-only`` or ``unrelated``, derived from the two "
            "lineages. Categorical: the lab encodes it to a stable integer code "
            "for LightGBM."
        ),
        producer=f"{_FENG}.compute_taxonomy, assembled by {_LEAF}._taxonomy_fields",
        status=FeatureStatus.PRODUCED,
        unit=None,
        value_range="one of {same, ancestor, descendant, child, parent, root-only, unrelated}",
        notes="Categorical feature. Populated when the ``compute_taxonomy`` export flag is enabled.",
    ),
    # ── Taxonomic consensus over voting neighbours (family "taxonomy_voters")
    FeatureDoc(
        name="tax_voters_same_frac",
        family="taxonomy_voters",
        summary="Fraction of voting neighbours from the same organism as the query.",
        definition=(
            "Over the neighbours that voted this candidate term, the fraction "
            "whose taxon equals the query's. NaN when taxonomy is disabled for "
            "the run."
        ),
        producer=f"{_LEAF}._tax_consensus_fields ({_LEAF}._tax_same_frac)",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0; NaN when taxonomy disabled",
    ),
    FeatureDoc(
        name="tax_voters_close_frac",
        family="taxonomy_voters",
        summary="Fraction of voting neighbours taxonomically close to the query.",
        definition=(
            "Over the neighbours that voted this candidate term, the fraction "
            "whose taxon is taxonomically close to the query's (near in the "
            "lineage tree). NaN when taxonomy is disabled."
        ),
        producer=f"{_LEAF}._tax_consensus_fields ({_LEAF}._tax_close_frac)",
        status=FeatureStatus.PRODUCED,
        unit="fraction",
        value_range="0.0..1.0; NaN when taxonomy disabled",
    ),
    FeatureDoc(
        name="tax_voters_mean_common_ancestors",
        family="taxonomy_voters",
        summary="Mean shared-lineage depth between the query and its voting neighbours.",
        definition=(
            "Average, over the neighbours that voted this candidate term, of the "
            "count of taxonomy nodes shared with the query. NaN when taxonomy is "
            "disabled."
        ),
        producer=f"{_LEAF}._tax_consensus_fields ({_LEAF}._tax_ca_mean)",
        status=FeatureStatus.PRODUCED,
        unit="count",
        value_range="non-negative; NaN when taxonomy disabled",
    ),
    # ── Anc2Vec neighbour-side semantic coherence (family "anc2vec_neighbor")
    FeatureDoc(
        name="anc2vec_neighbor_cos",
        family="anc2vec_neighbor",
        summary="Cosine of the candidate term to the neighbours' semantic centroid.",
        definition=(
            "Cosine similarity between the candidate GO term's Anc2Vec embedding "
            "(GO release 2020-10-06 pretrained) and the unit centroid of the "
            "voting neighbours' embeddings. NaN when the candidate has no "
            "Anc2Vec embedding or there is no centroid."
        ),
        producer=f"{_LEAF}._anc2vec_features / {_LEAF}._anc2vec_fields",
        status=FeatureStatus.PRODUCED,
        unit="cosine",
        value_range="-1.0..1.0; NaN when no embedding",
    ),
    FeatureDoc(
        name="anc2vec_neighbor_maxcos",
        family="anc2vec_neighbor",
        summary="Max cosine of the candidate term to any single voting neighbour.",
        definition=(
            "Maximum cosine similarity between the candidate term's Anc2Vec "
            "embedding and any individual neighbour embedding in the voting set. "
            "NaN when the candidate has no embedding or the neighbour matrix is "
            "absent."
        ),
        producer=f"{_LEAF}._anc2vec_features / {_LEAF}._anc2vec_fields",
        status=FeatureStatus.PRODUCED,
        unit="cosine",
        value_range="-1.0..1.0; NaN when no embedding",
    ),
    FeatureDoc(
        name="anc2vec_has_emb",
        family="anc2vec_neighbor",
        summary="Whether the candidate GO term has an Anc2Vec embedding.",
        definition=(
            "1.0 when the candidate term is present in the Anc2Vec index (so the "
            "cosine features are meaningful), 0.0 otherwise. Lets the booster "
            "tell a real 0 cosine from an absent embedding."
        ),
        producer=f"{_LEAF}._anc2vec_features / {_LEAF}._anc2vec_fields",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="0.0 or 1.0",
    ),
    # ── Anc2Vec query-side (candidate vs query's known terms) ───────────────
    FeatureDoc(
        name="anc2vec_query_known_cos",
        family="anc2vec_query",
        summary="Cosine of the candidate term to the centroid of the query's known terms.",
        definition=(
            "Cosine similarity between the candidate term's Anc2Vec embedding "
            "and the unit centroid of the query protein's pre-cutoff known "
            "annotations. NaN when the candidate has no embedding or the query "
            "has no known-term centroid."
        ),
        producer=f"{_LEAF}._anc2vec_features / {_LEAF}._anc2vec_fields",
        status=FeatureStatus.PRODUCED,
        unit="cosine",
        value_range="-1.0..1.0; NaN when no embedding",
    ),
    FeatureDoc(
        name="anc2vec_query_known_maxcos",
        family="anc2vec_query",
        summary="Max cosine of the candidate term to any of the query's known terms.",
        definition=(
            "Maximum cosine similarity between the candidate term's Anc2Vec "
            "embedding and any single pre-cutoff known-term embedding of the "
            "query. NaN when the candidate has no embedding or the query has no "
            "known-term matrix."
        ),
        producer=f"{_LEAF}._anc2vec_features / {_LEAF}._anc2vec_fields",
        status=FeatureStatus.PRODUCED,
        unit="cosine",
        value_range="-1.0..1.0; NaN when no embedding",
    ),
    FeatureDoc(
        name="anc2vec_query_known_count",
        family="anc2vec_query",
        summary="How many pre-cutoff known terms the query protein has.",
        definition=(
            "Count of the query protein's own pre-cutoff (non-experimental-"
            "leakage-free) known annotations, cast to float. Zero for a protein "
            "with no prior annotations."
        ),
        producer=f"{_LEAF}._anc2vec_fields (q_known_n)",
        status=FeatureStatus.PRODUCED,
        unit="count",
        value_range="bare count, non-negative",
    ),
    # ── Embedding-PCA query projection (family "emb_pca") ───────────────────
    *[
        FeatureDoc(
            name=f"emb_pca_query_{i}",
            family="emb_pca",
            summary=f"Component {i} of the 16-dim PCA projection of the query PLM embedding.",
            definition=(
                f"Coordinate {i} of a 16-dimensional PCA projection of the "
                "query protein's PLM embedding. The PCA is fit over the "
                "embedding pool at export time and applied to the query vector."
            ),
            producer=(
                "protea.core.operations.export_minijobs._export_features_batch "
                "(PCA fit + transform), assembled onto the leaf record in "
                f"{_LEAF}.make_leaf_record"
            ),
            status=FeatureStatus.PRODUCED,
            unit="PCA component",
            value_range="unbounded real; NaN when disabled",
            notes=(
                "Populated when the ``use_embedding_pca`` export flag is enabled; "
                "NaN otherwise (LightGBM reads it as missing). A training run "
                "measured this family to contribute essentially nothing; that is "
                "a property of that run, not of the feature, so no gain number is "
                "recorded here."
            ),
        )
        for i in range(16)
    ],
    # ── InterPro signature->GO mapping (family "interpro") ──────────────────
    FeatureDoc(
        name="interpro_hit",
        family="interpro",
        summary="Whether an InterPro signature maps the query onto this candidate GO term.",
        definition=(
            "True when at least one InterPro member-database signature of the "
            "query maps onto this candidate term in the InterPro GO-prediction "
            "table. Default False for a (query, term) with no InterPro evidence."
        ),
        producer="protea.core._interpro_features.apply_interpro_features (default protea.core._leaf_record_builder._LeafRecordBuilder._interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes=(
            "The InterPro GO-prediction table is loaded by "
            "``protea.core._interpro_features.load_interpro_go_pred``, which "
            "returns an empty table when its source env var is unset, in which "
            "case every row keeps the zero/False default and the column carries "
            "no signal. Whether the InterPro tables are populated in a given "
            "deployment is a database-state question that cannot be settled from "
            "the source tree alone, so no ``BROKEN`` status is asserted here. "
            "Note that InterPro's principal contribution to predictions enters "
            "through a separate InterPro2GO noisy-OR graft "
            "(``protea.core.operations.predict_go_terms._interpro_graft``), not "
            "through these reranker columns."
        ),
    ),
    FeatureDoc(
        name="interpro_score",
        family="interpro",
        summary="Strength of the InterPro signature->GO mapping for this candidate term.",
        definition=(
            "Graded InterPro2GO mapping score for the query onto this candidate "
            "term. 0.0 when there is no InterPro evidence."
        ),
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="score",
        value_range="non-negative; 0.0 when no InterPro evidence",
        notes="Env-gated table; carries no signal when the InterPro GO-prediction table is unpopulated (see interpro_hit).",
    ),
    FeatureDoc(
        name="interpro_n_signatures",
        family="interpro",
        summary="Number of InterPro signatures supporting this candidate term.",
        definition=(
            "Count of distinct InterPro member-database signatures of the query "
            "that map onto this candidate term. 0 when there is no InterPro "
            "evidence."
        ),
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="count",
        value_range="bare count, non-negative",
        notes="Env-gated table; 0 for every row when the InterPro table is unpopulated (see interpro_hit).",
    ),
    FeatureDoc(
        name="interpro_db_pfam",
        family="interpro",
        summary="Whether a Pfam signature supplied the InterPro mapping.",
        definition="One-hot: True when a Pfam member-database signature contributed the mapping for this candidate term.",
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes="Env-gated table (see interpro_hit).",
    ),
    FeatureDoc(
        name="interpro_db_panther",
        family="interpro",
        summary="Whether a PANTHER signature supplied the InterPro mapping.",
        definition="One-hot: True when a PANTHER member-database signature contributed the mapping for this candidate term.",
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes="Env-gated table (see interpro_hit).",
    ),
    FeatureDoc(
        name="interpro_db_superfamily",
        family="interpro",
        summary="Whether a SUPERFAMILY signature supplied the InterPro mapping.",
        definition="One-hot: True when a SUPERFAMILY member-database signature contributed the mapping for this candidate term.",
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes="Env-gated table (see interpro_hit).",
    ),
    FeatureDoc(
        name="interpro_db_smart",
        family="interpro",
        summary="Whether a SMART signature supplied the InterPro mapping.",
        definition="One-hot: True when a SMART member-database signature contributed the mapping for this candidate term.",
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes="Env-gated table (see interpro_hit).",
    ),
    FeatureDoc(
        name="interpro_db_cdd",
        family="interpro",
        summary="Whether a CDD signature supplied the InterPro mapping.",
        definition="One-hot: True when a CDD member-database signature contributed the mapping for this candidate term.",
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes="Env-gated table (see interpro_hit).",
    ),
    FeatureDoc(
        name="interpro_db_prosite",
        family="interpro",
        summary="Whether a PROSITE signature supplied the InterPro mapping.",
        definition="One-hot: True when a PROSITE member-database signature contributed the mapping for this candidate term.",
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes="Env-gated table (see interpro_hit).",
    ),
    FeatureDoc(
        name="knn_present",
        family="interpro",
        summary="Whether the KNN source proposed this candidate for the (protein, term).",
        definition=(
            "Presence flag: True when the KNN retrieval source contributed this "
            "candidate. Used when pooling KNN and InterPro candidates so a true "
            "zero is distinguishable from an absent source. True on every KNN "
            "leaf record."
        ),
        producer=f"{_LEAF}._interpro_default_fields (and the InterPro union path)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
    ),
    FeatureDoc(
        name="interpro_present",
        family="interpro",
        summary="Whether the InterPro source proposed this candidate for the (protein, term).",
        definition=(
            "Presence flag: True when the InterPro source contributed this "
            "candidate. Default False on a KNN leaf record with no InterPro "
            "evidence; set True by the InterPro post-pass / union path."
        ),
        producer="protea.core._interpro_features.apply_interpro_features (default _interpro_default_fields)",
        status=FeatureStatus.PRODUCED,
        unit="flag",
        value_range="False or True",
        notes="Env-gated table (see interpro_hit).",
    ),
    # ── LAFA classifier family (DECLARED_ABSENT per ADR-D45) ────────────────
    FeatureDoc(
        name="classifier_score",
        family="classifier",
        summary="Full-catalogue direct classifier score for this candidate GO term.",
        definition=(
            "Per-candidate score from the direct full-catalogue predictor "
            "(the first-place LAFA classifier). The producer "
            "``protea.core.operations.predict_go_terms._classifier.apply_classifier`` "
            "(and the export post-pass "
            "``protea.core.training_dump._classifier_postpass.apply_classifier_to_frame``) "
            "computes it, but only when the ``compute_classifier`` flag is set. "
            "It defaults to ``False`` on the export payload, so the default "
            "research-dataset export never fills this column."
        ),
        producer="protea.core.operations.predict_go_terms._classifier.apply_classifier (gated by compute_classifier, default False; export default emits NaN via _lafa_default_fields)",
        status=FeatureStatus.DECLARED_ABSENT,
        unit="score",
        value_range="producer-dependent; NaN in the default export",
        notes=(
            "ADR-D45: the default export emits NaN (was a well-defined 0.0 before "
            "PROTEA #710). The sealed 0.4063 champion was trained without the "
            "classifier family precisely because it was absent. The schema "
            "fingerprint pins names, not values, so a booster selecting this "
            "family still passes the schema-sha guard."
        ),
    ),
    FeatureDoc(
        name="classifier_present",
        family="classifier",
        summary="Whether the direct classifier proposed this candidate GO term.",
        definition=(
            "Presence flag for the direct full-catalogue classifier source. "
            "Produced by the same classifier producer, gated by "
            "``compute_classifier`` (default False), so the default export never "
            "fills it."
        ),
        producer="protea.core.operations.predict_go_terms._classifier.apply_classifier (gated by compute_classifier, default False; export default emits NaN via _lafa_default_fields)",
        status=FeatureStatus.DECLARED_ABSENT,
        unit="flag",
        value_range="0.0 or 1.0 when produced; NaN in the default export",
        notes="ADR-D45: DECLARED_ABSENT in the default export. See classifier_score.",
    ),
    # ── LAFA self-prior family (DECLARED_ABSENT per ADR-D45) ────────────────
    FeatureDoc(
        name="self_prior_score",
        family="self_prior",
        summary="Score from the query protein's own pre-cutoff non-experimental annotations.",
        definition=(
            "Self-prior signal: how strongly the query protein's own pre-cutoff "
            "non-experimental annotations support this candidate term. Produced "
            "by ``protea.core.operations.predict_go_terms._post_knn_pipeline.apply_self_prior``, "
            "gated by ``compute_self_prior`` (default False), so the default "
            "research-dataset export leaves it at the NaN default."
        ),
        producer="protea.core.operations.predict_go_terms._post_knn_pipeline.apply_self_prior (gated by compute_self_prior, default False; export default emits NaN via _lafa_default_fields)",
        status=FeatureStatus.DECLARED_ABSENT,
        unit="score",
        value_range="producer-dependent; NaN in the default export",
        notes="ADR-D45: DECLARED_ABSENT in the default export. See classifier_score.",
    ),
    # ── LAFA cross-aspect association family (DECLARED_ABSENT per ADR-D45) ───
    FeatureDoc(
        name="association_total",
        family="association",
        summary="Conditional probability of the candidate term given the query's known terms.",
        definition=(
            "Total cross-aspect association: the conditional probability of the "
            "candidate term given the query protein's pre-cutoff known terms, "
            "over all branches. Produced by "
            "``protea.core.operations.predict_go_terms._post_knn_pipeline.apply_association``, "
            "gated by ``compute_association`` (default False), so the default "
            "export leaves it at the NaN default."
        ),
        producer="protea.core.operations.predict_go_terms._post_knn_pipeline.apply_association (gated by compute_association, default False; export default emits NaN via _lafa_default_fields)",
        status=FeatureStatus.DECLARED_ABSENT,
        unit="probability",
        value_range="0.0..1.0 when produced; NaN in the default export",
        notes="ADR-D45: DECLARED_ABSENT in the default export. See classifier_score.",
    ),
    FeatureDoc(
        name="association_cross",
        family="association",
        summary="Cross-branch-only conditional probability of the candidate given known terms.",
        definition=(
            "Cross-branch component of the association signal: the conditional "
            "probability of the candidate term given the query's known terms, "
            "restricted to terms in a different GO aspect. Same producer and "
            "gating as ``association_total``."
        ),
        producer="protea.core.operations.predict_go_terms._post_knn_pipeline.apply_association (gated by compute_association, default False; export default emits NaN via _lafa_default_fields)",
        status=FeatureStatus.DECLARED_ABSENT,
        unit="probability",
        value_range="0.0..1.0 when produced; NaN in the default export",
        notes="ADR-D45: DECLARED_ABSENT in the default export. See classifier_score.",
    ),
    FeatureDoc(
        name="association_present",
        family="association",
        summary="Whether the association source proposed this candidate GO term.",
        definition=(
            "Presence flag for the cross-aspect association source. Same "
            "producer and gating as ``association_total`` (``compute_association``, "
            "default False), so the default export leaves it at the NaN default."
        ),
        producer="protea.core.operations.predict_go_terms._post_knn_pipeline.apply_association (gated by compute_association, default False; export default emits NaN via _lafa_default_fields)",
        status=FeatureStatus.DECLARED_ABSENT,
        unit="flag",
        value_range="0.0 or 1.0 when produced; NaN in the default export",
        notes="ADR-D45: DECLARED_ABSENT in the default export. See classifier_score.",
    ),
    # ── Categorical annotation metadata (family "annotation_meta") ──────────
    FeatureDoc(
        name="qualifier",
        family="annotation_meta",
        summary="GO annotation qualifier carried by the reference annotation.",
        definition=(
            "The GO qualifier string of the reference annotation that supplied "
            "this candidate term (for example ``enables``, ``NOT``), empty when "
            "absent. Categorical: encoded to a stable integer code by the lab."
        ),
        producer=f"{_LEAF}.make_leaf_record (from the reference annotation record)",
        status=FeatureStatus.PRODUCED,
        unit=None,
        value_range="GO qualifier vocabulary; empty string when absent",
        notes="Categorical feature.",
    ),
    FeatureDoc(
        name="evidence_code",
        family="annotation_meta",
        summary="GO evidence code of the reference annotation.",
        definition=(
            "The GO evidence code of the reference annotation that supplied this "
            "candidate term (for example ``EXP``, ``IEA``), empty when absent. "
            "Categorical: encoded to a stable integer code by the lab."
        ),
        producer=f"{_LEAF}.make_leaf_record (from the reference annotation record)",
        status=FeatureStatus.PRODUCED,
        unit=None,
        value_range="GO evidence-code vocabulary; empty string when absent",
        notes="Categorical feature.",
    ),
    FeatureDoc(
        name="aspect",
        family="annotation_meta",
        summary="GO aspect (BP / MF / CC) of the candidate term.",
        definition=(
            "The GO aspect of the candidate term, read from the runner's "
            "aspect map (biological process, molecular function or cellular "
            "component). Categorical: encoded to a stable integer code by the "
            "lab. Also a reserved column."
        ),
        producer=f"{_LEAF}.make_leaf_record (runner.aspect_map)",
        status=FeatureStatus.PRODUCED,
        unit=None,
        value_range="one of the three GO aspects",
        notes="Categorical feature; also present in RESERVED_COLUMNS.",
    ),
    # ── Pool-stage injected context (families "plm_context", "k_neighborhood")
    FeatureDoc(
        name="plm_id",
        family="plm_context",
        summary="Which protein language model produced the embeddings used for KNN retrieval.",
        definition=(
            "Categorical code identifying the PLM whose embeddings retrieved the "
            "candidate. The PROTEA dump does not write this column; the lab's "
            "pooled multi-manifest loader injects it as a per-source constant at "
            "stage time so the universal multi-PLM booster sees which PLM a row "
            "came from."
        ),
        producer="lab pooled multi-manifest loader (injected at pool stage; absent from raw parquet dumps)",
        status=FeatureStatus.POOL_INJECTED,
        unit=None,
        value_range="PLM identifier vocabulary",
        notes="Categorical feature. See PROTEA FEATURE_LEAKAGE_AUDIT.md for the GO/NO-GO ruling on this column.",
    ),
    FeatureDoc(
        name="k_context",
        family="k_neighborhood",
        summary="KNN neighbourhood size (K) used to retrieve this candidate.",
        definition=(
            "The K-neighbourhood size for the manifest source that produced this "
            "row. The PROTEA dump does not write this column; the lab's pooled "
            "loader injects it as a per-source constant at stage time so a booster "
            "trained over several K settings can condition on K."
        ),
        producer="lab pooled multi-manifest loader (injected at pool stage; absent from raw parquet dumps)",
        status=FeatureStatus.POOL_INJECTED,
        unit="neighbours",
        value_range="bare count, positive",
    ),
]

#: Single source of truth for feature documentation. Maps each canonical
#: column name to its :class:`FeatureDoc`. The drift lint asserts this covers
#: exactly :data:`feature_schema.ALL_FEATURES`.
FEATURE_DOCS: Mapping[str, FeatureDoc] = {doc.name: doc for doc in _DOCS}
