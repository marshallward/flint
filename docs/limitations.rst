===============================
Supported scope and limitations
===============================

Flint is a structural source-analysis framework under active development.
It does not validate all Fortran syntax or replace compiler diagnostics.
Its APIs may change as the source model develops.

Source analysis
===============

Directory discovery selects ``.f90`` and ``.F90`` files. The parser models
program units, declarations, interfaces, and supported executable constructs,
while retaining source spelling, whitespace, and comments.

Expression handling supports particular analysis tasks rather than a complete
Fortran expression AST and type system. Generic-interface inventories do not
select overloads from operand types. Type-bound bindings are represented
structurally; inherited bindings, override compatibility, and dynamic-dispatch
call edges are not resolved.

Documentation references resolve supported local, host, and imported names.
Unknown or ambiguous targets are diagnosed rather than linked to guessed
definitions. Call graphs therefore describe the calls Flint can resolve, not
necessarily every runtime call.

Preprocessing
=============

Object-like and named-argument function-like macros are supported, including
nested expansion. Conditional directives support a limited expression
evaluator, including tested numeric comparisons, logical operations, and
``defined`` expressions.

This is not a complete C preprocessor. Variadic macros, stringification, token
pasting, and function-like macro expansion within ``#if`` expressions are
unsupported. Analysis follows the selected conditional branches.

Formatting
==========

Spacing rules can propose and apply edits. Indentation and real-addition
grouping rules are diagnostic-only. Indentation checks do not support legacy
label-terminated DO loops.

The addition rule uses available local type evidence and skips unresolved
expressions. It does not infer an expression's type from its assignment target.
See the `guide <guide.rst#commands>`_ for its supported cases.

Documentation generation
========================

Flint writes reStructuredText and optional DOT/SVG graphs. Website rendering,
navigation, and staging referenced images belong to the caller. SVG graph
rendering requires Graphviz.

The Doxygen frontend translates a supported subset, not all Doxygen syntax.
Unsupported commands and unclosed math/code delimiters fail conversion.
Site-wide reference and citation roles require a resolver such as Sphinx.

Documentation checks assess the presence of explicit descriptions under a
defined policy; they do not assess prose quality or function-result
descriptions. See the
`documentation check policy <guide.rst#documentation-presence-checks>`_.

Back to the `documentation index <index.rst>`_.
