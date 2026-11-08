"""Reference extraction and rendering can be used independently."""
from dataclasses import asdict, replace
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import flint
from flint.docgen.model import UnitDocumentation, VariableDocumentation, iter_module_documentation
from flint.docgen.rst import write_module
from flint.docgen.references import ReferenceIndex, HtmlDestinations
from flint.tools.gendoc import discover_sources, generate_docs


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
    def test_definition_case_and_compact_signatures_keep_stable_links(self):
        text = '''module Ocean_API
contains
SUBROUTINE Advance(State, dt)
real, intent(inout) :: State !< State value.
real, intent(in) :: dt
end subroutine Advance
end module Ocean_API
module Client
use Ocean_API, only: advance
contains
subroutine Run()
call aDvAnCe(1., 2.)
end subroutine Run
end module Client
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mixed.F90'
            path.write_text(text)
            modules = tuple(iter_module_documentation(flint.parse(str(path))))
        ocean = next(module for module in modules if module.name == 'ocean_api')
        client = next(module for module in modules if module.name == 'client')
        self.assertEqual(ocean.name, 'ocean_api')
        self.assertEqual(ocean.display_name, 'Ocean_API')
        self.assertEqual(ocean.procedures[0].signature, 'SUBROUTINE Advance(State, dt)')
        self.assertEqual(ocean.procedures[0].variables[0].display_name, 'State')
        index = ReferenceIndex(modules)
        output = io.StringIO()
        write_module(output, client, references=index, destinations=HtmlDestinations(index))
        self.assertIn('Client module reference', output.getvalue())
        self.assertIn('`Advance <ocean_api.html#flint-ocean-0api-1advance>`__', output.getvalue())
        self.assertNotIn('aDvAnCe', output.getvalue())
        output = io.StringIO()
        write_module(output, ocean, references=index)
        self.assertIn('**State**', output.getvalue())
        self.assertIn('.. container:: api-procedure', output.getvalue())

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
        self.assertEqual(procedure.signature, 'subroutine update(x)')
        self.assertEqual(procedure.variables[0],
                         VariableDocumentation('x', 'inout', 'Value [m]', display_name='x'))
        self.assertEqual(procedure.variables[1].name, 'temporary')
        self.assertEqual(external.name, 'External')
        self.assertEqual(external.procedures[0].name, 'external_routine')
        before = json.dumps(asdict(module))
        project.modules[0].doc.header = 'Changed'
        project.modules[0].subprograms[0].variables[0].doc.docstring = 'Changed'
        project.modules[0].subprograms.clear()
        self.assertEqual(json.dumps(asdict(module)), before)


class RstWriterTests(unittest.TestCase):
    def test_optional_index_uses_display_names_and_selected_link_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'modules.f90'
            source.write_text('module Zebra\nend module Zebra\n'
                              'module Alpha\nend module Alpha\n')
            for link_format, suffix in ((None, 'rst'), ('html', 'html')):
                with self.subTest(link_format=link_format):
                    output = root / suffix
                    result = generate_docs([source], output, index_file='api-index.rst',
                                           index_title='Example API', link_format=link_format)
                    index = (output / 'api-index.rst').read_text()
                    self.assertTrue(index.startswith('Example API\n===========\n'))
                    self.assertIn(f'`Alpha <alpha.{suffix}>`__', index)
                    self.assertIn(f'`Zebra <zebra.{suffix}>`__', index)
                    self.assertLess(index.index('`Alpha'), index.index('`Zebra'))
                    self.assertEqual(result.summary['module_pages'], 2)
                    self.assertEqual(set(result.pages), {'alpha', 'zebra'})

    def test_index_rejects_module_collisions_and_directory_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'demo.f90'
            source.write_text('module demo\nend module demo\n')
            output = root / 'output'
            output.mkdir()
            page = output / 'demo.rst'
            page.write_text('Existing module page\n')
            for name in ('demo.rst', 'DEMO.rst'):
                with self.assertRaisesRegex(ValueError, 'conflicts with a module'):
                    generate_docs([source], output, index_file=name)
            for name in ('../index.rst', 'index.html'):
                with self.assertRaisesRegex(ValueError, 'Index filename'):
                    generate_docs([source], output, index_file=name)
            self.assertEqual(page.read_text(), 'Existing module page\n')

    def test_missing_symlink_targets_canonicalize_existing_ancestors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'src'
            source.mkdir()
            dependency = root / 'dependency'
            dependency.mkdir()
            alias = root / 'short-name'
            alias.symlink_to(root, target_is_directory=True)
            (source / 'demo.f90').write_text('module demo\nend module demo\n')
            missing = source / 'missing.f90'
            target = alias / 'dependency/absent/file.f90'
            missing.symlink_to(target)
            original_resolve = Path.resolve

            def windows_resolve(path, *args, **kwargs):
                # Simulate a short-name prefix surviving resolution of a
                # broken symlink. Existing ancestors still resolve normally.
                if path == missing:
                    return target
                return original_resolve(path, *args, **kwargs)

            with patch.object(Path, 'resolve', windows_resolve):
                files, includes, excluded = discover_sources([source], {'library': dependency})
            self.assertEqual(files, [source / 'demo.f90'])
            self.assertEqual(excluded, [
                ('library', missing, dependency.resolve() / 'absent/file.f90')])

    def test_sources_exclude_symlink_targets_and_keep_header_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'src'
            source.mkdir()
            headers = source / 'headers'
            headers.mkdir()
            (headers / 'values.h').write_text('#define STEP_NAME advance\n')
            dependency = root / 'dependency'
            dependency.mkdir()
            (dependency / 'bad.f90').write_text('not Fortran\n')
            (source / 'alias.f90').symlink_to(dependency / 'bad.f90')
            (source / 'missing.f90').symlink_to(dependency / 'absent.f90')
            (source / 'demo.f90').write_text(
                '#include "values.h"\nmodule demo\ncontains\nsubroutine STEP_NAME(value)\n'
                'integer, intent(in) :: value !< Input value.\n'
                'end subroutine STEP_NAME\nend module demo\n')
            output = root / 'docs'
            reports = root / 'reports'
            result = generate_docs([source, headers, dependency], output,
                                   excludes={'dependency': dependency}, reports=reports)
            self.assertEqual(result.pages, {'demo': 'demo'})
            self.assertEqual(result.summary['source_files'], 1)
            self.assertEqual(result.summary['excluded_dependency_files'], {'dependency': 3})
            self.assertIn('subroutine advance(value)', (output / 'demo.rst').read_text())
            self.assertIn('alias.f90', (reports / 'excluded-dependencies.txt').read_text())
            # Exclusion works without a dependency checkout, including broken aliases.
            (dependency / 'bad.f90').unlink()
            dependency.rmdir()
            result = generate_docs([source], root / 'absent', excludes=[dependency])
            self.assertEqual(result.summary['source_files'], 1)
            with self.assertRaisesRegex(FileNotFoundError, 'missing target'):
                generate_docs([source], root / 'broken')

    def test_generation_rejects_missing_empty_duplicate_and_unparsed_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'src'
            source.mkdir()
            with self.assertRaisesRegex(FileNotFoundError, 'does not exist'):
                generate_docs([root / 'missing'], root / 'output')
            with self.assertRaisesRegex(ValueError, 'No Fortran'):
                generate_docs([source], root / 'output')
            first = source / 'first.f90'
            first.write_text('module demo\nend module demo\n')
            with patch('flint.tools.gendoc.flint.parse') as parse:
                parse.return_value.sources = []
                with self.assertRaisesRegex(ValueError, 'Unable to parse .*first.f90'):
                    generate_docs([source], root / 'output')
            (source / 'second.f90').write_text('module demo\nend module demo\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate module demo: .*first.f90.*second.f90'):
                generate_docs([source], root / 'output')

    def test_missing_include_rejects_generation_and_retains_parse_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'demo.f90'
            source.write_text('module demo\n#include "absent.h"\nend module demo\n')
            for reports in (None, root / 'reports'):
                with self.subTest(reports=reports):
                    output = root / 'docs'
                    with self.assertRaisesRegex(ValueError, 'Incomplete parse of .*demo.f90') as error:
                        generate_docs([source], output, reports=reports, index_file='index.rst')
                    self.assertIn('absent.h', str(error.exception))
                    self.assertFalse(output.exists())
                    if reports is not None:
                        self.assertIn('absent.h', (reports / 'parse.log').read_text())

    def test_external_procedures_merge_across_files_and_reports_match_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / 'first.f90'
            first.write_text('subroutine first()\ncall second()\nend subroutine first\n')
            second = root / 'second.f90'
            second.write_text('subroutine second()\nend subroutine second\n')
            result = generate_docs([first, second], root / 'docs', reports=root / 'reports')
            self.assertEqual(result.pages, {'External': 'External'})
            self.assertEqual(result.summary['source_files'], 2)
            self.assertEqual(result.summary['unresolved_references'], 0)
            rst = (root / 'docs/External.rst').read_text()
            self.assertIn('subroutine first()', rst)
            self.assertIn('subroutine second()', rst)
            self.assertEqual((root / 'reports/unresolved.txt').read_text(), '')

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

.. container:: api-procedure

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
