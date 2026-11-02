"""flint gendoc command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from pathlib import Path
import sys

import flint
from flint.docgen.model import build_unit_documentation, iter_module_documentation
from flint.docgen.rst import write_module, write_unit
from flint.docgen.references import ReferenceIndex, HtmlDestinations


def generate_docs(srcdirs, docdir, includes=None, excludes=None, link_format=None):
    if link_format not in (None, 'html'):
        raise ValueError(f'Unsupported link format: {link_format}')
    project = flint.parse(*srcdirs, includes=includes, excludes=excludes)
    modules = tuple(iter_module_documentation(project))
    references = ReferenceIndex(modules)
    destinations = HtmlDestinations(references) if link_format == 'html' else None
    output = Path(docdir)
    output.mkdir(parents=True, exist_ok=True)
    for module in modules:
        with (output / (module.name + '.rst')).open('w', encoding='utf-8') as doc:
            write_module(doc, module, references=references, destinations=destinations)
    for diagnostic in references.diagnostics:
        print('gendoc: ' + diagnostic, file=sys.stderr)


def print_unit(doc, unit, depth, graph=None):
    """Compatibility adapter for callers of the original parser-based helper."""
    reference = build_unit_documentation(unit, graph=graph)
    write_unit(doc, reference, depth, show_callers=graph is not None)
