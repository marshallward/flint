from flint.document import is_docstring


class FortLines(object):
    """Fortran source line iterator."""

    def __init__(self, lines):
        self.lines = iter(lines)
        self.current_line = None
        self.current_doc = ''

        # Split lines
        self.buffered_line = None

        # Docstring buffer
        # Saved as a list to track multiple docstrings of split lines
        # XXX: Still debating whether to leave these as tokens or not
        self.docstrings = []

        # Track the previous variable, to append any docstrings after current
        # variable
        # TODO: What about the final read?  This really needs to be some sort
        # of general event.
        self.prior_var = None

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
        # TODO: Track and report these?
        while (line == []):
            self.current_doc = '\n'.join([self.current_doc, doc])
            doc = ''

            # XXX: What about null lines in semicolons? e.g. "; <stmt> ; ;"?
            #   We need to deplete buffered_lines before going back to lines!
            line = next(self.lines)

            # Append any lone docstrings to the prior docstring
            if line and is_docstring(line[-1]):
                doc = line.pop()

        # We are now on a new non-blank line, so flush the docstring
        self.docstrings.append(self.current_doc)
        self.current_doc = doc

        # Join extended lines
        # TODO: 255-limit line check
        string_append = False
        while line[-1] == '&':
            next_line = next(self.lines)
            if next_line and is_docstring(next_line[-1]):
                self.current_doc = '\n'.join([self.current_doc, next_line.pop()])
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
        return line
