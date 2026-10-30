=====
flint
=====

Flint is a framework for building Fortran code analysis tools in Python.  It
includes a basic command line tool for linting and code checks, and a more
general API for developing one's own custom tests.

More generally, flint provides an interface to a Fortran source code project
within a Python environment.

Flint is in the early stages of development, but currently provides some basic
functionality.


Installation
============

In most cases, flint can be installed with ``setup.py``

.. code:: python

   python setup.py install --user

If you want to install it in your system directories (and have permission):

.. code:: python

   python setup.py install

This may not work for some users, and more elegant installation methods ought
to be available in the future, depending on how well-received this project
becomes.


Basic usage
===========

Current functionality is described below.  During this very early stage of
development, features may change, expand, or be dropped without any notice.


Commands
--------

Use ``flint`` to invoke the CLI.  The following tools have been implemented
with limited features.

``flint report``
   Apply a generic linter and static analysis to a Fortran project.

   The following tests are included:

   * Trailing whitespace
   * Indents with mixed tabs and spaces
   * Tabs within statements
   * Excessive line length (both with and without comments)

``flint gendoc``
   Generates a reST documentation file based on docstrings in the source code.
   Currently follows the Doxygen convention.

``flint format``
   In principle, this will provide a formatted version of an input source code.
   Currently, it returns each statement with whitespace and comments removed.

``flint tag``
   Return the input files, with statements tagged based on type.  For example,
   a ``module`` statement is tagged with the letter ``M``.

   This is primarily a debugging tool, but might be of interest to users.


Development API
---------------

Flint provides an interface to the details of the source code, which can be
used to develop tools which are customized to your project.

To parse the source code, call the ``parse()`` function with the top-level
directory of your project.

.. code:: python

   import flint

   project = flint.parse('path/to/source')

This functions returns a ``Project`` object, which itself contains several
objects representing the contents and attributes of the source code.

For example, the following code block will return a list of all the modules and
its derived types.

.. code:: python

   for mod in proj.modules:
       for dtype in mod.derived_types:
           print(dtype.name)

For more examples, inspect the ``flint/tools`` directory, which describe the
command line tools.


How it Works
============

Flint is broken into three stages, which closely resemble compiler frontends.

1. The ``Scanner`` object takes an input stream and returns the "lexemes", the
   "words" of the grammar.  No semantic meaning is attached to them at this
   stage.

   One important feature of ``Scanner`` is that it also preserves the
   non-semantic lexemes.  Examples include grouped whitespace, endlines, and
   comments.

   Users would generally not use the ``Scanner`` since it is a component of the
   ``Lexer``, which is described below.


2. The lexemes are passed to the ``Lexer``, which is structured as an iterator.
   It has three major responsibilities:

   1. Lexemes are identified as either semantic or *liminal*, which is our term
      for non-semantic tokens such as whitespace, comments, or statement
      separators (``;``).

   2. Lexemes are converted from lines to ``Statements``.  A statement may span
      many lines (``&``), or a line may contain many statements (``;``).  The
      ``Lexer`` will resolve these cases and return the next semantic
      ``Statement``.

   3. Preprocessing is applied at this stage.  Macro substitutions are applied,
      but the original macro name is preserved.

   Each iteration of the lexer returns a ``Statement``, which is a ``list``
   subclass containing the ``Token`` lexemes.

   Each ``Token`` contains a ``head`` and ``tail``, which point to lists of the
   "liminals" inbetween the semantic lexemes.  This includes whitespace
   (including endlines), line breaks (``&``), statement terminators (``;``),
   and comments. Each ``Token`` stores lowercase semantic text as its string
   value, except that quoted string literals retain their case. The original
   spelling is retained in ``token.original`` and returned by ``str(token)``.
   Equality and hashing use ordinary string operations: compare names with
   lowercase strings, such as ``token == 'field'``, not ``token == 'FIELD'``.
   Token-to-token comparisons normalize both names at construction time.

   Slicing, joining, and other inherited string operations use semantic text.
   For source output use ``str(token)`` or ``Statement.source_text()``; for
   example, use ``''.join(map(str, tokens))`` to preserve spelling. Literal
   contents are case-sensitive. Preprocessed tokens compare and hash by their
   semantic value while ``str(token)`` returns their macro source text.

   There is also a ``PToken`` subclass from preprocessed content.  These tokens
   display as the original unprocessed lexemes, but are evaluated as the
   postprocessed value.  For example, macros appear unchanged but use their
   substituted value in comparison tests.  Values from an ``#include``
   statement appear as empty strings but are returned as semantically valid
   statements.

   Although we call these "tokens", they are not quite equivalent to the tokens
   produced by a compiler's parser, since we do not yet classify them into, for
   example, identifiers or operators.  There is some advantage in deferring
   this, since most Fortran keywords can also be used as identifiers.

   As with the ``Scanner``, most users will never need to interact with the
   ``Lexer``, which is a component of the ``Parser`` described below.


3. Finally, the ``Lexer`` output is passed to the ``Parser``, which interprets
   the semantic contents to recreate an abstraction of the source code and its
   components.

   This is where modules, subprograms, variables, and other content are
   organized into equivalent data structures which can be probed and traversed
   for further analysis.

   The ``Parser`` is contained with the ``Source`` objects, which represent
   abstractions of the source code (aka "translation units" in compiler-talk).

   If working as intended, this should be the only level at which the user is
   required to interact with the parser.

   This is also the least developed part of flint, so at this point I will just
   say to watch this space for future work.


Experimental declaration grammar
================================

``flint.declarations.parse_declaration(statement)`` recognizes the structure of
a type declaration using an explicit grammar tree. It returns a ``Declaration``
with half-open token spans for the type specifier, attributes, entities, and
initializers, plus the index of ``::`` when present. Slice the original statement
with these spans to retain token identity, original spelling, and whitespace::

   from flint.declarations import parse_declaration

   declaration = parse_declaration(statement)
   if declaration is not None:
       for start, end in declaration.entities:
           entity_tokens = statement[start:end]

The grammar covers intrinsic, derived, and polymorphic type declarations,
including nested selectors, array/coarray shapes, and initialization. Expressions
inside these regions remain opaque; recognition is not full Fortran validation.
Attribute compatibility and scope constraints are not checked. Unsupported forms
(including procedure declarations and nonstandard type-size syntax) return
``None`` so callers can retain their existing analysis path.

This API is opt-in while the grammar is evaluated as a replacement for existing
declaration analysis. It does not mutate or cache statements. Recompute spans
after inserting, removing, or replacing tokens. The rule descriptions follow
J3/24-007 R703 and R801-R805.


Unimplemented Features
======================

The "unknown unknowns" probably exceed the "known unknowns" at this stage, but
we are aware of the following issues.

* The Fortran expressions themselves remain unparsed beyond identification of
  its tokens.  Further parsing such as AST generation is not yet attempted.

* Expressions inside of an ``#if`` or ``#elif`` statement are not parsed, and
  for simplicity are currently assumed to always be false.

  To fix this would require a full expression parser, which is not yet
  available.
