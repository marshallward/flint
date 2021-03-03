class Token(str):
    def __new__(cls, value=''):
        tok = str.__new__(cls, value)
        tok.tail = []
        return tok

    #def __str__(self):
    #    return str(self.lower())

    def __eq__(self, other):
        return self.lower() == other.lower()

    def __hash__(self):
        return hash(str(self).lower())
