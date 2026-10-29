import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(1, '../')
import flint  # noqa: E402
from report_callable_comma_spacing import (  # noqa: E402
    format_statements,
    main,
    statement_contexts,
)


def format_source(text, **options):
    formatted, _ = format_source_with_changes(text, **options)
    return formatted


def format_source_with_changes(text, **options):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'test.F90'
        path.write_text(text)

        project = flint.parse(str(path))
        source = project.sources[0]
        formatted, changes = format_statements(
            path,
            source.statements,
            statement_contexts(source),
            text.splitlines(),
            **options,
        )

    return formatted, changes


class TestCallableCommaSpacing(unittest.TestCase):
    def test_array_constructor_commas_are_not_changed(self):
        source = '''subroutine demo(a, b)
  real :: a, b
  call f((/1,2,3/),a,b)
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(a, b)
  real :: a, b
  call f((/1,2,3/), a, b)
end subroutine demo
''',
        )

    def test_component_reference_commas_are_not_changed(self):
        source = '''subroutine demo(CS, I, J)
  integer :: I, J
  if (CS%umask(I,J) == 3) call f(I,J)
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(CS, I, J)
  integer :: I, J
  if (CS%umask(I,J) == 3) call f(I, J)
end subroutine demo
''',
        )

    def test_write_control_commas_are_not_changed(self):
        source = '''subroutine demo(root, outunit, id, timestep)
  if (root) write(outunit,*) "BEGIN CHECKSUM:: ", id, timestep
end subroutine demo
'''

        self.assertEqual(format_source(source), source)

    def test_continuation_comma_spacing_is_tolerated(self):
        source = '''subroutine demo(a, b, c)
  call f(a, b, &
         c)
end subroutine demo
'''

        self.assertEqual(format_source(source), source)

    def test_continuation_comma_same_line_spacing_is_changed(self):
        source = '''subroutine demo(a, b, c)
  call f(a, b,     &
         c)
end subroutine demo
'''

        self.assertEqual(
            format_source(source, strict=True),
            '''subroutine demo(a, b, c)
  call f(a, b, &
         c)
end subroutine demo
''',
        )

    def test_only_same_line_callable_comma_spacing_is_changed(self):
        source = '''subroutine demo(a, b, c)
  call f(a,  b, &
         c)
end subroutine demo
'''

        self.assertEqual(
            format_source(source, strict=True),
            '''subroutine demo(a, b, c)
  call f(a, b, &
         c)
end subroutine demo
''',
        )

    def test_reports_changed_continuation_line(self):
        source = '''subroutine demo(a, b, c, d)
  call f(a, b, &
         c,  d)
end subroutine demo
'''

        _, changes = format_source_with_changes(source, strict=True)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].line_number, 3)
        self.assertEqual(changes[0].original, '         c,  d)')

    def test_non_strict_alignment_spaces_are_preserved(self):
        source = '''subroutine demo(a, b, c)
  call f(a,   b,    c)
end subroutine demo
'''
        formatted, changes = format_source_with_changes(source)
        self.assertEqual(formatted, source)
        self.assertEqual(changes, [])
        self.assertEqual(
            format_source(source, strict=True),
            source.replace('a,   b,    c', 'a, b, c'),
        )

    def test_non_strict_still_fixes_missing_same_line_spaces(self):
        source = '''subroutine demo(a, b, c)
  call f(a,b,    c)
end subroutine demo
'''
        self.assertEqual(format_source(source), source.replace('f(a,b', 'f(a, b'))

    def test_continuation_spacing_depends_on_strictness(self):
        for gap in ('', ' ', '    '):
            with self.subTest(gap=gap):
                source = f'''subroutine demo(a, b, c)
  call f(a, b,{gap}&
         c)
end subroutine demo
'''
                formatted, changes = format_source_with_changes(source)
                self.assertEqual(formatted, source)
                self.assertEqual(changes, [])
                self.assertEqual(
                    format_source(source, strict=True),
                    source.replace(f'b,{gap}&', 'b, &'),
                )

    def test_continuation_comment_is_preserved_in_both_modes(self):
        source = '''subroutine demo(a, b, c)
  call f(a,b,& ! retain this comment
       & c)
end subroutine demo
'''
        for strict in (False, True):
            with self.subTest(strict=strict):
                self.assertEqual(
                    format_source(source, strict=strict),
                    source.replace('f(a,b', 'f(a, b'),
                )

    def test_named_exclusions_are_case_insensitive_in_both_modes(self):
        source = '''subroutine demo(a, b, x)
  x = MAX(a,b) + mod(a,b) + min(a,b)
end subroutine demo
'''
        for strict in (False, True):
            with self.subTest(strict=strict):
                self.assertEqual(
                    format_source(
                        source, strict=strict, excluded_functions=('max', 'MOD'),
                    ),
                    source.replace('min(a,b)', 'min(a, b)'),
                )

    def test_intrinsics_are_not_excluded_by_default(self):
        source = '''subroutine demo(a, b, x)
  x = max(a,b) + mod(a,b)
end subroutine demo
'''
        self.assertEqual(format_source(source), source.replace('(a,b)', '(a, b)'))

    def test_excluded_parent_does_not_exclude_nested_calls(self):
        source = '''subroutine demo(a, b, c, x)
  x = max(mod(a,b),c)
end subroutine demo
'''
        self.assertEqual(
            format_source(source, excluded_functions=('max',)),
            source.replace('mod(a,b)', 'mod(a, b)'),
        )

    def test_excluded_inner_call_does_not_exclude_parent(self):
        source = '''subroutine demo(a, b, c, x)
  x = max(mod(a,b),c)
end subroutine demo
'''
        self.assertEqual(
            format_source(source, excluded_functions=('mod',)),
            source.replace('),c)', '), c)'),
        )

    def test_excluded_subroutine_name(self):
        source = '''subroutine demo(a, b)
  call f(a,b)
  call g(a,b)
end subroutine demo
'''
        self.assertEqual(
            format_source(source, excluded_functions=('f',)),
            source.replace('g(a,b)', 'g(a, b)'),
        )

    def test_cli_repeatable_exclusions_and_strict_write(self):
        source = '''subroutine demo(a, b, x)
  x = max(a,b) + mod(a,b) + min(a,   b)
end subroutine demo
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'test.F90'
            path.write_text(source)
            arguments = [
                'report_callable_comma_spacing.py', str(path), '--strict',
                '--exclude-function=max', '--exclude-function', 'mod', '--write',
            ]
            with patch.object(sys, 'argv', arguments):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
            self.assertEqual(path.read_text(), source.replace('min(a,   b)', 'min(a, b)'))


if __name__ == '__main__':
    unittest.main()
