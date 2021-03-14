import itertools
from flint.document import is_docstring
from flint.tokenizer import Tokenizer
from flint.token import Token

# NOTE: This flag should be phased out
from flint import use_str_as_token


# This probably ought to be somewhere else, but leaving it here for now.
def gen_stmt(line, depth=0):
    """Recreate the statement by gathering tokens and null tokens."""
    if use_str_as_token:
        s = ' ' * depth + ' '.join([tok for tok in line])
    else:
        # Pad newlines by two spaces to match tagged lines
        # XXX: This works, but alters the tail of the token.
        #   We only want to do this inside the function.
        for tok in line:
            for i, ntok in enumerate(tok.tail):
                if ntok == '\n':
                    tok.tail.insert(i+1, '   ')

        s = ''.join([tok + ''.join(tok.tail) for tok in line])
        if line:
            s = ''.join(line[0].head) + s

    return s


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
            # First strip leading semicolons to avoid null lines
            while line[0] == ';':
                line = line[1:]

            # Now do the formal split
            idx = line.index(';')
            line, self.buffered_line = line[:idx], line[1 + idx:]

            # Again, strip any leading semicolons from the buffer
            while self.buffered_line and self.buffered_line[0] == ';':
                self.buffered_line = self.buffered_line[1:]

            # Nullify the buffer if it's empty or a lone line continuation
            if self.buffered_line in (['&'], []):
                self.buffered_line = None

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

                # XXX: Token() promotion also wipes out the .tail value here.
                #   No clear plan yet on how to handle trailing null tokens for
                #   split strings (or even lines) since we literally invent a
                #   new token here.  This needs a plan.
                new_string = line[-2] + next_line[idx]
                if not use_str_as_token:
                    new_string = Token(new_string)
                line = line[:-2] + [new_string] + next_line[idx + 1:]

                # True if string continues to next line
                string_append = (next_line[idx][-1] not in '"\'')

            elif ';' in next_line:
                # First strip leading semicolons to avoid null lines
                # NOTE: This could probably be moved outside of the block.
                while line[0] == ';':
                    line = line[1:]

                idx = next_line.index(';')

                line = line[:-1] + next_line[:idx]
                self.buffered_line = next_line[1 + idx:]

                # Skip repeated semicolons
                while self.buffered_line and self.buffered_line[0] == ';':
                    self.buffered_line = self.buffered_line[1:]

                # A lone line continuation serves no purpose (and may not even
                # be compliant) so we drop it.
                # We also nullify any empty buffers.
                if self.buffered_line in (['&'], []):
                    self.buffered_line = None

            else:
                if next_line[0] == '&':
                    if next_line[0].tail or line[-2].tail:
                        idx = 1
                    else:
                        # Check for line continuations inbetween tokens

                        # XXX: The following is a very overengineered method to
                        # distinguish between two tokens which may be split
                        # along a line separation but not separated by any
                        # whitespace.
                        #
                        # e.g. integer&
                        #             &:: x
                        #
                        # The tokens will be
                        #   [['integer', '&'], ['&', '::', 'x']]
                        #
                        # Our method will concatenate to
                        #   'integer::'
                        # due to lack of whitespace.
                        #
                        # We then Tokenizer.parse() it to ['integer', '::'] and
                        # wedge it between the two lines.
                        #
                        # This method is flawed and we really ought to just
                        # handle line continuations in Tokenizer.parse(), and
                        # log it in our Token metadata (e.g. like Token.tail).
                        # Then this horrible code can be ditched.
                        #
                        # But for now, it stays.
                        tokenizer = Tokenizer()
                        tokstr = line[-2] + next_line[1] + line[-1] + '\n'
                        new_toks = tokenizer.parse(tokstr)
                        line = line[:-2] + [Token(tok) for tok in new_toks]
                        line[-2].tail = next_line[1].tail

                        idx = 2
                else:
                    idx = 0

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
