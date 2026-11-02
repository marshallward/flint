"""flint gendoc command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from pathlib import Path

import flint
from flint.docgen.model import build_unit_documentation, iter_module_documentation
from flint.docgen.rst import write_module, write_unit


def generate_docs(srcdirs, docdir, includes=None, excludes=None):
    project = flint.parse(*srcdirs, includes=includes, excludes=excludes)
    output = Path(docdir)
    output.mkdir(parents=True, exist_ok=True)
    for module in iter_module_documentation(project):
        with (output / (module.name + '.rst')).open('w', encoding='utf-8') as doc:
            write_module(doc, module)


def print_unit(doc, unit, depth, graph=None):
    """Compatibility adapter for callers of the original parser-based helper."""
    reference = build_unit_documentation(unit, graph=graph)
    write_unit(doc, reference, depth, show_callers=graph is not None)
