"""Sphinx directive that renders the feature-documentation registry.

Registers ``.. feature-docs-table::``, which builds the reference table
directly from :data:`protea_contracts.feature_docs.FEATURE_DOCS` at build
time. The table is never written by hand: editing a :class:`FeatureDoc` in
``src/protea_contracts/feature_docs.py`` is the only way to change what this
page shows, so the docs cannot drift from the source of truth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def _rst_escape(text: str) -> str:
    """Neutralise characters that would break an RST grid/field rendering."""
    return text.replace("\\", "\\\\").replace("`", "\\`")


def _render_rst() -> list[str]:
    """Produce the RST lines for the whole registry, grouped by family."""
    from protea_contracts.feature_docs import FEATURE_DOCS
    from protea_contracts.feature_schema import ALL_FEATURES, FEATURE_FAMILIES

    # Preserve the declared column order within each family group.
    order = {name: i for i, name in enumerate(ALL_FEATURES)}
    by_family: dict[str, list[str]] = {}
    for name, doc in FEATURE_DOCS.items():
        by_family.setdefault(doc.family, []).append(name)

    lines: list[str] = []
    lines.append(f"There are **{len(FEATURE_DOCS)}** documented feature columns.")
    lines.append("")

    for family in FEATURE_FAMILIES:
        names = by_family.get(family)
        if not names:
            continue
        names.sort(key=lambda n: order.get(n, 0))
        lines.append(f".. rubric:: Family ``{family}``")
        lines.append("")
        for name in names:
            doc = FEATURE_DOCS[name]
            lines.append(f"``{name}``")
            lines.append(f"   {_rst_escape(doc.summary)}")
            lines.append("")
            lines.append(f"   :Status: {doc.status.value}")
            lines.append(f"   :Producer: ``{_rst_escape(doc.producer)}``")
            if doc.unit:
                lines.append(f"   :Unit: {_rst_escape(doc.unit)}")
            if doc.value_range:
                lines.append(f"   :Range: {_rst_escape(doc.value_range)}")
            lines.append(f"   :Definition: {_rst_escape(doc.definition)}")
            if doc.notes:
                lines.append(f"   :Notes: {_rst_escape(doc.notes)}")
            lines.append("")
    return lines


class FeatureDocsTableDirective(Directive):
    """``.. feature-docs-table::`` -> the registry rendered from FEATURE_DOCS."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        rst = _render_rst()
        container = nodes.container()
        self.state.nested_parse(
            StringList(rst, source="feature_docs.py"), self.content_offset, container
        )
        return container.children


def setup(app: Sphinx) -> dict[str, object]:
    app.add_directive("feature-docs-table", FeatureDocsTableDirective)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
