"""The flint Scanner.

The ``Scanner`` object creates a list of Fortran lexemes from a line of Fortran
source.  The line is expected to be terminated with an endline (``\n``).

We use an object here because there is some "state" regarding line continuation
of split strings.  But more modular design options are possible and could be
used in the future.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import itertools


class Scanner(object):

    punctuation = '=+-*/\\()[]{},:;%&~<>?`|$#@'    # Unhandled Table 3.1 tokens

    # Token pairs (syntax and operators)
    pairs = ('::', '=>', '**', '//', '==', '/=', '<=', '>=', '(/', '/)')

    def __init__(self):
        self.characters = None
        self.char = None
        self.idx = None

        self.prior_delim = None

    def parse(self, line):
        """Tokenize a line of Fortran source."""
        tokens = []

        self.idx = -1   # Bogus value to ensure idx = 0 after first iteration
        self.characters = iter(line)
        self.update_chars()

        # String line continuation?
        lc = True if self.prior_delim else False

        while self.char != '\n':
            word = ''
            if self.char in ' \t':
                while self.char in ' \t':
                    word += self.char
                    self.update_chars()
            elif self.char in '"\'' or (self.prior_delim and not lc):
                word = self.parse_string()
                if self.prior_delim:
                    lc = True

            elif self.char.isalpha() or self.char == '_':
                word = self.parse_name(line)

            elif self.char.isdigit():
                word = self.parse_numeric()

            elif self.char in ('!', '#'):
                # Abort the iteration and build the comment token
                word = line[self.idx:].rstrip('\n')
                self.char = '\n'

            elif self.char == '.':
                self.update_chars()
                if self.char.isdigit():
                    frac = self.parse_numeric()
                    word = '.' + frac
                else:
                    word = '.'
                    while self.char.isalpha():
                        word += self.char
                        self.update_chars()
                    if self.char == '.':
                        word += self.char
                        self.update_chars()

            elif self.char in Scanner.punctuation:
                # Turn off leading line continuation
                if self.char == '&':
                    lc = False

                word = self.char
                self.update_chars()

                # Test for a valid character pair
                pair = word + self.char
                try:
                    if pair in self.pairs:
                        if (
                            pair == '(/' and tokens
                            and tokens[-1] == 'operator'
                        ):
                            pass
                        elif (
                            pair == '/)' and tokens
                            and tokens[-1] == '('
                            and tokens[-2] == 'operator'
                        ):
                            pass
                        else:
                            tokens.append(pair)
                            self.update_chars()
                            continue
                except IndexError:
                    print(line)
                    raise
            else:
                # This should never happen
                raise ValueError

            tokens.append(word)

        # Append the final endline
        if line[-1] == '\n':
            tokens.append(self.char)

        return tokens

    def parse_name(self, line):
        end = self.idx
        for char in line[self.idx:]:
            if not char.isalnum() and char != '_':
                break
            end += 1

        word = line[self.idx:end]

        self.idx = end - 1
        # Update iterator, minus first character which was already read
        self.characters = itertools.islice(self.characters, len(word) - 1,
                                           None)
        self.update_chars()

        return word

    def parse_string(self):
        word = ''

        if self.prior_delim:
            delim = self.prior_delim
            self.prior_delim = None
        else:
            delim = self.char
            word += self.char
            self.update_chars()

        next_delim = None
        while True:
            if self.char == '&':
                self.characters, lookahead = itertools.tee(self.characters)

                # Skip any whitespace after '&'
                # TODO: probably a better way here...
                c = next(lookahead)
                while c in ' \t':
                    c = next(lookahead)

                # If end of line, then this is a line continuation.
                # Otherwise, it is part of the string (or a syntax error)
                if c == '\n':
                    next_delim = delim
                    break
                else:
                    word += '&'

                self.update_chars()

            elif self.char == delim:
                # Check for escaped delimiters
                # TODO: Use a lookahead
                self.update_chars()
                if self.char == delim:
                    word += 2 * delim
                    self.update_chars()
                else:
                    word += delim
                    break
            else:
                word += self.char
                self.update_chars()

        self.prior_delim = next_delim

        return word

    def parse_numeric(self):
        word = ''
        frac = False

        while self.char.isdigit() or (self.char == '.' and not frac):
            # Only allow one decimal point
            if self.char == '.':
                frac = True
            word += self.char
            self.update_chars()

        # Check for float exponent
        if self.char in 'eEdD':
            word += self.char
            self.update_chars()
            if self.char in '+-':
                word += self.char
                self.update_chars()
            while self.char.isdigit():
                word += self.char
                self.update_chars()

        if self.char == '_':
            word += self.char
            self.update_chars()
            named = self.char.isalpha()

            while (self.char.isdigit() or
                   (self.char.isalpha() or self.char == '_' and named)):
                word += self.char
                self.update_chars()

        return word

    def update_chars(self):
        self.char = next(self.characters)
        self.idx += 1
