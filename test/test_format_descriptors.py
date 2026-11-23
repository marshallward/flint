"""FORMAT repeat counts must not commit the scanner to real exponents."""
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.calls import get_callable_symbols
from flint.formatting.rules import select_rules
from flint.formatting.runner import check_spacing
from flint.lexer import Lexer
from flint.scanner import Scanner


class FormatDescriptorTests(unittest.TestCase):
    def test_repeat_count_and_descriptor_boundaries(self):
        for descriptor in ('dt', 'DT', 'en12', 'es12', 'EN12', 'ES12'):
            text = '2' + descriptor + '('
            self.assertEqual(Scanner().parse(text), ['2', descriptor, '('])
        for number in ('2d3', '2D-3', '2e+3', '2.0e3'):
            self.assertEqual(Scanner().parse(number), [number])
        self.assertEqual(Scanner().parse('1.eq.2'), ['1', '.eq.', '2'])

    def test_formats_preserve_source_and_are_not_calls(self):
        formats = (
            '50 format(2dt(3),1x,i0)',
            '50 format(2DT"Mixed"(1,-2),1x,i0)',
            "50 format(2dt'it''s'(3),2en12.3,2es12.3)",
            '50 format(1x,2(dt\'k\'(4),:,"|"))',
            '50 format(2dt&\n&(3),1x,i0)',
        )
        for line in formats:
            with self.subTest(line=line), tempfile.TemporaryDirectory() as tmp:
                stmt = next(Lexer(io.StringIO(line + '\n')))
                self.assertEqual(stmt.source_text(), line + '\n')
                self.assertEqual(get_callable_symbols(stmt, []), [])
                text = 'program test\n' + line + '\nend program\n'
                path = Path(tmp) / 'test.f90'
                path.write_text(text, encoding='utf-8', newline='')
                project = flint.parse(str(path))
                self.assertEqual(project.sources[0].source_text(), text)
                self.assertEqual(list(check_spacing(project, select_rules().values())), [])
