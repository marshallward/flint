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
        # Testing (TODO: Remove this)
        if line[-1] != '\n':
            line += '\n'

        tokens = []

        word = ''
        characters = iter(line)
        char = next(characters)

        next_delim = None
        while char != '\n':
            if char in ' \t':
                while char in ' \t':
                    word += char
                    char = next(characters)

            elif char in '"\'' or self.prior_delim:
                if self.prior_delim:
                    delim = self.prior_delim
                    self.prior_delim = None
                else:
                    delim = char
                    word += char
                    char = next(characters)

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

            elif char.isalnum() or char == '_':
                if char.isdigit():
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
                else:
                    # TODO: Variables cannot start with underscore
                    #       Keep for now to accommodate preprocessed tags
                    while char.isalnum() or char == '_':
                        word += char
                        char = next(characters)

            elif char in ('!', '#'):
                while char != '\n':
                    word += char
                    char = next(characters)

            elif char == '.':
                word += char
                char = next(characters)
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

        self.prior_delim = next_delim
        return tokens
