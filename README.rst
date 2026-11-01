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
   Report spacing and indentation issues with file, line, and rule name.
   Use ``--diff`` to preview spacing fixes or ``--write`` to apply them.

``flint tag``
   Return the input files, with statements tagged based on type.  For example,
   a ``module`` statement is tagged with the letter ``M``.

   This is primarily a debugging tool, but might be of interest to users.


Formatting rules
----------------

Formatting is one application of Flint's parsing and source-analysis API.
All selected rules share one project parse::

   flint format src/
   flint format --diff src/
   flint format --write src/
   flint format --only assignment-spacing,operator-spacing src/
   flint format --skip callable-comma-spacing src/
   flint format --only indentation src/
   flint format --list-rules

``python -m flint`` also invokes the CLI. Source paths may be files or
directories. ``--only`` and ``--skip`` accept repeatable, comma-separated rule
names. All four rules run by default; skipping takes precedence over selection.
Unknown names are errors.

* ``assignment-spacing`` spaces assignments and removes spaces around named
  argument equals signs. ``--do-controls`` also normalizes DO-control spacing.
* ``operator-spacing`` spaces binary operators and normalizes unary spacing,
  preserving existing exceptions for exponentiation, concatenation, DO controls,
  and arithmetic inside callable or subscript groups.
* ``callable-comma-spacing`` spaces commas in known callable argument lists,
  preserving array subscripts. Repeat ``--exclude-function NAME`` to exempt
  particular callables (case-insensitive).
* ``indentation`` checks four-space block bodies, with unindented module contents.
  The configuration setting ``format.indentation.width`` sets a positive number
  of spaces per level (default 4).
  Continuations require at least eight extra spaces, except declarations (four)
  and continued single-line IF actions (four). ``--strict`` requires eight extra
  spaces for declarations too, while retaining manual continuation alignment.
  Comments, preprocessor directives, and inactive branches are skipped.
  Legacy label-terminated DO loops are not supported.
  With a custom width, continuation minima scale to two levels, or one level
  for the declaration and IF-action exceptions.

Default spacing is a minimum, preserving extra alignment spaces. ``--strict``
requests exact spacing. These retain the policies of the original scripts;
indentation fixes are future work.

Report and diff modes return 1 when changes are needed, otherwise 0. Successful
writes return 0 unless selected diagnostic-only rules still find issues.
Indentation is diagnostic-only: it reports issues in every mode, including
``--diff`` and ``--write``, and returns 1 when they remain. Spacing fixes can
still be applied in the same invocation. ``--diff --write`` both previews and
applies the spacing changes.
The default never writes source files.

Python callers can reuse a parsed project and obtain proposals without output
or writes:

.. code:: python

   from flint.formatting.rules import select_rules
   from flint.formatting.runner import check_spacing, report_spacing

   project = flint.parse('src')
   rules = select_rules(only=['assignment-spacing', 'operator-spacing'])
   changes = list(check_spacing(project, rules.values()))
   for change in changes:
       print(change.path, change.formatted)
   report_spacing(changes, diff=True)

``select_rules`` also accepts ``skip``, ``strict``, ``do_controls``, and
``excluded_functions``. Individual rule modules expose ``prepare_check`` for
callers needing different options for each rule. Keep source files unchanged
between parsing and checking; reparse after applying edits.

Diagnostic-only rules use ``select_diagnostic_rules`` with the same rule names,
``only``, ``skip``, and ``strict`` options, plus ``indent=4`` for the width.
``select_rules`` returns spacing
checks; ``select_diagnostic_rules`` returns source-to-issues callables:

.. code:: python

   from flint.formatting.rules import select_diagnostic_rules

   for name, check in select_diagnostic_rules(only=['indentation']).items():
       for source in project.sources:
           for issue in check(source):
               print(issue.path, issue.line_number, name, issue.message)

The direct API is ``flint.formatting.indentation.indentation_issues(source,
strict=False, indent=4)``. Both APIs reuse the caller's project without reparsing
or writing.


Project formatting configuration
--------------------------------

``flint format`` discovers the nearest ``flint.toml`` in the current working
directory or its parents. Only that file is loaded; files are not merged.
Discovery starts from the working directory, not each source path.
``--config PATH`` selects an explicit file instead. An empty configuration file
can be used to bypass project settings. Missing explicit files, invalid TOML,
unknown settings, and invalid values are errors before source parsing.

For example:

