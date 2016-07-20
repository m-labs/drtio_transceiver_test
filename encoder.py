from migen import *


comma = 0b1101010100


class WordAligner(Module):
    def __init__(self, words_per_cycle=1):
        self.input = Signal(10*words_per_cycle)
        self.output = Signal(10*words_per_cycle)

        self.comma_found = Signal()
        self.position = Signal(max=10*words_per_cycle)

        # # #

        buf = Signal(10*(words_per_cycle + 1))
        self.sync += buf.eq(Cat(self.input, buf[:10]))

        self.sync += self.comma_found.eq(0)
        for i in range(10*words_per_cycle):
            self.sync += If(buf[i:i+10] == comma,
                  self.comma_found.eq(1),
                  self.position.eq(i)
            )
        self.sync += self.output.eq(buf >> self.position)
