"""Reference extraction and rendering can be used independently."""
from dataclasses import asdict, replace
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

import flint
from flint.docgen.model import UnitDocumentation, VariableDocumentation, iter_module_documentation
from flint.docgen.rst import write_module
from flint.tools.gendoc import generate_docs


SOURCE = '''!> Example module.
module demo
  type :: item
    real :: value !< Length [m]
  end type item
contains
  !> Update a value.
  subroutine update(x)
    real, intent(inout) :: x !< Value [m]
    real :: temporary
  contains
    subroutine helper()
    end subroutine helper
  end subroutine update
end module demo
subroutine external_routine()
end subroutine external_routine
'''


class DocumentationModelTests(unittest.TestCase):
    def test_unit_summary_keeps_paragraphs_before_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text('!> First paragraph.\n!!\n!!   Second paragraph\n'
                            '!! with incidental indentation.\nmodule demo\nend module demo\n')
            module = next(iter_module_documentation(flint.parse(str(path))))
        self.assertEqual(module.summary,
                         'First paragraph.\n\n  Second paragraph\nwith incidental indentation.')

    def test_snapshot_is_detached_and_preserves_nested_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(SOURCE)
            project = flint.parse(str(path))
        module, external = tuple(iter_module_documentation(project))
        self.assertEqual(module.name, 'demo')
        self.assertEqual(module.summary, 'Example module.')
        self.assertEqual(module.derived_types[0].qualified_name, 'demo::item')
        procedure = module.procedures[0]
        self.assertEqual(procedure.procedures[0].qualified_name, 'demo::update::helper')
        self.assertEqual(procedure.signature, 'subroutine update ( x )')
        self.assertEqual(procedure.variables[0], VariableDocumentation('x', 'inout', 'Value [m]'))
        self.assertEqual(procedure.variables[1].name, 'temporary')
        self.assertEqual(external.name, 'External')
        self.assertEqual(external.procedures[0].name, 'external_routine')
        before = json.dumps(asdict(module))
        project.modules[0].doc.header = 'Changed'
        project.modules[0].subprograms[0].variables[0].doc.docstring = 'Changed'
        project.modules[0].subprograms.clear()
        self.assertEqual(json.dumps(asdict(module)), before)


class RstWriterTests(unittest.TestCase):
    def test_writer_uses_records_without_parser_objects(self):
        procedure = UnitDocumentation(
            name='update', qualified_name='demo::update', kind='subroutine',
            signature='subroutine update ( x )', summary='Update a value.', description='',
            variables=(VariableDocumentation('x', 'inout', 'Value [m]'),),
        )
        module = UnitDocumentation(
            name='demo', qualified_name='demo', kind='module',
            signature='module demo', summary='Example module.', description='',
            procedures=(procedure,),
        )
        output = io.StringIO()
        write_module(output, module)
        self.assertEqual(output.getvalue(), r'''=====================
demo module reference
=====================
Example module.

Functions/Subroutines
=====================
.. list-table::

   * - `update <flint-demo-1update_>`__
     - Update a value.


Functions/Subroutine Documentation
==================================

.. _flint-demo-1update:

subroutine update ( x )
  Update a value.

  Parameters
    - **x** :: [inout] Value \[m\]

''')

    def test_command_writes_module_and_external_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(SOURCE)
            output = Path(tmp) / 'reference'
            generate_docs([str(path)], output)
            self.assertEqual({p.name for p in output.iterdir()}, {'demo.rst', 'External.rst'})
            self.assertIn(r'Length \[m\]', (output / 'demo.rst').read_text())
            self.assertIn('external_routine', (output / 'External.rst').read_text())

    @unittest.skipUnless(importlib.util.find_spec('docutils'), 'requires optional docutils renderer')
    def test_plain_prose_renders_without_markup_or_indentation_errors(self):
        from docutils import nodes
        from docutils.core import publish_doctree

        text = r'''  By the authors.

    The functions perform useful manipulations of
  character strings. Use *literal* text, name_, |symbols| and [units].

.. warning:: This is prose, not a directive.

1. This is prose, not a numbered list.

\namespace demo

Example::'''
        procedure = UnitDocumentation(
            name='update', qualified_name='demo::update', kind='subroutine',
            signature='subroutine update ( x )', summary=text, description='',
            variables=(VariableDocumentation('x', 'inout', text),),
        )
        module = replace(procedure, name='demo', qualified_name='demo', kind='module',
                         signature='module demo', description=text, variables=(),
                         procedures=(procedure,))
        output = io.StringIO()
        write_module(output, module)
        warnings = io.StringIO()
        tree = publish_doctree(output.getvalue(), settings_overrides={
            'warning_stream': warnings, 'halt_level': 2,
        })
        self.assertEqual(warnings.getvalue(), '')
        self.assertFalse(list(tree.findall(nodes.warning)))
        self.assertFalse(list(tree.findall(nodes.emphasis)))
        self.assertFalse(list(tree.findall(nodes.enumerated_list)))
        paragraphs = [node.astext() for node in tree.findall(nodes.paragraph)]
        self.assertIn('By the authors.', paragraphs)
        self.assertIn('The functions perform useful manipulations of character strings. '
                      'Use *literal* text, name_, |symbols| and [units].', paragraphs)
        self.assertIn(r'\namespace demo', paragraphs)
