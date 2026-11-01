"""flint Variable class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.document import Document
from flint.declarations import declared_entities
from flint.documentation import declaration_comments, entity_comments
from flint.locations import statement_locations


class Variable(object):

    intrinsic_types = [
        'integer',
        'real',
        'double',   # double precision
        'complex',
        'character',
        'logical',
    ]

    def __init__(self, name, vtype):
        self.name = name
        self.type = vtype
        self.intent = None
        self.dimension = None

        self.attributes = []
        self.refs = 0

        self.stmt = None
        self.doc = Document()

    @classmethod
    def from_token(cls, token, vtype, intent=None, dimension=None, stmt=None):
        variable = cls(token, vtype)
        variable.intent = intent
        variable.dimension = dimension
        variable.stmt = stmt
        return variable

    @staticmethod
    def dimension_from_tokens(tokens):
        par_count = 1
        rank = 1
        for tok in tokens:
            if tok == '(':
                par_count += 1
            elif tok == ')':
                par_count -= 1
            elif tok == ',' and par_count == 1:
                rank += 1

            if par_count == 0:
                return rank

        return rank

    @property
    def is_array(self):
        return self.dimension is not None

    @property
    def declaration(self):
        """Source entity view, or None for an unsupported declaration.

        Computed on demand so ordinary parsing retains no source-view cache.
        """
        if self.stmt is None:
            return None
        entities = declared_entities(self.stmt)
        if entities is not None:
            return next((entity for entity in entities if entity.name is self.name), None)
        return None

    @property
    def declaration_tokens(self):
        """Tokens of this entity, including shape/initializer, or None."""
        entity = self.declaration
        if entity is None:
            return None
        return tuple(self.stmt[entity.span[0]:entity.span[1]])

    @property
    def location(self):
        """Displayed name-token location, or None if no physical span exists."""
        if self.stmt is not None:
            return next((location for location in statement_locations(self.stmt)
                         if location.token is self.name), None)
        return None

    @property
    def documentation(self):
        """Associated CommentBlocks, or None when association is unsupported.

        Empty means a recognized declaration with no associated comments.
        Documentation validity and conflicting blocks remain caller policy.
        """
        if self.stmt is None:
            return None
        entities = declared_entities(self.stmt)
        if entities is None:
            return None
        entity = next((entity for entity in entities if entity.name is self.name), None)
        if entity is None:
            return None
        return entity_comments(entity, declaration_comments(self.stmt, entities))
