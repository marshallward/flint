"""Macro expansion must improve analysis without rewriting source invocations."""
import io
import tempfile
import unittest
from pathlib import Path

import flint
from flint.calls import get_callable_symbols
from flint.docgen.model import iter_module_documentation
from flint.docgen.references import ReferenceIndex
from flint.formatting.spacing import render
from flint.lexer import Lexer
from flint.token import semantic_tokens


class FunctionMacroTests(unittest.TestCase):
    def check(self, source, expected, includes=()):
        statements = list(Lexer(io.StringIO(source), include_paths=includes))
        self.assertEqual([''.join(semantic_tokens(stmt)) for stmt in statements], expected)
        self.assertEqual(render(statements), source)
        return statements

    def test_mom_dimensions_and_real_calls(self):
        statements = self.check(
            '#define SZI_(G) G%isd:G%ied\n'
            '#define ALLOC_(x) allocate(x)\n'
            'ALLOC_(a(SZI_(grid), extent()))\n',
            ['allocate(a(grid%isd:grid%ied,extent()))'])
        self.assertNotIn('szi_', get_callable_symbols(statements[0], []))
        self.assertIn('extent', get_callable_symbols(statements[0], []))

    def test_arguments_nested_commas_strings_and_continuations(self):
        self.check('#define PAIR(a,b) a+b\n'
                   'x = PAIR(f(1, 2), & ! keep this comment\n'
                   '         & g("a,b"))\n', ['x=f(1,2)+g("a,b")'])

    def test_recursive_arguments_and_object_chains(self):
        self.check('#define N 3\n#define EXTENT N\n'
                   '#define DOUBLE(x) (x+x)\n'
                   'x = DOUBLE(DOUBLE(EXTENT))\n', ['x=((3+3)+(3+3))'])

    def test_object_alias_to_function_macro(self):
        self.check('#define SIZE(G) G%lo:G%hi\n#define ALIAS SIZE\n'
                   'x = ALIAS(grid)\n', ['x=grid%lo:grid%hi'])

    def test_recursion_stops(self):
        self.check('#define A B\n#define B A\n'
                   '#define SELF(x) SELF(x)\n'
                   'x = A + SELF(1)\n', ['x=a+self(1)'])

    def test_empty_zero_argument_and_unused_argument(self):
        self.check('#define EMPTY(x)\n#define VALUE() 7\n#define FIXED(x) 4\n'
                   'x = VALUE() EMPTY(unused()) + FIXED(unused())\n', ['x=7+4'])

    def test_bare_names_and_case_sensitivity(self):
        self.check('#define SIZE(x) x%size\n'
                   'x = SIZE + size(g) + SIZE(g)\n', ['x=size+size(g)+g%size'])

    def test_definition_continuation_and_timing(self):
        self.check('#define SIZE(G) \\\n'
                   '  G%lo:G%hi\n'
                   'x = SIZE(grid)\n'
                   '#undef SIZE\n'
                   'y = SIZE(grid)\n', ['x=grid%lo:grid%hi', 'y=size(grid)'])

    def test_function_macro_conditionals_and_undef(self):
        self.check('#define F(x) x\n'
                   '#ifdef F\na=1\n#else\na=0\n#endif\n'
                   '#if defined(F)\nb=1\n#endif\n'
                   '#ifndef F\nb=0\n#endif\n'
                   '#if F\nc=0\n#else\nc=1\n#endif\n'
                   '#undef F\n#if defined(F)\nd=0\n#else\nd=1\n#endif\n',
                   ['a=1', 'b=1', 'c=1', 'd=1'])

    def test_redefinition_between_macro_kinds(self):
        self.check('#define F(x) x\nx=F(2)\n'
                   '#define F 3\ny=F\n'
                   '#define F(x) x+1\nz=F(4)\n', ['x=2', 'y=3', 'z=4+1'])

    def test_nested_headers_share_function_macros(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'outer.h').write_text('#include "inner.h"\n')
            (root / 'inner.h').write_text('#define SIZE(G) G%lo:G%hi\n')
            self.check('#include "outer.h"\nx=SIZE(grid)\n', ['x=grid%lo:grid%hi'], [tmp])

    def test_invalid_arity_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, 'expects 2 arguments, got 1'):
            list(Lexer(io.StringIO('#define PAIR(a,b) a+b\nx=PAIR(1)\n')))

    def test_macro_generated_calls_keep_semantic_names_in_documentation(self):
        text = ('#define DO_WORK(x) call work(x)\n'
                'module demo\ncontains\nsubroutine run()\nDO_WORK(1)\n'
                'end subroutine run\nsubroutine work(x)\ninteger :: x\n'
                'end subroutine work\nend module demo\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            project = flint.parse(str(path))
        self.assertEqual(render(project.sources[0].statements), text)
        modules = tuple(iter_module_documentation(project))
        index = ReferenceIndex(modules)
        self.assertEqual(index.calls['demo::run'][0].label, 'work')
        self.assertEqual(index.calls['demo::run'][0].target, 'demo::work')


if __name__ == '__main__':
    unittest.main()
