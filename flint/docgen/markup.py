"""Comment frontends producing reStructuredText without a rendering dependency.

The Doxygen frontend implements an explicit subset, not the Doxygen program.
Unrecognized commands raise an error rather than silently losing their meaning.
Reference and citation roles are left for a project's document resolver.
"""
import html
import re
import string
import textwrap


def plain(text):
    """Escape prose while retaining paragraph boundaries."""
    paragraphs = re.split(r'\n\s*\n', text.strip())
    result = []
    for paragraph in paragraphs:
        paragraph = ' '.join(paragraph.split())
        if not paragraph:
            continue
        escaped = re.sub(r'([\\`*_|\[\]:<>])', r'\\\1', paragraph)
        if not escaped.startswith('\\') and (
                paragraph[0] in string.punctuation
                or re.match(r'(?:\d+|[A-Za-z]+)[.)](?:\s|$)', paragraph)):
            escaped = '\\' + escaped
        result.append(escaped)
    return '\n\n'.join(result)


def _inline(text):
    """Translate inline markup, escaping all remaining prose literally."""
    saved = []

    def keep(value):
        saved.append(value)
        return f'FLINTINLINE{len(saved)-1}TOKEN'

    text = re.sub(r'\\f\$(.*?)\\f\$',
                  lambda m: keep(':math:`' + ' '.join(m[1].split()) + '`'), text, flags=re.S)
    text = re.sub(r'\[([^\]]+)\]\([\\@]ref\s+([\w:.-]+)\)',
                  lambda m: keep(':ref:`' + m[1] + ' <' + m[2] + '>`'), text)
    text = re.sub(r'[\\@](cite|ref)\s+([\w:.-]+)',
                  lambda m: keep(':' + m[1] + ':`' + m[2].rstrip('.') + '`')
                            + ('.' if m[2].endswith('.') else ''), text)
    text = re.sub(r'<a\s+href=["\']([^"\']+)["\']\s*>(.*?)</a>',
                  lambda m: keep('`' + plain(m[2]) + ' <' + m[1] + '>`__'), text, flags=re.S | re.I)
    for tag, before, after in (('code', '``', '``'), ('tt', '``', '``'),
                               ('em', '*', '*'), ('i', '*', '*'),
                               ('b', '**', '**'), ('strong', '**', '**'),
                               ('sub', ':sub:`', '`'), ('sup', ':sup:`', '`')):
        text = re.sub(fr'<{tag}>(.*?)</{tag}>',
                      lambda m: keep(before + m[1] + after), text, flags=re.S | re.I)
    text = re.sub(r'`([^`]+)`', lambda m: keep('``' + m[1] + '``'), text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  lambda m: keep('`' + plain(m[1]) + ' <' + m[2] + '>`__'), text)
    for marker in ('**', '*'):
        token = re.escape(marker)
        text = re.sub(r'(?<!\w)' + token + r'(\S(?:.*?\S)?)' + token + r'(?!\w)',
                      lambda m: keep(marker + plain(m[1]) + marker), text)
    text = re.sub(r'[\\@](?:c|p)\s+(\S+)', lambda m: keep('``' + m[1] + '``'), text)
    text = re.sub(r'[\\@](?:a|e|em)\s+(\S+)', lambda m: keep('*' + plain(m[1]) + '*'), text)
    text = re.sub(r'[\\@]b\s+(\S+)', lambda m: keep('**' + plain(m[1]) + '**'), text)
    text = re.sub(r'\\([@#$&])', lambda m: keep(plain(m[1])), text)
    # Avoid treating email addresses as commands. LaTeX belongs inside math.
    unknown = re.search(r'\\([A-Za-z]+)|(?<!\w)@([A-Za-z]+)', text)
    if unknown:
        raise ValueError(f'Unsupported Doxygen command: {unknown[0]}')
    result = plain(html.unescape(text.replace('\\(', '(').replace('\\)', ')')))
    for index, value in reversed(list(enumerate(saved))):
        result = result.replace(f'FLINTINLINE{index}TOKEN', value)
    return result


def _paragraph(text):
    """Retain lists and schematic ASCII paragraphs instead of flattening them."""
    lines = text.splitlines()
    if any(re.search(r'--o--|\|[-+]{2,}|[-+]{2,}\|', line) for line in lines):
        return '.. code-block:: text\n\n' + textwrap.indent(textwrap.dedent(text), '   ')
    items = []
    intro = []
    for line in lines:
        bullet = re.match(r'\s*([-+*]|\d+[.)])\s+(.*)', line)
        if bullet:
            items.append([bullet[1], bullet[2]])
        elif items:
            items[-1][1] += ' ' + line.strip()
        else:
            intro.append(line.strip())
    if not items:
        return _inline(text)
    result = [_inline(' '.join(intro))] if intro else []
    result.extend(marker + ' ' + _inline(body) for marker, body in items)
    return '\n\n'.join(result)


