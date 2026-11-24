=====
Flint
=====

Flint is a Python library and command-line toolkit for understanding and working
with Fortran source code.

Flint provides an API for exploring and analyzing source code, and making
precise, context-aware changes where needed.  Command-line tools built on this
API cover common tasks, from linter-style checks to higher-level features such
as comment analysis and documentation generation.

Flint is under active development.  Its analysis is structural rather than a
substitute for compiler validation, and its APIs may change.


Installation
============

Flint requires Python 3.10 or newer.  From a source checkout::

   python -m venv .venv
   source .venv/bin/activate
   python -m pip install .

On Windows, activate the environment with ``.venv\Scripts\activate`` in Command
Prompt.  Graphviz is optional and is needed only to render SVG call graphs.


Everyday usage
==============

Commands accept source files or directories.  Directory discovery selects
``.f90`` and ``.F90`` files.  Use ``-I include/`` to supply additional include
directories and ``--exclude vendor/`` to omit dependency trees.


Check formatting
----------------

Report spacing and indentation issues, preview spacing fixes, or apply them::

   flint format src/
   flint format --diff src/
   flint format --write src/

Files are edited only with ``--write``.  Indentation and real-addition grouping
checks report issues without changing them.  Report and diff modes return a
nonzero exit status when issues remain.

Use ``flint format --list-rules`` to see available rules.  Project settings can
be stored in ``flint.toml``.


Check source documentation
--------------------------

Find declarations with missing documentation::

   flint check-docs src/

The default policy checks concrete derived types, named interfaces and generic
bindings, module variables, and type components, with some exclusions.  Add
``--strict`` to also require descriptions for modules and procedures, among
other entities; add ``--arguments`` to check dummy arguments.  Documentation
uses explicit ``!>``, ``!<``, or ``!!`` markers.  Missing required
documentation produces a nonzero exit status.


Generate reference documentation
--------------------------------

Generate reStructuredText reference pages from source comments::

   flint gendoc src/ -o reference/

Comments are treated as plain prose by default.  Use ``--markup rst`` for
native reStructuredText or ``--markup doxygen`` for supported Doxygen markup.
Flint generates reference sources, not a complete website; render the pages
with a separate reST tool.  Cross-module HTML links, indexes, and call graphs
are available through additional options.

Run ``flint --help`` or ``flint COMMAND --help`` for command-line options.
``python -m flint`` provides the same interface.  The ``report`` and ``tag``
commands provide basic lint reports and statement tags.


Using Flint from Python
=======================

Parse a project and list its named modules and derived types::

   import flint

   project = flint.parse("src")
   for module in project.modules:
       if not module.name:
           continue
       print(module.name)
       for dtype in module.derived_types:
           print("  ", dtype.name)

The same parsed source can support custom checks, documentation extraction,
and formatting analysis.


Documentation
=============

See the `documentation index <docs/index.rst>`_ for detailed usage:

* `Command-line tools <docs/guide.rst#commands>`_.
* `Formatting rules <docs/guide.rst#formatting-rules>`_ and
  `project configuration <docs/guide.rst#project-formatting-configuration>`_.
* `Documentation checks and generation <docs/guide.rst#documentation-generation>`_.
* `Python API and custom checks <docs/guide.rst#development-api>`_.
* `Parser architecture <docs/guide.rst#how-it-works>`_.
* `Supported scope and limitations <docs/limitations.rst>`_.

Fortran and preprocessor coverage is partial.  Flint does not provide complete
type checking, overload selection, or dynamic-dispatch resolution.


Development
===========

Install an editable checkout and run the test suite::

   python -m pip install -e . docutils
   python -m unittest discover -s test -v

Some optional tests require Graphviz or external project tooling.


License
========

Flint is distributed under the `Apache License, Version 2.0 <LICENSE>`_.
See also `NOTICE <NOTICE>`_ and `AUTHORS <AUTHORS>`_.
