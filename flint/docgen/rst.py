"""reStructuredText presentation of documentation records.

This writer consumes only the documentation model; it does not inspect Fortran
tokens, traverse a parsed project, or resolve names in the parser's call graph.
"""
import re
import string


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


def write_module(doc, module):
    """Write a module reference to a text stream using the legacy layout."""
    title = module.name + ' module reference'
    doc.write('=' * len(title) + '\n' + title + '\n' + '=' * len(title) + '\n')
    doc.write(_prose(module.summary) + '\n\n')

    for title, entries in (('Data Types', module.derived_types),
                           ('Functions/Subroutines', module.procedures)):
        if entries:
            doc.write(title + '\n' + '=' * len(title) + '\n')
            doc.write('.. list-table::\n\n')
            for entry in entries:
                name = (entry.display_name or entry.name) if title == 'Data Types' else entry.name
                summary = _prose(entry.summary).replace('\n', '\n       ')
                doc.write(f'   * - |{name}|_\n     - {summary}\n\n\n')

    if module.description:
        doc.write('Detailed Description\n====================\n')
        doc.write(_prose(module.description) + '\n\n')

    if module.derived_types:
        doc.write('Type Documentation\n==================\n')
        for entry in module.derived_types:
            write_unit(doc, entry, show_callers=False)

    if module.procedures:
        doc.write('Functions/Subroutine Documentation\n==================================\n\n')
        for entry in module.procedures:
            write_unit(doc, entry)

    for label, entries in (('Type/Interface', module.derived_types),
                           ('Subprogram', module.procedures)):
        if entries:
            doc.write(f'\n.. {label} labels\n\n')
            for entry in entries:
                name = entry.display_name or entry.name
                doc.write(f'.. |{name}| replace:: ``{name}``\n')


def write_unit(doc, unit, depth=0, *, show_callers=True):
    """Write a unit record and its nested types and procedures."""
    indent = depth * ' '
    doc.write(indent + '.. _' + unit.name + ':\n\n')
    doc.write(indent + unit.signature + '\n')
    doc.write(_indented(_prose(unit.summary), indent + '  ') + '\n')
    doc.write('\n')

    if unit.variables:
        doc.write(indent + '  Parameters\n')
    for variable in unit.variables:
        if variable.description:
            doc.write(indent + '    - **' + variable.name + '** :: ')
            if variable.intent:
                doc.write(f'[{variable.intent}] ')
            description = _prose(variable.description).replace('\n', '\n' + indent + '      ')
            doc.write(description + '\n\n')

    for title, names in (('Calls into', unit.callees),
                         ('Called by', unit.callers if show_callers else ())):
        if names:
            doc.write('\n' + indent + title + '\n')
            doc.write(indent + '  ' + ' '.join(f'|{name}|_' for name in names) + '\n\n')

    for child in unit.derived_types:
        write_unit(doc, child, depth + 2, show_callers=False)
    for child in unit.procedures:
        write_unit(doc, child, depth + 2, show_callers=show_callers)
