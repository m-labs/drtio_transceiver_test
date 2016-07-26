import unittest

from migen import *

from prbs import PRBSGenerator, PRBSChecker


def prbs_genenerate(dw, length):
    dut = PRBSGenerator(dw)
    output = []
    def pump():
        yield
        for _ in range(length):
            yield
            output.append((yield dut.o))
    run_simulation(dut, pump())
    return output


def prbs_check(dw, seq):
    error_count = 0
    dut = PRBSChecker(dw)
    def pump():
        nonlocal error_count
        for w in seq:
            yield dut.i.eq(w)
            yield
            error_count += (yield dut.error_count)
    run_simulation(dut, pump())
    return error_count


class TestPRBS(unittest.TestCase):
    dw = 16

    @classmethod
    def setUpClass(cls):
        cls.sequence = prbs_genenerate(cls.dw, 500)

    def test_no_error(self):
        self.assertEqual(prbs_check(self.dw, self.sequence), 0)

    def test_one_error(self):
        err_sequence = list(self.sequence)
        err_sequence[42] ^= 0x0100
        detected_error_count = prbs_check(self.dw, err_sequence)
        self.assertGreater(detected_error_count, 0)
        self.assertLess(detected_error_count, 23)
