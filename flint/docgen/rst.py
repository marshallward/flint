"""reStructuredText presentation of documentation records.

This writer consumes only the documentation model; it does not inspect Fortran
tokens, traverse a parsed project, or resolve names in the parser's call graph.
"""
import io

from flint.docgen.references import Reference, ReferenceIndex, anchor
from flint.docgen.markup import documentation as _documentation, plain as _prose


def _indented(text, indent):
    return '\n'.join(indent + line if line else '' for line in text.split('\n'))


def _link(reference, references, current, destinations):
    label = reference.label
    if reference.target is not None:
        unit = references.units[reference.target]
        if label.lower() == unit.name.lower():
            label = unit.display_name or unit.name
        elif label.lower() == unit.qualified_name.lower():
            parts = []
            key = reference.target
            while key is not None:
                entry = references.units[key]
                parts.append(entry.display_name or entry.name)
                key = references.parents[key]
            label = '::'.join(reversed(parts))
    if reference.target is None:
        return '``' + label + '``'
    if destinations is not None:
        target = destinations.destination(reference.target, current)
    elif references.pages[reference.target] == references.pages[current]:
        target = anchor(reference.target) + '_'
    else:
        return '``' + label + '``'
    return f'`{_prose(label)} <{target}>`__'


def write_module(doc, module, *, references=None, destinations=None, graph_images=None,
                 markup='plain'):
    """Write a module reference to a text stream using the legacy layout."""
    if references is None:
        references = ReferenceIndex((module,))
    title = (module.display_name or module.name) + ' module reference'
    doc.write('=' * len(title) + '\n' + title + '\n' + '=' * len(title) + '\n')
    doc.write(_documentation(module.summary, markup) + '\n\n')
    implementations = tuple(entry for entry in module.procedures if not entry.declaration_only)
    declarations = tuple(entry for entry in module.procedures if entry.declaration_only)

    for title, entries in (('Data Types', module.derived_types),
                           ('Generic Interfaces', module.interfaces),
                           ('Procedure Interfaces', declarations),
                           ('Functions/Subroutines', implementations)):
        if entries:
            doc.write(title + '\n' + '=' * len(title) + '\n')
            doc.write('.. list-table::\n\n')
            for entry in entries:
                name = entry.display_name or entry.name
                # Detailed blocks (targets, equations, tables) belong only in
                # the definition, not a duplicate copy in the overview table.
                summary = _documentation(entry.summary, markup)
                if markup != 'plain':
                    summary = summary.split('\n\n', 1)[0]
                    if summary.lstrip().startswith('.. '):
                        summary = ''
                summary = summary.replace('\n', '\n       ')
                link = _link(Reference(name, entry.qualified_name), references,
                             module.qualified_name, destinations)
                doc.write(f'   * - {link}\n     - {summary}\n\n\n')

    if module.description:
        doc.write('Detailed Description\n====================\n')
        doc.write(_documentation(module.description, markup) + '\n\n')

    if module.derived_types:
        doc.write('Type Documentation\n==================\n')
        for entry in module.derived_types:
            write_unit(doc, entry, show_callers=False, references=references,
                       destinations=destinations, graph_images=graph_images, markup=markup)

    if module.interfaces:
        doc.write('Generic Interface Documentation\n===============================\n\n')
        for entry in module.interfaces:
            write_unit(doc, entry, references=references, destinations=destinations,
                       graph_images=graph_images, markup=markup)

    if declarations:
        doc.write('Procedure Interface Documentation\n=================================\n\n')
        for entry in declarations:
            write_unit(doc, entry, references=references, destinations=destinations,
                       graph_images=graph_images, markup=markup)

    if implementations:
        doc.write('Functions/Subroutine Documentation\n==================================\n\n')
        for entry in implementations:
            write_unit(doc, entry, references=references, destinations=destinations,
                       graph_images=graph_images, markup=markup)


def write_unit(doc, unit, depth=0, *, show_callers=True, references=None, destinations=None,
               graph_images=None, markup='plain'):
    """Group each callable entry in a portable reST presentation container."""
    if unit.kind in ('function', 'subroutine', 'interface'):
        content = io.StringIO()
        _write_unit(content, unit, show_callers=show_callers,
                    references=references, destinations=destinations, graph_images=graph_images, markup=markup)
        indent = depth * ' '
        doc.write(indent + '.. container:: api-procedure\n\n')
        doc.write(_indented(content.getvalue().rstrip(), indent + '   ') + '\n\n')
    else:
        _write_unit(doc, unit, depth, show_callers=show_callers,
                    references=references, destinations=destinations, graph_images=graph_images, markup=markup)