.. code:: toml

   [format]
   rules = ["assignment-spacing", "operator-spacing", "callable-comma-spacing", "indentation"]
   exclude = ["vendor"]

   [format.assignment-spacing]
   strict = false
   do-controls = false

   [format.operator-spacing]
   strict = false

   [format.callable-comma-spacing]
   strict = false
   excluded-functions = ["min", "max"]

   [format.indentation]
   width = 2
   module-contents = false
   continuation-width = 4
   declaration-continuation-width = 2
   strict = false

Precedence is explicit CLI options, then project settings, then Flint defaults.
``--only`` replaces the configured rule list; ``--skip`` removes rules from the
selection. CLI exclusion lists replace their configured lists rather than
appending. Configured excluded directories are relative to the configuration
file; CLI paths remain relative to the working directory. Omitting ``rules``
enables all built-ins; ``rules = []`` enables none.

``--strict`` and ``--no-strict`` override strictness for every selected rule.
``--do-controls`` and ``--no-do-controls`` override assignment DO-control policy.
Block width is set by ``format.indentation.width``. Explicit continuation widths remain
independent; when omitted, they default to twice the block width (ordinary
continuations) and once the block width (declarations). Strict indentation uses
the ordinary continuation width for declarations too. The IF-action exception
always uses one block width. Module headers and ``contains`` remain aligned;
``module-contents = true`` indents module bodies by one level.

Python scripts use the same configuration and override machinery:

.. code:: python

   from flint.formatting.config import load_config, configured_rules
   from flint.formatting.runner import check_spacing

   settings = load_config('flint.toml')
   checks, diagnostics = configured_rules(settings, only=['indentation'])
   project = flint.parse('src', excludes=settings.get('exclude'))
   for name, check in diagnostics.items():
       for source in project.sources:
           for issue in check(source):
               print(issue.path, issue.line_number, name, issue.message)
   changes = list(check_spacing(project, checks.values()))

``configured_rules`` also accepts a plain Python mapping shaped like the TOML
``format`` table. Explicit ``False`` and empty lists override settings; ``None``
means omitted. No configuration is discovered by this function itself.
Python 3.11+ uses ``tomllib``; older supported Python versions install ``tomli``.


Development API
---------------

Custom checks can iterate a unit's declared variables directly:

.. code:: python

   def inspect(unit):
       for variable in unit.variables:
           if variable.type != 'real':
               continue
           location = variable.location
           documentation = variable.documentation
           if documentation is None:
               continue  # Unsupported declaration; choose a reporting policy.
           for block in documentation:
               print(variable.name, location, block.comments)
   for source in project.sources:
       for root in source.units:
           for unit in root.walk():
               inspect(unit)

``unit.variables`` contains that unit's declarations, not those of nested units.
``unit.walk()`` traverses nested derived types, implementation procedures, and
explicit interface bodies. Interface bodies are exposed separately through
``unit.interfaces[i].subprograms``; generic procedure references remain names in
``interface.procedures``. Use ``walk(include_interfaces=False)`` for analyses
that want implementation scopes only. Interface arguments have the same variable
source/documentation API as implementation arguments, with distinct scopes.
Standard type declarations are extracted using grammar spans so shapes and
initializer expressions cannot introduce spurious variables. ``double
precision`` variables have ``type == 'real'``; their full type syntax remains
available from ``variable.declaration.type_tokens``. Entity shapes override
declaration-wide DIMENSION attributes.

``variable.declaration`` is a source entity view, ``declaration_tokens`` exposes
its original tokens and whitespace tails, ``location`` locates the name token,
and ``documentation`` provides associated comment blocks. These source views
are computed on demand without retained caches. Unsupported declarations return
``None`` for declaration/documentation views; recognized declarations without
comments return an empty tuple. Locations may be absent for undisplayed tokens.
The historical ``variable.doc`` interface remains available for existing clients;
new policy checks should use ``documentation`` for explicit association evidence.

Custom declaration checks can inspect source entities without reconstructing
the declaration's comma nesting or searching for names by spelling:

.. code:: python

   from flint.declarations import declared_entities

   for source in project.sources:
       for statement in source.statements:
           entities = declared_entities(statement)
           if entities is None:
               continue  # Unrecognized declaration; callers may supply fallback.
           for entity in entities:
               print(entity.name, entity.type_tokens, entity.attribute_tokens)
               if entity.location is not None:
                   print(source.path, entity.location.line)

