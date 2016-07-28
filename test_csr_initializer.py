import unittest

from migen import *

from csr_initializer import *


class TestCSRInitializer(unittest.TestCase):
    def test_csr_initializer(self):
        program = [
            InstWrite(6, 0x3e),
            InstWrite(5, 0x10),
            InstReadUntil0(4, 0x03),
            InstWrite(1, 0x76),
            InstReadUntil1(1, 7),
            InstReadUntil0(12, 0),
            InstWrite(3, 0x24),
            InstEnd()
        ]
        dut = CSRInitializer(program)

        def wait():
            timeout = 0
            while not ((yield dut.bus.cyc) and (yield dut.bus.stb)):
                timeout += 1
                assert timeout < 20
                yield
            return (
                (yield dut.bus.we),
                (yield dut.bus.adr),
                (yield dut.bus.dat_w))

        def ack(data=None):
            if data is not None:
                yield dut.bus.dat_r.eq(data)
            yield dut.bus.ack.eq(1)
            yield
            yield dut.bus.ack.eq(0)
            yield

        def check():
            for inst in program:
                if isinstance(inst, InstWrite):
                    we, a, d = yield from wait()
                    self.assertTrue(we)
                    self.assertEqual(a, inst.address)
                    self.assertEqual(d, inst.data)
                    yield from ack()
                elif isinstance(inst, (InstReadUntil0, InstReadUntil1)):
                    pos_val = 1 << inst.bsel
                    if isinstance(inst, InstReadUntil0):
                        pos_val = ~pos_val & 0xff
                        neg_val = 0xff
                    else:
                        neg_val = 0x00
                    for _ in range(3):
                        we, a, d = yield from wait()
                        self.assertFalse(we)
                        self.assertEqual(a, inst.address)
                        yield from ack(neg_val)
                    we, a, d = yield from wait()
                    self.assertFalse(we)
                    self.assertEqual(a, inst.address)
                    yield from ack(pos_val)
                elif isinstance(inst, InstEnd):
                    for _ in range(20):
                        self.assertFalse(((yield dut.bus.cyc)
                                          and (yield dut.bus.stb)))
                    return
                else:
                    raise ValueError

        run_simulation(dut, check())
