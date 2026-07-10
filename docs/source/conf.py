"""Sphinx configuration for ``protea-contracts``."""

from __future__ import annotations

import os
import sys
from importlib.metadata import version as _pkg_version

sys.path.insert(0, os.path.abspath("../../src"))
sys.path.insert(0, os.path.abspath("_ext"))

# ── Project info ─────────────────────────────────────────────
project = "protea-contracts"
author = "Francisco Miguel Pérez Canales"
copyright = "2026, Francisco Miguel Pérez Canales"

try:
    release = _pkg_version("protea-contracts")
except Exception:
    release = "0.1.0"
version = release

# ── Extensions ───────────────────────────────────────────────
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "feature_docs_table",
]

autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "special-members": "__init__",
    "exclude-members": "__weakref__,__init_subclass__,__subclasshook__",
}
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# protea-contracts is the contract surface and has no heavy deps:
# pydantic, numpy, pyarrow are imported during autodoc unmocked.

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pydantic": ("https://docs.pydantic.dev/latest", None),
}

# ── HTML output ──────────────────────────────────────────────
html_theme = "shibuya"
html_title = "protea-contracts"
html_static_path: list[str] = []

templates_path = ["_templates"]
exclude_patterns: list[str] = []

master_doc = "index"
