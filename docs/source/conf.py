# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = "Pure3270"
copyright = "2025, Pure3270 Contributors"
author = "Pure3270 Contributors"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.ifconfig",
    "sphinx.ext.githubpages",
    "sphinx.ext.mathjax",
    "sphinx.ext.inheritance_diagram",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = ".rst"

master_doc = "index"

language = None

# -- Options for HTML output -------------------------------------------------
html_theme = "alabaster"
html_static_path = ["_static"]

# -- Options for HTMLHelp output ---------------------------------------------
htmlhelp_basename = "Pure3270doc"

# -- Options for LaTeX output ------------------------------------------------
latex_elements = {}

latex_documents = [
    (
        master_doc,
        "Pure3270.tex",
        "Pure3270 Documentation",
        "Pure3270 Contributors",
        "manual",
    ),
]

# -- Options for manual page output ------------------------------------------
man_pages = [(master_doc, "pure3270", "Pure3270 Documentation", [author], 1)]

# -- Options for Texinfo output ----------------------------------------------
texinfo_documents = [
    (
        master_doc,
        "Pure3270",
        "Pure3270 Documentation",
        author,
        "Pure3270",
        "One line description of project.",
        "Miscellaneous",
    ),
]

# -- Options for Epub output -------------------------------------------------
epub_name = "pure3270.epub"
epub_exclude_files = ["search.html"]

# -- Extension configuration -------------------------------------------------
autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

todo_include_todos = True
