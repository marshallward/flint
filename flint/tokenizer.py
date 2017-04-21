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
        self.prior_delim = None

    def parse(self, line):
        """Tokenize a line of Fortran source."""

        tokens = []

        word = ''
        characters = iter(line)
        char = next(characters)

        while char != '\n':
            if char in ' \t':
                while char in ' \t':
                    word += char
                    char = next(characters)

            elif char in '"\'' or self.prior_delim:
                word, char = self.parse_string(characters, char)

            elif char.isalpha() or char == '_':
                # NOTE: Variables cannot start with underscore
                #       But keep for now to accommodate preprocessed tags
                while char.isalnum() or char == '_':
                    word += char
                    char = next(characters)

            # TODO: Leading sign (-5e4)
            elif char.isdigit():
                word, char = self.parse_numeric(characters, char)

            elif char in ('!', '#'):
                while char != '\n':
                    word += char
                    char = next(characters)

            elif char == '.':
                char = next(characters)
                if char.isdigit():
                    frac, char = self.parse_numeric(characters, char)
                    word = '.' + frac
                else:
                    while char.isalpha():
                        word += char
                        char = next(characters)
                    if char == '.':
                        word += char
                        char = next(characters)

            elif char in Tokenizer.punctuation:
                # TODO: Check for valid two-character tokens
                word += char
                char = next(characters)

            else:
                # This should never happen
                raise ValueError

            tokens.append(word)
            word = ''

        return tokens

    # TODO: Manage iteration better, rather than using char at in/out
    def parse_string(self, characters, char):
        word = ''

        if self.prior_delim:
            delim = self.prior_delim
            self.prior_delim = None
        else:
            delim = char
            word += char
            char = next(characters)

        next_delim = None
        while True:
            if char == '&':
                char = next(characters)
                if char == '\n':
                    next_delim = delim
                    break
                else:
                    word += '&'
            elif char == delim:
                # Check for escaped delimiters
                char = next(characters)
                if char == delim:
                    word += 2 * delim
                    char = next(characters)
                else:
                    word += delim
                    break
            else:
                word += char
                char = next(characters)

        self.prior_delim = next_delim
        return word, char

    def parse_numeric(self, characters, char):
        word = ''
        frac = False

        while char.isdigit() or (char == '.' and not frac):
            # Only allow one decimal point
            if char == '.':
                frac = True
            word += char
            char = next(characters)

        # Check for float exponent
        if char in 'eEdD':
            word += char
            char = next(characters)
            if char in '+-':
                word += char
                char = next(characters)
            while char.isdigit():
                word += char
                char = next(characters)

        if char == '_':
            word += char
            char = next(characters)
            label = False
            while char.isalpha() or (char.isdigit() and not label):
                if char.isalpha():
                    label = False
                word += char
                char = next(characters)

        return word, char