Each entity references the original statement, its parsed declaration, and a
half-open entity token span. ``name_index`` identifies the actual declaration
token even if the same name occurs earlier in a selector or dimension attribute.
Standard type declarations with and without ``::`` are supported; procedure
declarations and compiler extensions may return ``None``. Locations are absent
for tokens with no displayed span. These are syntactic source views, not
scope-resolved symbols; recompute them after token edits.

Object-like macro expansions are matched using their semantic tokens, excluding
the source-only macro-name anchors. Returned declaration spans still index the
original statement, preserving source spelling and whitespace. Use
``flint.token.semantic_tokens(tokens)`` to inspect such a span without its
anchors; hidden expansion and included-file tokens remain in that view.

Comment associations are exposed separately, without imposing documentation
requirements:

.. code:: python

   from flint.documentation import declaration_comments, entity_comments

   entities = declared_entities(statement)
   if entities is not None:
       blocks = declaration_comments(statement, entities)
       for entity in entities:
           for block in entity_comments(entity, blocks):
               print(entity.name, block.placement, block.kind, block.comments)

``CommentBlock`` records comment text, first and last physical lines, placement
(``leading``, ``trailing``, or ``following``), and kind (``forward`` for ``!>``,
``backward`` for ``!<``, or ``plain``). ``entity_index`` is the name-token index,
or ``None`` for declaration-wide documentation.

Leading forward documentation is declaration-wide. Comments within an entity
or after its separating comma belong to that entity. A final trailing comment
on a single-line entity list is shared by the declaration. Within a continued
declaration, a comment after several names on one physical line is shared by
those names, with one association per entity; it does not apply to other lines.
Comments inside unfinished shapes or initializers remain entity-specific.
Adjacent following plain comments are
exposed as candidates so callers can decide whether to accept them. Blank lines
and new forward-documentation markers terminate trailing/following association.
Conflicting forward and backward blocks are retained as evidence, not resolved
by Flint. The caller decides whether they are an error and what constitutes
valid documentation. Unsupported declarations return ``None`` for fallback.

Consecutive trailing comment lines remain one block, including repeated ``!<``
markers and mixtures of ``!!`` and ``!<``. A backward marker anywhere in such a
block identifies it as backward documentation. Blank lines, intervening code,
and new forward blocks prevent these associations from being merged.

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


Streaming source locations
==========================

``flint.locations.source_locations(source)`` yields ``(statement, location)``
pairs without adding token fields or storing an index. Each location includes
the token, its index within the statement, and one-based ``line``, ``column``,
``end_line``, and ``end_column`` coordinates. Ends are exclusive; columns count
characters, not bytes or expanded tabs. Consume the iterator directly to keep
memory bounded; collecting all results into a list naturally retains them.

``statement_locations(statement)`` provides the same locations for an isolated
statement. Columns are ``None`` until an absolute column can be determined from
a newline or the optional ``column=`` argument. This matters for statements
following a semicolon. Whole-source traversal provides exact columns.

Positions describe the current rendered source and must be recomputed after
edits. A continued token can span several lines. Macro tokens that display an
invocation point to that invocation; invisible expansion tokens have no separate
span and are omitted. This API does not reconstruct included-file origins.


Shared spacing runner
=====================

``flint.formatting.runner`` separates checking from reporting and writing.
A check is a function that receives a source and returns a statement edit
collector. This permits scope-dependent checks to prepare context once per file.
Several checks can share one parse and propose edits against the same unchanged
tokens::

   import flint
   from flint.formatting.runner import check_spacing, report_spacing
   from flint.formatting.spacing import spacing_edits

   def assignment_check(source):
       def collect(statement):
           for token in statement:
               if token.syntax_role == 'assignment':
                   yield from spacing_edits(token, ' ', ' ')
       return collect

   project = flint.parse('src')
   results = list(check_spacing(project, [assignment_check]))
   status = report_spacing(results, diff=True)

``FileChange`` results expose the path, original text, proposed text, and changed
lines. ``report_spacing`` supports ``report``, ``diff``, and ``write``; a dry run
returns 1 when changes are proposed, otherwise 0. ``run_spacing`` is a convenience
wrapper accepting paths and excludes, or an existing ``project``. Source files
must remain unchanged between parsing and checking. After writing edits, reparse
before another run. Identical gap edits coalesce; conflicting edits raise an
error. Checks retain their own policies and options, for example via
``functools.partial``.


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
