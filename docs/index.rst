===================
Flint documentation
===================

Start with the `README <../README.rst>`_ for installation and basic workflows.
The `user and API guide <guide.rst>`_ contains the detailed reference.

Command-line tools
==================

* `Commands <guide.rst#commands>`_: report, format, check-docs, gendoc, and tag.
* `Formatting rules <guide.rst#formatting-rules>`_: selection, diagnostics,
  previewing edits, and writing changes.
* `Project configuration <guide.rst#project-formatting-configuration>`_:
  flint.toml settings and command-line overrides.
* `Preprocessing <guide.rst#preprocessing>`_: macro expansion and source preservation.

Source documentation
====================

* `Documentation presence checks <guide.rst#documentation-presence-checks>`_.
* `Generating the reference <guide.rst#generating-the-reference>`_:
  source selection, markup formats, and output.
* `Cross-module documentation links <guide.rst#cross-module-documentation-links>`_.
* `Call graph diagrams <guide.rst#call-graph-diagrams>`_.

Python API and internals
========================

* `Development API <guide.rst#development-api>`_: declarations, variables,
  comment associations, and custom checks.
* `Type-bound procedures <guide.rst#type-bound-procedures>`_.
* `Streaming source locations <guide.rst#streaming-source-locations>`_.
* `Shared spacing runner <guide.rst#shared-spacing-runner>`_.
* `Experimental declaration grammar <guide.rst#experimental-declaration-grammar>`_.
* `How it works <guide.rst#how-it-works>`_: scanner, lexer, tokens, and parser.

Scope
=====

Read `Supported scope and limitations <limitations.rst>`_ before relying on
analysis results for a new codebase.
