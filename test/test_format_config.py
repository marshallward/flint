"""Configuration discovery, validation, precedence, and rule integration."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import flint
from flint.cli import parse
from flint.formatting.config import configured_rules, load_config
from flint.formatting.runner import check_spacing
from flint.tools.format import format_statements


class FormatConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'flint.toml'
        self.source = self.root / 'demo.F90'

    def run_format(self, **options):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = format_statements([str(self.source)], config=self.config, **options)
        return status, output.getvalue()

    def test_discovery_nearest_and_explicit(self):
        child = self.root / 'child'
        child.mkdir()
        self.config.write_text('[format]\nrules = ["indentation"]\n')
        self.assertEqual(load_config(start=child)['rules'], ['indentation'])
        (child / 'flint.toml').write_text('[format]\nrules = []\n')
        self.assertEqual(load_config(start=child)['rules'], [])
        self.assertEqual(load_config(self.config)['rules'], ['indentation'])

    def test_default_width_is_four_and_project_can_override(self):
        self.config.write_text('')
        text = 'subroutine demo()\n    call task()\nend subroutine demo\n'
        self.source.write_text(text)
        self.assertEqual(self.run_format(), (0, ''))
        self.source.write_text(text.replace('    call', '  call'))
        self.assertEqual(self.run_format()[0], 1)
        self.config.write_text('[format.indentation]\nwidth = 2\n')
        self.assertEqual(self.run_format(), (0, ''))

    def test_invalid_config_rejected_before_parsing(self):
        examples = [
            '[format', '[other]\nx = 1', '[format]\nrules = ["unknown"]',
            '[format]\nrules = "indentation"', '[format]\nexclude = [1]',
            '[format.unknown]', '[format.indentation]\nwidht = 4',
            '[format.indentation]\nwidth = true', '[format.indentation]\nwidth = 0',
            '[format.indentation]\ncontinuation-width = -1',
            '[format.assignment-spacing]\nstrict = "yes"',
        ]
        with patch.object(flint, 'parse') as parsing:
            for text in examples:
                with self.subTest(text=text):
                    self.config.write_text(text)
                    with self.assertRaises(ValueError):
                        self.run_format()
            self.config.unlink()
            with self.assertRaises(ValueError):
                self.run_format()
            parsing.assert_not_called()

    def test_per_rule_strict_and_boolean_cli_override(self):
        self.config.write_text('''[format]
rules = ["assignment-spacing", "operator-spacing"]
[format.assignment-spacing]
strict = true
[format.operator-spacing]
strict = false
''')
        text = 'subroutine demo()\n  x  =  a  +  b\nend subroutine demo\n'
        self.source.write_text(text)
        self.assertEqual(self.run_format()[0], 1)
        with patch('sys.argv', ['flint', 'format', str(self.source), '--config',
                                str(self.config), '--no-strict']):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(parse(), 0)
        self.run_format(write=True)
        self.assertEqual(self.source.read_text(), text.replace('x  =  a', 'x = a'))

    def test_independent_widths_and_module_contents(self):
        self.config.write_text('''[format]
rules = ["indentation"]
[format.indentation]
width = 4
module-contents = true
continuation-width = 6
declaration-continuation-width = 3
''')
        self.source.write_text('''module demo
    real :: &
       x
contains
    subroutine work()
        call task(1, &
              2)
    end subroutine work
end module demo
''')
        self.assertEqual(self.run_format(), (0, ''))
        self.assertEqual(self.run_format(indent=2)[0], 1)
        status, output = self.run_format(strict=True)
        self.assertEqual(status, 1)
        self.assertIn('at least 10 spaces', output)

    def test_rule_selection_and_callable_list_override(self):
        self.config.write_text('''[format]
rules = ["callable-comma-spacing"]
[format.callable-comma-spacing]
excluded-functions = ["max"]
''')
        self.source.write_text('subroutine demo()\n  x=max(a,b)\nend subroutine demo\n')
        self.assertEqual(self.run_format(), (0, ''))
        self.assertEqual(self.run_format(excluded_functions=[])[0], 1)
        self.assertEqual(self.run_format(only=['assignment-spacing'])[0], 1)
        self.assertEqual(self.run_format(skip=['callable-comma-spacing']), (0, ''))

    def test_config_exclusions_relative_to_config_file(self):
        self.config.write_text('[format]\nexclude = ["ignored"]\n')
        ignored = self.root / 'ignored'
        ignored.mkdir()
        (ignored / 'bad.F90').write_text('subroutine demo()\nx=1\nend subroutine demo\n')
        original_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            for source in ('.', str(self.root)):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(format_statements([source]), 0)
                    self.assertEqual(format_statements([source], excludes=[]), 1)
        finally:
            os.chdir(original_cwd)

    def test_python_api_reuses_project_without_mutating_settings(self):
        self.source.write_text('subroutine demo()\n  x=1\nend subroutine demo\n')
        settings = {'rules': ['assignment-spacing'], 'assignment-spacing': {'strict': True}}
        checks, diagnostics = configured_rules(settings, strict=False)
        project = flint.parse(str(self.source))
        self.assertEqual(len(list(check_spacing(project, checks.values()))), 1)
        self.assertEqual(diagnostics, {})
        self.assertTrue(settings['assignment-spacing']['strict'])
