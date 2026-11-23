"""flint Line class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import itertools
from flint.endlines import is_endline


class Lines(object):
    """Iterator which reconstructs lines from lists of statements.

    This is more of a proof-of-concept than for actual use; it's much more
    efficient to just open the file!
    """
    def __init__(self, statements):
        self.statements = iter(statements)

        # Initialize the buffer, including the head liminals
        next_stmt = next(self.statements)

        # Create a new list with semantic and liminal tokens in a single list
        self.buffer = list(next_stmt[0].head)
        for tok in next_stmt:
            self.buffer += tok.pp if hasattr(tok, 'pp') else [tok]
            self.buffer += tok.tail

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        while not any(is_endline(item) for item in self.buffer):
            try:
                next_stmt = next(self.statements)
            except StopIteration:
                # NOTE: This occurs if a source does not have a final endline.

                # The buffer has been depleted and iteration is complete.
                if not self.buffer:
                    raise

                # Return the buffer
                lines, self.buffer = self.buffer, []
                return lines

            for tok in next_stmt:
                self.buffer += tok.pp if hasattr(tok, 'pp') else [tok]
                self.buffer += tok.tail

        idx = next(i for i, item in enumerate(self.buffer) if is_endline(item))
        line, self.buffer = self.buffer[:idx], self.buffer[idx+1:]

        return line
