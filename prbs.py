from operator import xor, add
from functools import reduce

from migen import *


class Generator(Module):
    def __init__(self, n_out, n_state=23, taps=[17, 22]):
        self.o = Signal(n_out)

        # # #

        state = Signal(n_state, reset=1)
        curval = [state[i] for i in range(n_state)]
        curval += [0]*(n_out - n_state)
        for i in range(n_out):
            nv = reduce(xor, [curval[tap] for tap in taps])
            curval.insert(0, nv)
            curval.pop()

        self.sync += [
            state.eq(Cat(*curval[:n_state])),
            self.o.eq(Cat(*curval))
        ]


class Checker(Module):
    def __init__(self, n_in, n_state=23, taps=[17, 22]):
        self.i = Signal(n_in)
        self.errors = Signal(n_in)
        self.error_count = Signal(max=n_in+1)

        # # #

        state = Signal(n_state, reset=1)
        curval = [state[i] for i in range(n_state)]
        for i in reversed(range(n_in)):
            correctv = reduce(xor, [curval[tap] for tap in taps])
            self.sync += self.errors[i].eq(self.i[i] != correctv)
            curval.insert(0, self.i[i])
            curval.pop()

        self.sync += state.eq(Cat(*curval[:n_state]))
        self.comb += self.error_count.eq(
            reduce(add, [self.errors[i] for i in range(n_in)]))