def doxygen(text):
    """Convert supported Doxygen comments to native, renderer-independent reST."""
    blocks = []

    def block(value):
        blocks.append(value)
        return f'\n\nFLINTBLOCK{len(blocks)-1}TOKEN\n\n'

    def literal(match):
        return block('.. code-block:: text\n\n' + textwrap.indent(
            textwrap.dedent(match[1]).strip('\n'), '   '))

    # Extract literal content first: it must never be parsed as commands or tables.
    text = re.sub(r'[\\@]verbatim\b[ \t]*\n?(.*?)[\\@]endverbatim\b', literal, text, flags=re.S)
    text = re.sub(r'[\\@]code(?:\{[^}]*\})?[ \t]*\n?(.*?)[\\@]endcode\b', literal, text, flags=re.S)
    escaped = []

    def escape_command(match):
        escaped.append(match[0].removeprefix('\\'))
        return f'FLINTESCAPE{len(escaped)-1}TOKEN'

    text = re.sub(r'\\@|(?<=\w)@(?=\w)', escape_command, text)

    def math(body):
        # Doxygen uses doubled escaping for TeX row separators in comments.
        body = textwrap.dedent(body).strip().replace('\\\\\\\\', '\\\\')
        return block('.. math::\n\n' + textwrap.indent(body, '   '))

    text = re.sub(r'\\f\[(.*?)\\f\]', lambda m: math(m[1]), text, flags=re.S)

    def environment(match):
        name, body = match[1], match[2]
        if name in ('eqnarray', 'eqnarray*', 'align', 'align*'):
            if name.startswith('eqnarray'):
                body = re.sub(r'&\s*([^&\n]+?)\s*&', r'&\1', body)
            name = 'aligned'
        return math('\\begin{' + name + '}\n' + body.strip() + '\n\\end{' + name + '}')

    text = re.sub(r'\\f\{([\w*]+)\}\{?(.*?)\\f\}', environment, text, flags=re.S)
    # Inline math may span source lines. Keep it out of structural processing.
    inline_math = []

    def save_math(match):
        inline_math.append(match[0])
        return f'FLINTMATHTOKEN{len(inline_math)-1}END'

    text = re.sub(r'\\f\$(.*?)\\f\$', save_math, text, flags=re.S)
    text = re.sub(r'[\\@]namespace\s+(\w+)', lambda m: block('.. _' + m[1] + ':'), text)
    text = re.sub(r'[\\@](?:subsubsection|subsection|section)\s+(\w+)\s+([^\n]+)',
                  lambda m: block('.. _' + m[1] + ':\n\n.. rubric:: ' + _inline(m[2])), text)
    text = re.sub(r'[\\@]anchor\s+(\w+)', lambda m: block('.. _' + m[1] + ':'), text)
    text = re.sub(r'[\\@](?:brief|details)\s+', '', text)
    text = re.sub(r'[\\@](author|authors|date|note|warning|todo|remark|return|returns|see|sa)\b\s*\{?',
                  lambda m: '\n\n' + m[1].title() + ': ', text)
    if text.rstrip().endswith('}') and 'Remark:' in text:
        text = text.rstrip()[:-1]
    text = re.sub(r'[\\@]param(?:\[([^]]+)\])?\s+(\w+)\s*',
                  lambda m: '\n\nParameter ' + m[2] + (' [' + m[1] + ']' if m[1] else '') + ': ', text)
    text = re.sub(r'[\\@]image\s+html\s+(\S+)([^\n]*)',
                  lambda m: block('.. figure:: ' + m[1] + '\n\n   ' + _inline(m[2].strip().strip('"'))), text)
    text = re.sub(r'<br\s*/?>', '\n\n', text, flags=re.I)

    def restore_math(value):
        for index, expression in enumerate(inline_math):
            value = value.replace(f'FLINTMATHTOKEN{index}END', expression)
        return value

    def table(match):
        rows = [[cell.strip() for cell in line.strip().strip('|').split('|')]
                for line in match[0].splitlines()]
        header = len(rows) > 1 and all(re.fullmatch(r'[: -]+', cell) for cell in rows[1])
        if header:
            del rows[1]
        if len({len(row) for row in rows}) != 1:
            raise ValueError('Inconsistent Doxygen table column count')
        result = '.. list-table::\n' + ('   :header-rows: 1\n' if header else '') + '\n'
        for row in rows:
            result += '   * - ' + '\n     - '.join(_inline(restore_math(cell)) for cell in row) + '\n'
        return block(result.rstrip())

    text = re.sub(r'(?m)^[ \t]*\|[^\n]*\|[ \t]*(?:\n[ \t]*\|[^\n]*\|[ \t]*)*', table, text)
    result = '\n\n'.join(_paragraph(restore_math(p)) for p in re.split(r'\n\s*\n', text) if p.strip())
    for index, value in enumerate(blocks):
        result = result.replace(f'FLINTBLOCK{index}TOKEN', value)
    for index, value in enumerate(escaped):
        result = result.replace(f'FLINTESCAPE{index}TOKEN', value)
    # A namespace and its first section occasionally share the same target.
    result = re.sub(r'(\.\. _([^\n]+):\n\s*\n)\.\. _\2:\n', r'\1', result)
    return result


def documentation(text, markup='plain'):
    if markup == 'plain':
        return plain(text)
    if markup == 'rst':
        return textwrap.dedent(text).strip('\n')
    if markup == 'doxygen':
        return doxygen(text)
    raise ValueError(f'Unsupported documentation markup: {markup}')
