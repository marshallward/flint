class Tokenizer(object):

    # I don't use these two
    special_chars = ' =+-*/\\()[]{},.:;!"%&~<>?\'`|$#@'     # Table 3.1
    lexical_tokens = '=+-*/()[],.:;%&<>'                    # Meaningful?

    # I only use this one
    punctuation = '=+-*/\\()[]{},:;%&~<>?`|$#@'    # Unhandled Table 3.1 tokens

    # These are the strict keywords, but I believe any name is possible?
    # Actually, I don't use these either...
    logical_kw = ['not', 'and', 'or', 'eqv', 'neqv']
    relational_kw = ['lt', 'le', 'gt', 'ge', 'eq', 'ne']
    logical_value = ['true', 'false']

    def __init__(self):
        self.characters = None
        self.prior_char = None
        self.char = None

        self.prior_delim = None

    def parse(self, line):
        """Tokenize a line of Fortran source."""

        tokens = []

        word = ''
        self.characters = iter(line)
        self.char = next(self.characters)

        while self.char != '\n':
            if self.char in ' \t':
                while self.char in ' \t':
                    word += self.char
                    self.char = next(self.characters)

            elif self.char in '"\'' or self.prior_delim:
                word = self.parse_string()
                if (self.prior_char, self.char) == ('&', '\n'):
                    tokens.append(word)
                    word = self.prior_char

            elif self.char.isalpha() or self.char == '_':
                # NOTE: Variables cannot start with underscore
                #       But keep for now to accommodate preprocessed tags
                while self.char.isalnum() or self.char == '_':
                    word += self.char
                    self.char = next(self.characters)

            # TODO: Leading sign (-5e4)
            elif self.char.isdigit():
                word, self.char = self.parse_numeric(self.char)

            elif self.char in ('!', '#'):
                while self.char != '\n':
                    word += self.char
                    self.char = next(self.characters)

            elif self.char == '.':
                self.char = next(self.characters)
                if self.char.isdigit():
                    frac, self.char = self.parse_numeric(self.char)
                    word = '.' + frac
                else:
                    word = '.'
                    while self.char.isalpha():
                        word += self.char
                        self.char = next(self.characters)
                    if self.char == '.':
                        word += self.char
                        self.char = next(self.characters)

            elif self.char in Tokenizer.punctuation:
                # TODO: Check for valid two-character tokens
                word += self.char
                self.char = next(self.characters)

            else:
                # This should never happen
                raise ValueError

            tokens.append(word)
            word = ''

        return tokens

    # TODO: Manage iteration better, rather than using char at in/out
    def parse_string(self):
        word = ''

        if self.prior_delim:
            delim = self.prior_delim
            self.prior_delim = None
        else:
            delim = self.char
            word += self.char
            self.prior_char, self.char = self.char, next(self.characters)

        next_delim = None
        while True:
            if self.char == '&':
                self.prior_char, self.char = self.char, next(self.characters)
                if self.char == '\n':
                    next_delim = delim
                    break
                else:
                    word += '&'
            elif self.char == delim:
                # Check for escaped delimiters
                self.prior_char, self.char = self.char, next(self.characters)
                if self.char == delim:
                    word += 2 * delim
                    self.prior_char, self.char = (self.char,
                                                  next(self.characters))
                else:
                    word += delim
                    break
            else:
                word += self.char
                self.prior_char, self.char = self.char, next(self.characters)

        self.prior_delim = next_delim

        return word

    def parse_numeric(self, char):
        word = ''
        frac = False

        while char.isdigit() or (char == '.' and not frac):
            # Only allow one decimal point
            if char == '.':
                frac = True
            word += char
            char = next(self.characters)

        # Check for float exponent
        if char in 'eEdD':
            word += char
            char = next(self.characters)
            if char in '+-':
                word += char
                char = next(self.characters)
            while char.isdigit():
                word += char
                char = next(self.characters)

        if char == '_':
            word += char
            char = next(self.characters)
            label = False
            while char.isalpha() or (char.isdigit() and not label):
                if char.isalpha():
                    label = False
                word += char
                char = next(self.characters)

        return word, char
