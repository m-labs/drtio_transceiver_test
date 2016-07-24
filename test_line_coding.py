import unittest
import random
from collections import namedtuple

from migen import *

import line_coding


Control = namedtuple("Control", "value")


def encode_sequence(seq):
    output = []

    dut = line_coding.Encoder()
    def pump():
        for w in seq:
            if isinstance(w, Control):
                yield dut.k[0].eq(1)
                yield dut.d[0].eq(w.value)
            else:
                yield dut.k[0].eq(0)
                yield dut.d[0].eq(w)
            yield
            output.append((yield dut.output[0]))
        for _ in range(2):
            yield
            output.append((yield dut.output[0]))
    run_simulation(dut, pump())

    return output[2:]


class TestLineCoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prng = random.Random(42)
        cls.input_sequence = [Control((1 << 5) | 28)]*2 
        cls.input_sequence += [prng.randrange(256) for _ in range(1000)]
        cls.output_sequence = encode_sequence(cls.input_sequence)

    def test_comma(self):
        self.assertEqual(self.output_sequence[0], 0b0011111001)
        self.assertEqual(self.output_sequence[1], 0b1100000110)

    def test_running_disparity(self):
        rd = -1
        for w in self.output_sequence:
            rd += line_coding.disparity(w, 10)
            self.assertIn(rd, {-1, 1})

    def test_no_spurious_commas(self):
        for w1, w2 in zip(self.output_sequence[2:], self.output_sequence[3:]):
            for shift in range(10):
                cw = (w1 << shift) | (w2 >> (10-shift))
                self.assertNotIn(cw, {0b0011111001, 0b1100000110,   # K28.1
                                      0b0011111010, 0b1100000101,   # K28.5
                                      0b0011111000, 0b1100000111})  # K28.7
