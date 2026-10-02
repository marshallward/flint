"""The flint Scanner.

The ``Scanner`` object creates a list of Fortran lexemes from a line of Fortran
source.  The line is expected to be terminated with an endline (``\n``).

We use an object here because there is some "state" regarding line continuation
of split strings.  But more modular design options are possible and could be
used in the future.

:copyright: Copyright 2026 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import string

class Scanner(object):

    # The Fortran Alphabet
    alpha = string.ascii_letters
    digit = string.digits
    alnum = alpha + digit + '_'
    blank = string.whitespace.replace('\n', '')
    special = '=+-*/\\()[]{},.:;!"%&~<>?\'`^|$#@\n'  # Special characters
    charset = alnum + blank + special
    
    
    # Function to remove characters from strings
    def notchar(chars, ref=charset):
        base = ref
        for c in chars:
            base = ''.join(base.split(c))
        return base


    # Quasi-DFA scanner
    # (Still has some NFA bits to it, need to work them out...)
    M = {
        # Start state
        'start': dict(
            **{c: 'blank' for c in blank},
            **{c: 'id' for c in alpha + '_'},
            **{c: 'num' for c in digit},
            **{'.': 'dec'},
            **{"'": 'str_a'},
            **{'"': 'str_q'},
            **{'!': 'cmt'},
            **{'#': 'cmt'},
            **{':': 'op_colon'},
            **{'=': 'op_equal'},
            **{'*': 'op_star'},
            **{'/': 'op_slash'},
            **{'<': 'op_lt_gt'},
            **{'>': 'op_lt_gt'},
            **{'(': 'op_lpar'},
            **{c: 'op' for c in notchar('."\'!#:=*/<>(', special)},
        ),
        # Identifiers (keywords, functions, variables, ...)
        # NOTE: We permit identifiers to start with _ for preprocessor support
        'id': dict(
            **{c: 'id' for c in alnum},
            **{c: 'end' for c in blank + special},
        ),
        # Blanks
        # NOTE: Endlines are not handled as blanks, but as punctuation
        'blank': dict(
            **{c: 'blank' for c in blank},
            **{c: 'end' for c in alnum + special},
        ),
        # NOTE: Strings can also accept unicode characters, may need defaultdict()
        # Apostrophe string
        'str_a': dict(
            **{c: 'str_a' for c in notchar("'&")},
            **{'&': 'str_a_lc'},
            **{"'": 'str_a_esc'},
        ),
        # Apostrophe (escape)
        'str_a_esc': dict(
            **{"'": 'str_a'},
            **{c: 'end' for c in notchar("'")},
        ),
        'str_a_lc': dict(
            **{c: 'str_a_lc' for c in blank + '&'},
            **{"'": 'str_a_esc'},
            **{'\n': 'str_a_lc_end'},
            **{c: 'str_a' for c in notchar(blank + "&'\n")},
        ),
        # Quote string
        'str_q': dict(
            **{c: 'str_q' for c in notchar('"&')},
            **{'&': 'str_q_lc'},
            **{'"': 'str_q_esc'},
        ),
        # Quote (escape)
        'str_q_esc': dict(
            **{'"': 'str_q'},
            **{c: 'end' for c in notchar('"')},
        ),
        'str_q_lc': dict(
            **{c: 'str_q_lc' for c in blank + '&'},
            **{'"': 'str_q_esc'},
            **{'\n': 'str_q_lc_end'},
            **{c: 'str_q' for c in notchar(blank + '&"\n')},
        ),
        # Decimal mark
        'dec': dict(
            **{c: 'num_frac' for c in digit},
            **{c: 'op_keyword' for c in alpha},
            **{c: 'end' for c in notchar(digit + alpha)},
        ),
        # Numeric: Leading digit
        'num': dict(
            **{c: 'num' for c in digit},
            **{'.': 'num_frac'},
            **{c: 'num_float' for c in 'eEdD'},
            **{'_': 'op_kind'},
            **{c: 'end' for c in notchar(digit + '._eEdD')},
        ),
        # Kind delimiter
        # NOTE: This binds the kind to the literal.
        #   I may want to split them, but it will require a backreference.
        'op_kind': dict(
            **{c: 'id' for c in alpha},
            **{c: 'num_int' for c in digit},
        ),
        'num_int': dict(
            **{c: 'num_int' for c in digit},
            **{c: 'end' for c in notchar(digit)},
        ),
        # Numeric: fractional digits
        'num_frac': dict(
            **{c: 'num_frac' for c in digit},
            **{c: 'num_float' for c in 'eEdD'},
            **{c: 'num_op_kw' for c in notchar('eEdD', alpha)},
            **{'_': 'op_kind'},
            **{c: 'end' for c in notchar(alnum)},
        ),
        # Numeric: Float exponent sign
        'num_float': dict(
            **{c: 'num_float_sign' for c in '+-'},
            **{c: 'num_float_exp' for c in digit},
            **{c: 'num_op_kw' for c in alpha + '_'},
            **{c: 'end' for c in notchar(alnum + '+-')},
        ),
        # Numeric: Signed exponent lead
        'num_float_sign': dict(
            **{c: 'num_float_exp' for c in digit},
            **{c: 'end' for c in notchar(digit)},
        ),
        # Numeric: Signed exponent lead
        'num_float_exp': dict(
            **{c: 'num_float_exp' for c in digit},
            **{'_': 'op_kind'},
            **{c: 'end' for c in notchar(digit + '_')},
        ),
        # Numeric: integer followed by a keyword operator (e.g. 1.and.)
        # NOTE: This is a backreference
        'num_op_kw': dict(
            **{c: 'num_op_kw' for c in alpha},
            **{'.': 'num_op_kw_end'},
        ),
        # Single-character tokens (operators, declaration, etc)
        'op': dict(
            **{c: 'end' for c in charset},
        ),
        # Two-character tokens
        'op_colon': dict(
            **{':': 'op'},
            **{c: 'end' for c in notchar(':')},
        ),
        'op_equal': dict(
            **{'>': 'op'},
            **{'=': 'op'},
            **{c: 'end' for c in notchar('>=')},
        ),
        'op_star': dict(
            **{'*': 'op'},
            **{c: 'end' for c in notchar('*')},
        ),
        'op_slash': dict(
            **{'/': 'op'},
            **{'=': 'op'},
            **{')': 'op'},
            **{c: 'end' for c in notchar('/=)')},
        ),
        'op_lt_gt': dict(
            **{'=': 'op'},
            **{c: 'end' for c in notchar('=')},
        ),
        # Backreference: (/1,2/) vs (/) vs (/=)
        'op_lpar': dict(
            **{'/': 'op_def_slash'},
            **{c: 'end' for c in notchar('/')},
        ),
        'op_keyword': dict(
            **{'.': 'op'},
            **{c: 'op_keyword' for c in alpha},
        ),
        # This doesn't actually get used more than once, but it is correct.
        'cmt': dict(
            **{'\n': 'end'},
            **{c: 'cmt' for c in notchar('\n')},
        ),
    }

    def __init__(self):
        self.delim = None

    @property
    def prior_delim(self):
        return self.delim

    @prior_delim.setter
    def prior_delim(self, value):
        self.delim = value
    
    def parse(self, line):
        lexemes = []
        ileft = 0
    
        # Determine if this is a line-continued string
        if self.delim:
            # NOTE: This code block is a bit deceptive.
            #
            # It does construct the lexeme preceding a line-continued string,
            # but the DFA still iterates through these chars.  The updated
            # ileft ensures that they are omitted frmo the string lexeme.
            #
            # It is probably not very efficient, but seems faster than yet
            # another if-block inside of the DFA iteration.
    
            state = self.delim
            self.delim = None
    
            ileft = len(line) - len(line.lstrip())
            lexemes.append(line[:ileft])
    
            if line[ileft] == '&':
                lexemes.append('&')
                ileft += 1
        else:
            state = 'start'
    
        for idx, char in enumerate(line):
            try:
                state = Scanner.M[state][char]
            except KeyError:
                # Quoted strings may contain characters outside Fortran's
                # lexical character set, such as unicode text in messages.
                if state in ('str_a', 'str_q'):
                    pass
                elif state == 'str_a_lc':
                    state = 'str_a'
                elif state == 'str_q_lc':
                    state = 'str_q'
                else:
                    raise

            # Traversing these if-blocks is actually quite expensive!
            # By using this first "escape" block and by ordering these from
            # most to least likely, we can improve the speed by ~20%.

            if state not in (
                'end', 'cmt', 'op_def_slash', 'str_a_lc_end', 'str_q_lc_end', 'num_op_kw_end',
            ):
                continue

            elif (state == 'end'):
                lexemes.append(line[ileft:idx])
                ileft = idx

                # "Lookback" by re-evaluating char
                state = Scanner.M['start'][char]

            # Not a backtrack, but we can infer the lexeme immediately
            elif (state == 'cmt'):
                if line[-1] == '\n':
                    lexemes.append(line[ileft:len(line)-1])
                    ileft = len(line) - 1
                else:
                    lexemes.append(line[ileft:len(line)])
                    ileft = len(line)
                break

            # Backtracking cases
            # (Actually a lookahead!  Rewrite as a backreference?)
            elif state == 'op_def_slash':
                lookahead = line[idx+1:].strip()
                if lookahead and lookahead[0] == ')':
                    lexemes.append(line[ileft:idx])
                    ileft = idx
                    state = 'op'
                elif idx + 1 < len(line) and line[idx+1] in '=/':
                    lexemes.append(line[ileft:idx])
                    ileft = idx
                    state = 'op_slash'
                else:
                    state = 'op'


            elif state in ('str_a_lc_end', 'str_q_lc_end'):
                lc_tok = line.rindex('&')
                lexemes.append(line[ileft:lc_tok])
                ileft = lc_tok

                if (lc_tok + 1 < idx):
                    lexemes.append(line[ileft:lc_tok+1])
                    ileft = lc_tok + 1

                lexemes.append(line[ileft:idx])
                ileft = idx

                # XXX: make this more explicit (e.g. dict)
                self.delim = state[:5]

            elif state == 'num_op_kw_end':
                dec_tok = line[:idx].rindex('.')
                lexemes.append(line[ileft:dec_tok])
                ileft = dec_tok
                state = 'op'
    
        lexemes.append(line[ileft:])
    
        return lexemes
