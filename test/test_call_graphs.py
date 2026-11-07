"""Resolved call graph neighborhoods and their documentation output."""
import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import flint
from flint.docgen.graphs import call_graph, write_dot
from flint.docgen.model import iter_module_documentation
from flint.docgen.references import Reference, ReferenceIndex, anchor
from flint.tools.gendoc import generate_docs


SOURCE = '''module library
private :: hidden
interface dispatch
module procedure work
end interface
contains
subroutine work()
call leaf()
end subroutine work
subroutine leaf()
call work()
end subroutine leaf
subroutine hidden()
end subroutine hidden
end module library
module client
use library, only: work, dispatch
contains
subroutine run()
call work()
call dispatch()
call unknown()
contains
subroutine inner()
call work()
end subroutine inner
end subroutine run
subroutine work_local()
end subroutine work_local
end module client
module unrelated
contains
subroutine work()
end subroutine work
end module unrelated
'''


class CallGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'example.F90'
        self.source.write_text(SOURCE)
        self.modules = tuple(iter_module_documentation(flint.parse(str(self.source))))
        self.references = ReferenceIndex(self.modules)

    def test_depth_cycles_and_generic_targets(self):
        graph = call_graph(self.references, 'client::run')
        self.assertEqual(graph.nodes,
                         ('client::run', 'library::interface::dispatch', 'library::work'))
        self.assertEqual(graph.edges, (
            ('client::run', 'library::interface::dispatch'),
            ('client::run', 'library::work')))
        deeper = call_graph(self.references, 'client::run', depth=2)
        self.assertIn(('library::work', 'library::leaf'), deeper.edges)
        self.assertNotIn(('library::leaf', 'library::work'), deeper.edges)
        cyclic = call_graph(self.references, 'client::run', depth=3)
        self.assertIn(('library::leaf', 'library::work'), cyclic.edges)
        self.assertEqual(cyclic, call_graph(self.references, 'client::run', depth=20))
        self.assertEqual(call_graph(self.references, 'client::run', depth=0).edges, ())
        with self.assertRaises(ValueError):
            call_graph(self.references, 'client::run', depth=-1)
        with self.assertRaises(ValueError):
            call_graph(self.references, 'client::run', direction='both')

    def test_callers_are_separate_and_private_paths_are_retained(self):
        graph = call_graph(self.references, 'library::work', direction='callers')
        self.assertIn(('client::run', 'library::work'), graph.edges)
        self.assertNotIn(('library::work', 'library::leaf'), graph.edges)
        callees = call_graph(self.references, 'library::work')
        self.assertEqual(callees.edges, (('library::work', 'library::leaf'),))
        self.assertNotIn('client::run', callees.nodes)
        self.assertEqual(call_graph(self.references, 'library::hidden').nodes,
                         ('library::hidden',))
        self.references.calls['client::run'] += (Reference('hidden', 'library::hidden'),)
        self.references.calls['library::hidden'] = (Reference('leaf', 'library::leaf'),)
        graph = call_graph(self.references, 'client::run', depth=2)
        self.assertIn(('library::hidden', 'library::leaf'), graph.edges)
        dot = io.StringIO()
        write_dot(dot, graph, self.references)
        self.assertIn('[private/internal]', dot.getvalue())

    def test_dot_is_deterministic_and_links_to_html_pages(self):
        graph = call_graph(self.references, 'client::run')
        first, second = io.StringIO(), io.StringIO()
        write_dot(first, graph, self.references, html_links=True)
        write_dot(second, graph, self.references, html_links=True)
        self.assertEqual(first.getvalue(), second.getvalue())
        self.assertIn('client.html#' + anchor('client::run'), first.getvalue())
        self.assertIn('library.html#' + anchor('library::work'), first.getvalue())
        self.assertIn('(interface)', first.getvalue())
        self.assertIn('subgraph "cluster_client"', first.getvalue())
        self.assertIn('subgraph "cluster_library"', first.getvalue())
        self.assertNotIn('subgraph "cluster_unrelated"', first.getvalue())
        self.assertIn('label="run"', first.getvalue())
        self.assertNotIn('unknown', first.getvalue())

    def test_dot_export_and_missing_renderer(self):
        output = self.root / 'docs'
        with contextlib.redirect_stderr(io.StringIO()):
            generate_docs([str(self.source)], output, call_graphs='dot')
        self.assertTrue(list(output.glob('*.dot')))
        self.assertFalse(list(output.glob('*.svg')))
        self.assertNotIn('.. image::', (output / 'client.rst').read_text())
        with patch('flint.tools.gendoc.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'require Graphviz'):
                generate_docs([str(self.source)], output, call_graphs='svg')

    @unittest.skipUnless(shutil.which('dot'), 'requires Graphviz dot')
    def test_private_graphs_have_unique_inline_ids_and_configurable_fontsize(self):
        self.source.write_text(SOURCE.replace('call leaf()', 'call leaf()\ncall hidden()'))
        output = self.root / 'private'
        with contextlib.redirect_stderr(io.StringIO()):
            result = generate_docs([self.source], output, call_graphs='svg',
                                   include_private=True, graph_fontsize=12, link_format='html')
        self.assertTrue((output / ('callers-' + anchor('library::hidden') + '.svg')).is_file())
        images = list(output.glob('*.svg'))
        self.assertEqual(result.summary['call_graphs'], len(images))
        ids = []
        for path in images:
            tree = ET.parse(path)
            ids.extend(node.get('id') for node in tree.iter() if 'id' in node.attrib)
            self.assertIn('font-size="12.00"', path.read_text())
        self.assertEqual(len(ids), len(set(ids)))
        # Disabling diagrams does not require a Graphviz installation.
        with patch('flint.tools.gendoc.shutil.which', return_value=None), \
                contextlib.redirect_stderr(io.StringIO()):
            result = generate_docs([self.source], self.root / 'no-graphs',
                                   call_graphs='svg', graph_depth=0)
        self.assertEqual(result.summary['call_graphs'], 0)

    @unittest.skipUnless(shutil.which('dot'), 'requires Graphviz dot')
    def test_svg_generation_and_rst_embedding(self):
        output = self.root / 'docs'
        with contextlib.redirect_stderr(io.StringIO()):
            generate_docs([str(self.source)], output, call_graphs='svg', link_format='html')
        name = 'callees-' + anchor('client::run') + '.svg'
        image = ET.parse(output / name)
        links = [node.attrib['{http://www.w3.org/1999/xlink}href']
                 for node in image.iter()
                 if '{http://www.w3.org/1999/xlink}href' in node.attrib]
        self.assertIn('library.html#' + anchor('library::work'), links)
        rst = (output / 'client.rst').read_text()
        self.assertIn('.. image:: ' + name, rst)
        self.assertIn('.. rubric:: Callees', rst)
        self.assertNotIn('.. rubric:: Callers', rst)
        library_rst = (output / 'library.rst').read_text()
        self.assertIn('.. rubric:: Callers', library_rst)
        self.assertIn('callers-' + anchor('library::work') + '.svg', library_rst)
        try:
            from docutils.core import publish_doctree
        except ImportError:
            return
        warnings = io.StringIO()
        publish_doctree(rst, settings_overrides={'warning_stream': warnings, 'halt_level': 2})
        self.assertEqual(warnings.getvalue(), '')
