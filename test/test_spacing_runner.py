import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import flint
from flint.formatting.runner import check_spacing, report_spacing, run_spacing
from flint.formatting.spacing import spacing_edits


def around(symbol, space=' '):
    def prepare(source):
        def collect(statement):
            for token in statement:
                if token == symbol:
                    yield from spacing_edits(token, before=space, after=space)
        return collect
    return prepare


class TestSpacingRunner(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'example.f90'
        self.text = 'subroutine demo\nreal :: x\nx=1+2; x=3+4\nend subroutine demo\n'
        self.path.write_text(self.text)
        self.project = flint.parse(str(self.path))

    def test_combines_checks_without_reparse_or_mutation(self):
        statements = self.project.sources[0].statements
        before = [(str(t), id(t.head), tuple(t.head), id(t.tail), tuple(t.tail))
                  for s in statements for t in s]
        with patch('flint.formatting.runner.flint.parse', side_effect=AssertionError('reparse')):
            results = list(check_spacing(self.project, (around('='), around('+'))))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_spacing(project=self.project, checks=(around('='),)), 1)
        self.assertEqual(len(results), 1)
        self.assertIn('x = 1 + 2; x = 3 + 4', results[0].formatted)
        self.assertEqual(before, [(str(t), id(t.head), tuple(t.head), id(t.tail), tuple(t.tail))
                                  for s in statements for t in s])
        self.assertEqual(self.path.read_text(), self.text)

    def test_parse_once_and_prepare_once_per_source(self):
        prepared = []
        def prepare(source):
            prepared.append(source)
            return around('=')(source)
        with patch('flint.formatting.runner.flint.parse', return_value=self.project) as parse:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_spacing([self.path], checks=(prepare, around('+'))), 1)
        parse.assert_called_once_with(str(self.path), excludes=())
        self.assertEqual(prepared, self.project.sources)

    def test_shared_gap_conflicts_and_identical_proposals(self):
        results = list(check_spacing(self.project, (around('='), around('='))))
        self.assertEqual(len(results), 1)
        with self.assertRaisesRegex(ValueError, 'Conflicting spacing edits'):
            list(check_spacing(self.project, (around('='), around('=', '  '))))

    def test_report_deduplicates_physical_lines_and_write_status(self):
        results = list(check_spacing(self.project, (around('='), around('+'))))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = report_spacing(results, report=True)
        self.assertEqual(status, 1)
        self.assertEqual(output.getvalue(), f'{self.path}:3: x=1+2; x=3+4\n')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(report_spacing(results, write=True, diff=True), 0)
        self.assertIn(f'--- {self.path}', output.getvalue())
        self.assertIn('+x = 1 + 2; x = 3 + 4', output.getvalue())
        self.assertEqual(self.path.read_text(), results[0].formatted)

    def test_empty_checks_and_ambiguous_input(self):
        self.assertEqual(list(check_spacing(self.project, [])), [])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(report_spacing([]), 0)
        self.assertEqual(output.getvalue(), '')
        with self.assertRaises(ValueError):
            run_spacing([self.path], project=self.project, checks=())


if __name__ == '__main__':
    unittest.main()
