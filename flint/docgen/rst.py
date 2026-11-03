"""reStructuredText presentation of documentation records.

This writer consumes only the documentation model; it does not inspect Fortran
tokens, traverse a parsed project, or resolve names in the parser's call graph.
"""
import re
import string

from flint.docgen.references import Reference, ReferenceIndex, anchor


def _prose(text):
    """Render plain prose, preserving paragraphs rather than source indentation.

    This is deliberately writer policy: the model retains the original text so
    a future strict reST mode can bypass this normalization.
    """
    paragraphs = re.split(r'\n\s*\n', text.strip())
    result = []
    for paragraph in paragraphs:
        paragraph = ' '.join(line.strip() for line in paragraph.splitlines()).strip()
        if not paragraph:
            continue
        escaped = re.sub(r'([\\`*_|\[\]:<>])', r'\\\1', paragraph)
        # Prevent incidental bullets, enumerations, directives, and adornments
        # from becoming block markup. Inline markup was escaped above.
        if not escaped.startswith('\\') and (
                paragraph[0] in string.punctuation
                or re.match(r'(?:\d+|[A-Za-z]+)[.)](?:\s|$)', paragraph)):
            escaped = '\\' + escaped
        result.append(escaped)
    return '\n\n'.join(result)


def _indented(text, indent):
    return '\n'.join(indent + line if line else '' for line in text.split('\n'))


def _link(reference, references, current, destinations):
    if reference.target is None:
        return '``' + reference.label + '``'
    if destinations is not None:
        target = destinations.destination(reference.target, current)
    elif references.pages[reference.target] == references.pages[current]:
        target = anchor(reference.target) + '_'
    else:
        return '``' + reference.label + '``'
    return f'`{_prose(reference.label)} <{target}>`__'


def write_module(doc, module, *, references=None, destinations=None):
    """Write a module reference to a text stream using the legacy layout."""
    if references is None:
        references = ReferenceIndex((module,))
    title = module.name + ' module reference'
    doc.write('=' * len(title) + '\n' + title + '\n' + '=' * len(title) + '\n')
    doc.write(_prose(module.summary) + '\n\n')
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
                name = (entry.display_name or entry.name) if title == 'Data Types' else entry.name
                summary = _prose(entry.summary).replace('\n', '\n       ')
                link = _link(Reference(name, entry.qualified_name), references,
                             module.qualified_name, destinations)
                doc.write(f'   * - {link}\n     - {summary}\n\n\n')

    if module.description:
        doc.write('Detailed Description\n====================\n')
        doc.write(_prose(module.description) + '\n\n')

    if module.derived_types:
        doc.write('Type Documentation\n==================\n')
        for entry in module.derived_types:
            write_unit(doc, entry, show_callers=False, references=references, destinations=destinations)

    if module.interfaces:
        doc.write('Generic Interface Documentation\n===============================\n\n')
        for entry in module.interfaces:
            write_unit(doc, entry, references=references, destinations=destinations)

    if declarations:
        doc.write('Procedure Interface Documentation\n=================================\n\n')
        for entry in declarations:
            write_unit(doc, entry, references=references, destinations=destinations)

    if implementations:
        doc.write('Functions/Subroutine Documentation\n==================================\n\n')
        for entry in implementations:
            write_unit(doc, entry, references=references, destinations=destinations)


def write_unit(doc, unit, depth=0, *, show_callers=True, references=None, destinations=None):
    """Write a unit record and its nested types and procedures."""
    indent = depth * ' '
    doc.write(indent + '.. _' + anchor(unit.qualified_name) + ':\n\n')
    doc.write(indent + unit.signature + '\n')
    doc.write(_indented(_prose(unit.summary), indent + '  ') + '\n')
    doc.write('\n')

    if any(variable.description for variable in unit.variables):
        doc.write(indent + '  Parameters\n')
    for variable in unit.variables:
        if variable.description:
            doc.write(indent + '    - **' + variable.name + '** :: ')
            if variable.intent:
                doc.write(f'[{variable.intent}] ')
            description = _prose(variable.description).replace('\n', '\n' + indent + '      ')
            doc.write(description + '\n\n')

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

    external_calls = {}
    if references is not None:
        for ref in references.calls[unit.qualified_name]:
            if ref.external is not None:
                external_calls.setdefault(ref.external.library, []).append(ref)
    if external_calls:
        doc.write('\n' + indent + '.. container:: external-calls\n\n')
        doc.write(indent + '   .. rubric:: External calls\n\n')
        for library, links in sorted(external_calls.items()):
            doc.write(indent + '   ' + _prose(library) + '\n')
            for ref in links:
                origin = ref.external.module + '::' + ref.external.name
                doc.write(indent + f'     * ``{ref.label}`` (``{origin}``)\n')
            doc.write('\n')

    for child in unit.derived_types:
        write_unit(doc, child, depth + 2, show_callers=False,
                   references=references, destinations=destinations)
    for child in (*unit.interfaces, *unit.procedures):
        write_unit(doc, child, depth + 2, show_callers=show_callers,
                   references=references, destinations=destinations)
