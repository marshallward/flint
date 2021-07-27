"""flint Line class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import itertools

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
        self.buffer = next_stmt[0].head + [
            tok for tok in itertools.chain(
                *([t] + t.tail for t in next_stmt)
            )
        ]

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        while '\n' not in self.buffer:
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

            self.buffer += [
                tok for tok in itertools.chain(
                    *([t] + t.tail for t in next_stmt)
                )
            ]

        idx = self.buffer.index('\n')
        line, self.buffer = self.buffer[:idx], self.buffer[idx+1:]

        return line
