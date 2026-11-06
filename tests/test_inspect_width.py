from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from inspect_width import inspect, classify, number

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / 'examples' / (name + '.json')).read_text(), parse_float=Decimal)


class WidthTest(unittest.TestCase):
    def test_nominal(self):
        out = inspect(load('nominal'))
        self.assertEqual((out['scale_mm_per_px'], out['offset_mm'], out['check_residual_mm']),
                         ('0.100000', '-0.200000', '0.010000'))
        self.assertEqual([(p['status'], p['width_mm']) for p in out['parts']],
                         [('accept', '15.040000'), ('review', '15.080000'),
                          ('reject', '15.200000'), ('hold', None)])
        self.assertEqual(out['parts'][-1]['reason'], 'outside_calibration')

    def test_shift_blocks_apparently_good_part(self):
        out = inspect(load('shifted-check'))
        self.assertEqual((out['check'], out['check_residual_mm']), ('fail', '0.050000'))
        self.assertEqual(out['parts'][0],
                         dict(id='center', status='hold', reason='check_failed', width_mm=None))

    def test_equality_and_display_rounding(self):
        out = inspect(load('boundaries'))
        self.assertEqual((out['check'], out['check_residual_mm']), ('pass', '-0.020000'))
        self.assertEqual([p['status'] for p in out['parts']], ['accept', 'accept', 'review', 'reject'])
        self.assertEqual(out['parts'][-2]['width_mm'], out['parts'][-1]['width_mm'])

    def test_interval_oracle_on_integer_grid(self):
        for width in range(-12, 13):
            for half in range(7):
                candidates = set(range(width - half, width + half + 1))
                tolerance = set(range(-5, 9))
                expected = ('accept' if candidates <= tolerance else
                            'reject' if candidates.isdisjoint(tolerance) else 'review')
                self.assertEqual(classify(width, half, -5, 8), expected)

    def test_wide_interval_enveloping_tolerance_is_review(self):
        self.assertEqual(classify(Fraction(15), Fraction(1), Fraction(149, 10),
                                  Fraction(151, 10)), 'review')

    def test_bad_calibration_rejected(self):
        for bad in (102, 101):
            cfg = load('nominal')
            cfg['calibration'][1]['span_px'] = bad
            with self.assertRaisesRegex(ValueError, 'increasing widths'):
                inspect(cfg)

    def test_check_must_be_separate_interior_span(self):
        cfg = load('nominal')
        cfg['check']['span_px'] = 102
        with self.assertRaisesRegex(ValueError, 'interior'):
            inspect(cfg)

    def test_bad_allowance_and_duplicate_id(self):
        for key, value, message in [('allowance_mm', -1, 'nonnegative'),
                                     ('parts', [dict(id='a', span_px=150)] * 2, 'unique')]:
            cfg = load('nominal')
            cfg[key] = value
            with self.assertRaisesRegex(ValueError, message):
                inspect(cfg)

    def test_input_numbers(self):
        self.assertEqual(number('0.000001'), Fraction(1, 1000000))
        for value in (True, 'NaN', 'Infinity', '0.0000001', 1000001):
            with self.assertRaises(ValueError):
                number(value)

    def test_cli_exit_codes_and_json(self):
        command = [sys.executable, str(ROOT / 'inspect_width.py')]
        ok = subprocess.run(command + [str(ROOT / 'examples/nominal.json')], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0)
        self.assertEqual(json.loads(ok.stdout)['check'], 'pass')
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'bad.json'
            bad.write_text('{"calibration": []}')
            result = subprocess.run(command + [str(bad)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertIn('exactly two calibration rows', result.stderr)


if __name__ == '__main__':
    unittest.main()
