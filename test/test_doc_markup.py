"""Comment frontends preserve scientific structure without requiring Doxygen."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.docgen.markup import documentation
from flint.docgen.model import iter_module_documentation
from flint.docgen.rst import write_module


class MarkupTests(unittest.TestCase):
    def test_formats_are_explicit(self):
        source = '.. math::\n\n   x^2\n'
        self.assertEqual(documentation(source, 'rst'), source.rstrip())
        self.assertNotIn('\n   x^2', documentation(source, 'plain'))
        with self.assertRaisesRegex(ValueError, 'Unsupported documentation markup'):
            documentation(source, 'automatic')

    def test_inline_math_citations_and_labeled_references(self):
        output = documentation(r'The [harmonic mean](@ref harmonic) has \f$ |x| \f$ '
                               r'and follows \cite Paper2001. See \ref harmonic.', 'doxygen')
        self.assertIn(':ref:`harmonic mean <harmonic>`', output)
        self.assertIn(':math:`|x|`', output)
        self.assertIn(':cite:`Paper2001`.', output)
        self.assertIn(':ref:`harmonic`.', output)
        self.assertNotIn('FLINT', output)

    def test_literal_blocks_do_not_interpret_commands_or_tables(self):
        source = r'''\verbatim
  |-- root
  |   `-- child
  \not_a_command | unparsed |
\endverbatim'''
        output = documentation(source, 'doxygen')
        self.assertEqual(output, '.. code-block:: text\n\n'
                         '   |-- root\n   |   `-- child\n   \\not_a_command | unparsed |')

    def test_ascii_stencil_retains_alignment(self):
        source = 'Stencil:\n\n     i     i+1\n  ..--o------o--..\n    i-1/2  i+1/2'
        output = documentation(source, 'doxygen')
        self.assertIn('.. code-block:: text\n\n      i     i+1\n   ..--o------o--..', output)

    def test_math_environments_and_pipe_tables(self):
        source = r'''\f{eqnarray*}{
x & = & y \\
z & = & t
\f}

| Symbol | Parameter |
| --- | --- |
| \f$ |x| \f$ | <code>X_SCALE</code> |
'''
        output = documentation(source, 'doxygen')
        self.assertIn('.. math::\n\n   \\begin{aligned}', output)
        self.assertIn('x &= y \\\\', output)
        self.assertIn('.. list-table::\n   :header-rows: 1', output)
        self.assertIn('* - :math:`|x|`\n     - ``X_SCALE``', output)

    def test_unsupported_or_unclosed_commands_fail(self):
        for text in (r'\unknown argument', r'\f$ x', r'\verbatim unclosed'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'Unsupported Doxygen command'):
                documentation(text, 'doxygen')

    def test_escaped_mentions_and_emails_are_literal(self):
        output = documentation(r'By \@author-name (name@example.org).', 'doxygen')
        self.assertIn('@author-name', output)
        self.assertIn('name@example.org', output)

    @unittest.skipUnless(importlib.util.find_spec('docutils'), 'requires optional docutils renderer')
    def test_structured_comments_survive_extraction_and_rendering(self):
        from docutils import nodes
        from docutils.core import publish_doctree
        source = r'''!> Example.
module demo
type :: state
  logical :: enabled !< Enable diagnostics.
  !>@{ Diagnostic IDs
  integer :: first, second
  !>@}
end type state
contains
!> Advance the state.
!!
!! \f[
!!    x = y^2
!! \f]
!!
!! \verbatim
!!   left    right
!!   o-------o
!! \endverbatim

!> More details after the diagram.
subroutine advance(x)
real :: x !< Value with \f$ x^2 \f$ units.
end subroutine advance
!> \namespace demo
!! \section demo Details
!!
!! | Name | Meaning |
!! | --- | --- |
!! | <code>x</code> | value |
end module demo
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(source)
            module = next(iter_module_documentation(flint.parse(str(path))))
        self.assertEqual(module.derived_types[0].variables[1].description, 'Diagnostic IDs')
        output = io.StringIO()
        write_module(output, module, markup='doxygen')
        warnings = io.StringIO()
        tree = publish_doctree(output.getvalue(), settings_overrides={
            'halt_level': 2, 'warning_stream': warnings})
        self.assertEqual(warnings.getvalue(), '')
        self.assertEqual(len(list(tree.findall(nodes.math_block))), 1)
        self.assertEqual(len(list(tree.findall(nodes.literal_block))), 1)
        self.assertEqual(len(list(tree.findall(nodes.math))), 1)
        self.assertIn('More details after the diagram.', tree.astext())
        self.assertEqual(output.getvalue().count('.. _demo:'), 1)

    @unittest.skipUnless(importlib.util.find_spec('docutils'), 'requires optional docutils renderer')
    def test_native_rst_variable_comments_preserve_blocks(self):
        from docutils import nodes
        from docutils.core import publish_doctree
        source = '''module demo
contains
!> Advance a value.
subroutine advance(x)
real :: x !< Input value.
          !!
          !! .. math::
          !!
          !!    x^2
end subroutine advance
end module demo
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(source)
            module = next(iter_module_documentation(flint.parse(str(path))))
        output = io.StringIO()
        write_module(output, module, markup='rst')
        tree = publish_doctree(output.getvalue(), settings_overrides={'halt_level': 2})
        self.assertEqual(len(list(tree.findall(nodes.math_block))), 1)
