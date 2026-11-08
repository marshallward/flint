"""flint gendoc command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from collections.abc import Mapping
import contextlib
from dataclasses import dataclass, replace
import io
from pathlib import Path
import sys
import shutil
import subprocess
import xml.etree.ElementTree as ET

import flint
from flint.docgen.model import build_unit_documentation, iter_module_documentation
from flint.docgen.rst import write_module, write_unit
from flint.docgen.references import ReferenceIndex, HtmlDestinations
from flint.docgen.references import anchor
from flint.docgen.graphs import call_graph, write_dot


@dataclass(frozen=True)
class GenerationResult:
    """Generated page titles and statistics, independent of parser objects."""
    pages: dict
    summary: dict


def _resolved_path(path):
    """Canonicalize existing ancestors even when the final target is missing.

    On Windows, resolving a missing target can retain 8.3 path components,
    while resolving an existing exclusion root expands them to long names.
    """
    path = path.resolve()
    missing = []
    while not path.exists() and path != path.parent:
        missing.append(path.name)
        path = path.parent
    return path.resolve().joinpath(*reversed(missing))


def discover_sources(srcdirs, excludes):
    """Find sources and include directories, respecting resolved exclusions.

    Exclusions may be paths or a mapping from diagnostic labels to paths.
    Excluded symlinks need not have existing targets.
    """
    roots = (excludes.items() if isinstance(excludes, Mapping)
             else ((str(path), path) for path in excludes))
    roots = [(label, Path(path).absolute(), _resolved_path(Path(path))) for label, path in roots]

    def excluded(path):
        return next((label for label, lexical, resolved in roots
                     if path.absolute().is_relative_to(lexical)
                     or _resolved_path(path).is_relative_to(resolved)), None)

    paths = set()
    for item in srcdirs:
        path = Path(item)
        if excluded(path) is None and not path.exists():
            raise FileNotFoundError(f'Source path does not exist: {path}')
        paths.update(path.rglob('*') if path.is_dir() else [path])
    selected, omitted = [], []
    for path in sorted(paths):
        label = excluded(path)
        if label is not None:
            if path.suffix in ('.F90', '.f90'):
                omitted.append((label, path, _resolved_path(path)))
        else:
            if path.is_symlink() and not path.exists():
                raise FileNotFoundError(f'Source symlink has a missing target: {path} -> {path.resolve()}')
            selected.append(path)
    files = [path for path in selected if path.is_file() and path.suffix in ('.F90', '.f90')]
    if not files:
        raise ValueError('No Fortran source files selected')
    includes = sorted({str(path.parent) for path in selected if path.is_file()})
    return files, includes, omitted


def generate_graphs(references, output, *, format, depth, html_links,
                    include_private, fontsize, dot):
    """Write DOT/SVG diagrams whose IDs are safe for inline HTML embedding."""
    images = {}
    count = 0
    if format is None or depth == 0:
        return images, count
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    for key, unit in sorted(references.units.items()):
        if unit.kind not in ('function', 'subroutine', 'interface'):
            continue
        if not include_private and not references.is_public(key):
            continue
        for direction in ('callees', 'callers'):
            graph = call_graph(references, key, depth=depth, direction=direction)
            if not graph.edges:
                continue
            count += 1
            path = output / (direction + '-' + anchor(key) + '.dot')
            with path.open('w', encoding='utf-8') as stream:
                write_dot(stream, graph, references, html_links=html_links)
            if format == 'svg':
                image = path.with_suffix('.svg')
                options = ([f'-{scope}fontsize={fontsize}' for scope in ('N', 'G', 'E')]
                           if fontsize is not None else [])
                subprocess.run([dot, '-Tsvg', *options, str(path), '-o', str(image)], check=True)
                tree = ET.parse(image)
                for node in tree.iter():
                    if 'id' in node.attrib:
                        node.set('id', path.stem + '-' + node.get('id'))
                    for attr in ('href', '{http://www.w3.org/1999/xlink}href'):
                        value = node.get(attr, '')
                        if value.startswith('#'):
                            node.set(attr, '#' + path.stem + '-' + value[1:])
                tree.write(image, encoding='utf-8', xml_declaration=True)
                images.setdefault(key, []).append((direction.title(), image.name))
    return images, count


def generate_docs(srcdirs, docdir, includes=None, excludes=None, link_format=None,
                  call_graphs=None, graph_depth=1, markup='plain', *,
                  include_private=False, graph_fontsize=None, reports=None,
                  index_file=None, index_title='API reference'):
    """Generate linked reST and optional graphs, returning page titles and counts.

    Only documentation snapshots are retained between files. ``reports`` enables
    parser, exclusion, external-reference, and unresolved-reference logs.
    ``excludes`` accepts either paths or a mapping of library labels to paths.
    ``index_file`` optionally names a reST index alongside the module pages.
    """
    if markup not in ('plain', 'rst', 'doxygen'):
        raise ValueError(f'Unsupported documentation markup: {markup}')
    if link_format not in (None, 'html'):
        raise ValueError(f'Unsupported link format: {link_format}')
    if call_graphs not in (None, 'dot', 'svg'):
        raise ValueError(f'Unsupported graph format: {call_graphs}')
    if graph_depth < 0:
        raise ValueError('Graph depth must be nonnegative')
    if index_file is not None:
        index_file = Path(index_file)
        if index_file.name != str(index_file) or index_file.suffix != '.rst':
            raise ValueError('Index filename must be a .rst filename without directories')
    dot = shutil.which('dot') if call_graphs == 'svg' and graph_depth else None
    if call_graphs == 'svg' and graph_depth and dot is None:
        raise ValueError('SVG call graphs require Graphviz dot; install Graphviz or use --call-graphs dot')
    if graph_fontsize is not None and graph_fontsize <= 0:
        raise ValueError('Graph font size must be positive')
    files, include_dirs, excluded = discover_sources(srcdirs, excludes or ())
    include_dirs = list(dict.fromkeys([*(includes or ()), *include_dirs]))
    reports = Path(reports) if reports is not None else None
    if reports is not None:
        reports.mkdir(parents=True, exist_ok=True)
    modules, externals = [], []
    owners = {}
    external = None
    with contextlib.ExitStack() as stack:
        if reports is not None:
            log = stack.enter_context((reports / 'parse.log').open('w', encoding='utf-8'))
            stack.enter_context(contextlib.redirect_stdout(log))
            stack.enter_context(contextlib.redirect_stderr(log))
        for path in files:
            diagnostics = io.StringIO()
            try:
                with contextlib.redirect_stderr(diagnostics):
                    project = flint.parse(str(path), includes=include_dirs)
            finally:
                if reports is not None:
                    log.write(diagnostics.getvalue())
            if diagnostics.getvalue():
                raise ValueError(f'Incomplete parse of {path}:\n{diagnostics.getvalue().rstrip()}')
            if len(project.sources) != 1:
                raise ValueError(f'Unable to parse {path}')
            for module in iter_module_documentation(project):
                if module.name == 'External' and not module.kind:
                    external = module
                    externals.extend(module.procedures)
                else:
                    name = module.name.lower()
                    if name in owners:
                        raise ValueError(f'Duplicate module {module.name}: {owners[name]} and {path}')
                    owners[name] = path
                    modules.append(module)
            del project
    if externals:
        modules.append(replace(external, procedures=tuple(externals)))
    pages = {module.name: module.display_name or module.name for module in modules}
    if index_file is not None and index_file.stem.casefold() in {name.casefold() for name in pages}:
        raise ValueError(f'Index filename conflicts with a module page: {index_file}')
    references = ReferenceIndex(modules)
    destinations = HtmlDestinations(references) if link_format == 'html' else None
    output = Path(docdir)
    output.mkdir(parents=True, exist_ok=True)
    graph_images, graph_count = generate_graphs(
        references, output, format=call_graphs, depth=graph_depth,
        html_links=link_format == 'html', include_private=include_private,
        fontsize=graph_fontsize, dot=dot)
    for module in modules:
        with (output / (module.name + '.rst')).open('w', encoding='utf-8') as doc:
            try:
                write_module(doc, module, references=references, destinations=destinations,
                             graph_images=graph_images, markup=markup)
            except ValueError as error:
                raise ValueError(f'{owners.get(module.name.lower(), module.name)}: {error}') from error
    if index_file is not None:
        suffix = 'html' if link_format == 'html' else 'rst'
        with (output / index_file).open('w', encoding='utf-8') as stream:
            stream.write(index_title + '\n' + '=' * len(index_title) + '\n\nModules\n-------\n\n')
            for name, title in sorted(pages.items(), key=lambda entry: entry[0].lower()):
                stream.write(f'* `{title} <{name}.{suffix}>`__\n')
    excluded_counts = {}
    for label, path, target in excluded:
        excluded_counts[label] = excluded_counts.get(label, 0) + 1
    external_calls = [(scope, ref) for scope, calls in references.calls.items()
                      for ref in calls if ref.external is not None]
    if reports is not None:
        (reports / 'excluded-dependencies.txt').write_text(
            ''.join(f'{label}: {path} -> {target}\n' for label, path, target in excluded), encoding='utf-8')
        (reports / 'unresolved.txt').write_text(
            ''.join(message + '\n' for message in references.diagnostics), encoding='utf-8')
        (reports / 'external.txt').write_text(
            ''.join(f'{scope}: {ref.label}: {ref.external.library}: '
                    f'{ref.external.module}::{ref.external.name}\n' for scope, ref in external_calls),
            encoding='utf-8')
    for diagnostic in references.diagnostics:
        print('gendoc: ' + diagnostic, file=sys.stderr)
    return GenerationResult(
        pages=pages,
        summary={'source_files': len(files), 'module_pages': len(modules),
                 'call_graphs': graph_count,
                 'excluded_dependency_files': excluded_counts,
                 'call_references': sum(len(calls) for calls in references.calls.values()),
                 'external_references': len(external_calls),
                 'external_libraries': {},
                 'unresolved_references': len(references.diagnostics)})


def print_unit(doc, unit, depth, graph=None):
    """Compatibility adapter for callers of the original parser-based helper."""
    reference = build_unit_documentation(unit, graph=graph)
    write_unit(doc, reference, depth, show_callers=graph is not None)
