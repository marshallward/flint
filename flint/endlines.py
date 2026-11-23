"""Physical Fortran line endings, preserving their source spelling."""


def is_endline(text):
    return text in ('\n', '\r\n', '\r')


def count_endlines(text):
    """Count CRLF as one boundary, along with standalone LF and CR."""
    return text.count('\n') + text.count('\r') - text.count('\r\n')


def line_tail(text):
    """Return text after its last physical line ending."""
    return text[max(text.rfind('\n'), text.rfind('\r')) + 1:]


def normalize_endlines(text):
    """Normalize presentation text, not source rendering."""
    return text.replace('\r\n', '\n').replace('\r', '\n')