def _write_unit(doc, unit, depth=0, *, show_callers=True, references=None, destinations=None,
                graph_images=None, markup='plain'):
    """Write a unit record and its nested types and procedures."""
    indent = depth * ' '
    doc.write(indent + '.. _' + anchor(unit.qualified_name) + ':\n\n')
    doc.write(indent + unit.signature + '\n')
    doc.write(_indented(_documentation(unit.summary, markup), indent + '  ') + '\n')
    doc.write('\n')

    if any(variable.description for variable in unit.variables):
        doc.write(indent + '  Parameters\n')
    for variable in unit.variables:
        if variable.description:
            doc.write(indent + '    - **' + (variable.display_name or variable.name) + '**')
            if markup == 'plain':
                # Preserve the legacy plain-text layout.
                description = _prose(variable.description).replace('\n', '\n' + indent + '      ')
                doc.write(' :: ' + (f'[{variable.intent}] ' if variable.intent else '')
                          + description + '\n\n')
            else:
                if variable.intent:
                    doc.write(f' [{variable.intent}]')
                doc.write('\n\n' + _indented(_documentation(variable.description, markup),
                                            indent + '      ') + '\n\n')

    calls = (references.calls[unit.qualified_name] if references is not None else
             tuple(Reference(name, None) for name in unit.callees))
    callers = references.callers.get(unit.qualified_name, ()) if references is not None else ()
    implementations = (references.implementations[unit.qualified_name] if references is not None else
                       tuple(Reference(name, None) for name in unit.implementations))
    if references is not None:
        calls = tuple(ref for ref in calls
                      if ref.target is not None and references.is_public(ref.target))
        implementations = tuple(ref for ref in implementations
                                if ref.target is not None and references.is_public(ref.target))
    specifics_title = ('Specific Procedures' if references is not None and any(
        references.units[ref.target].declaration_only for ref in implementations
        if ref.target is not None) else 'Implementations')
    for title, links in ((specifics_title, implementations), ('Calls into', calls),
                         ('Called by', callers if show_callers else ())):
        if links:
            doc.write('\n' + indent + title + '\n')
            for ref in links:
                doc.write(indent + '  ' +
                          _link(ref, references, unit.qualified_name, destinations) + '\n')
            doc.write('\n')

    for title, image in (graph_images or {}).get(unit.qualified_name, ()):
        doc.write('\n' + indent + '.. rubric:: ' + title + '\n')
        doc.write('\n' + indent + '.. image:: ' + image + '\n')
        doc.write(indent + '   :alt: ' + title + ' of ' + unit.qualified_name + '\n\n')

    external_calls = {}
    if references is not None:
        for ref in references.calls[unit.qualified_name]:
            if ref.external is not None:
                group = ref.external.library or ref.external.module
                external_calls.setdefault(group, []).append(ref)
    if external_calls:
        doc.write('\n' + indent + '.. container:: external-calls\n\n')
        doc.write(indent + '   .. rubric:: External calls\n\n')
        for library, links in sorted(external_calls.items()):
            doc.write(indent + '   ' + _prose(library) + '\n')
            for ref in links:
                origin = ref.external.module + '::' + ref.external.name
                doc.write(indent + f'     * ``{ref.label}`` (``{origin}``)\n')
            doc.write('\n')

    if (graph_images or {}).get(unit.qualified_name) and (
            unit.derived_types or unit.interfaces or unit.procedures):
        # End the image directive before the indented nested-unit blocks.
        doc.write('\n' + indent + '..\n\n')

    for child in unit.derived_types:
        write_unit(doc, child, depth + 2, show_callers=False,
                   references=references, destinations=destinations, graph_images=graph_images, markup=markup)
    for child in (*unit.interfaces, *unit.procedures):
        write_unit(doc, child, depth + 2, show_callers=show_callers,
                   references=references, destinations=destinations, graph_images=graph_images, markup=markup)
