import itertools
from flint.document import is_docstring


class FortLines(object):
    """Fortran source line iterator."""

    def __init__(self, lines):
        self.lines = iter(lines)
        self.current_line = None
        self.current_doc = ''
        self.prior_doc = ''

        # Split lines
        self.buffered_line = None

        # Track the previous variable, to append any docstrings after current
        # variable
        # TODO: What about the final read?  This really needs to be some sort
        # of general event.
        self.prior_var = None

        # Before starting iteration, extract any header docstrings
        self.lines, lookahead = itertools.tee(self.lines)
        self.header = ''
        for line in lookahead:
            if len(line) > 1:
                break
            elif line and is_docstring(line[-1]):
                # NOTE: Also removes the docstring from lines in self.lines!
                doc = line.pop()
                self.header = '\n'.join([self.header, doc])
            # else: line is blank; continue

        # XXX: Trying this out...
        self.current_doc = self.header

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self.buffered_line:
            line = self.buffered_line
            self.buffered_line = None
        else:
            line = next(self.lines)

        # Skip empty lines
        while (line == []):
            line = next(self.lines)

        # Extract any docstrings
        doc = ''
        if line and is_docstring(line[-1]):
            doc = line.pop()

        if ';' in line:
            idx = line.index(';')
            line, self.buffered_line = line[:idx], line[1 + idx:]

            # How literally do we handle end-line semicolons?
            # This tosses them aside
            if self.buffered_line == []:
                self.buffered_line = None

        # Skip empty lines
        while (line == []):
            line = next(self.lines)

        # Join extended lines
        # TODO: 255-limit line check
        string_append = False
        while line[-1] == '&':
            next_line = next(self.lines)
            if next_line and is_docstring(next_line[-1]):
                doc = '\n'.join([doc, next_line.pop()])
                if not next_line:
                    continue

            if ((len(line) > 1 and (line[-2][0] in '"\''
                                    and line[-2][-1] not in '"\''))
                    or string_append):
                if '&' in next_line:
                    idx = next_line.index('&') + 1
                else:
                    # Search for the first non-whitespace token
                    idx = 0
                    for word in next_line:
                        if all(w in ' \t' for w in word):
                            idx += 1

                    # TODO: With no matching &, some care is needed to align
                    # the whitespace correctly.  A job for another day!

                new_string = line[-2] + next_line[idx]
                line = line[:-2] + [new_string] + next_line[idx + 1:]

                # True if string continues to next line
                string_append = (next_line[idx][-1] not in '"\'')
            else:
                idx = 1 if next_line[0] == '&' else 0
                line = line[:-1] + next_line[idx:]

        self.current_line = line

        if not self.buffered_line:
            # Append any subsequent docstrings to the current line
            self.lines, lookahead = itertools.tee(self.lines)

            for toks in lookahead:
                doc_ext = ''
                if toks:
                    if is_docstring(toks[0]):
                        # NOTE: Also removes the docstring from lines in self.lines!
                        doc_ext = toks.pop()
                        doc = '\n'.join([doc, doc_ext])
                    else:
                        break
                # else: line is blank; continue

        self.prior_doc = self.current_doc
        self.current_doc = doc

        return line
