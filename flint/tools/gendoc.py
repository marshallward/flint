"""flint gendoc command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from pathlib import Path
import sys
import shutil
import subprocess

import flint
from flint.docgen.model import build_unit_documentation, iter_module_documentation
from flint.docgen.rst import write_module, write_unit
from flint.docgen.references import ReferenceIndex, HtmlDestinations
from flint.docgen.references import anchor
from flint.docgen.graphs import call_graph, write_dot


def generate_docs(srcdirs, docdir, includes=None, excludes=None, link_format=None,
                  call_graphs=None, graph_depth=1, markup='plain'):
    if markup not in ('plain', 'rst', 'doxygen'):
        raise ValueError(f'Unsupported documentation markup: {markup}')
    if link_format not in (None, 'html'):
        raise ValueError(f'Unsupported link format: {link_format}')
    if call_graphs not in (None, 'dot', 'svg'):
        raise ValueError(f'Unsupported graph format: {call_graphs}')
    if graph_depth < 0:
        raise ValueError('Graph depth must be nonnegative')
    dot = shutil.which('dot') if call_graphs == 'svg' else None
    if call_graphs == 'svg' and dot is None:
        raise ValueError('SVG call graphs require Graphviz dot; install Graphviz or use --call-graphs dot')
    project = flint.parse(*srcdirs, includes=includes, excludes=excludes)
    modules = tuple(iter_module_documentation(project))
    references = ReferenceIndex(modules)
    destinations = HtmlDestinations(references) if link_format == 'html' else None
    output = Path(docdir)
    output.mkdir(parents=True, exist_ok=True)
    graph_images = {}
    if call_graphs is not None:
        for key, unit in sorted(references.units.items()):
            if unit.kind not in ('function', 'subroutine', 'interface') or not references.is_public(key):
                continue
            for direction in ('callees', 'callers'):
                graph = call_graph(references, key, depth=graph_depth, direction=direction)
                if not graph.edges:
                    continue
                path = output / (direction + '-' + anchor(key) + '.dot')
                with path.open('w', encoding='utf-8') as stream:
                    write_dot(stream, graph, references, html_links=link_format == 'html')
                if call_graphs == 'svg':
                    image = path.with_suffix('.svg')
                    subprocess.run([dot, '-Tsvg', str(path), '-o', str(image)], check=True)
                    graph_images.setdefault(key, []).append((direction.title(), image.name))
    for module in modules:
        with (output / (module.name + '.rst')).open('w', encoding='utf-8') as doc:
            write_module(doc, module, references=references, destinations=destinations,
                         graph_images=graph_images, markup=markup)
    for diagnostic in references.diagnostics:
        print('gendoc: ' + diagnostic, file=sys.stderr)


def print_unit(doc, unit, depth, graph=None):
    """Compatibility adapter for callers of the original parser-based helper."""
    reference = build_unit_documentation(unit, graph=graph)
    write_unit(doc, reference, depth, show_callers=graph is not None)
