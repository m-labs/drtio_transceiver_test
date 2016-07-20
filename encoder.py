from migen import *


comma = 0b1101010100


class WordAligner(Module):
    def __init__(self, words_per_cycle=1):
        self.input = Signal(10*words_per_cycle)
        self.output = Signal(10*words_per_cycle)

        self.comma_found = Signal()
        self.position = Signal(max=10*words_per_cycle)

        # # #

        buf = Signal(2*10*words_per_cycle)
        self.sync += buf.eq(Cat(buf[10*words_per_cycle:], self.input))

        self.sync += self.comma_found.eq(0)
        for i in range(10*words_per_cycle):
            self.sync += If(buf[i:i+10] == comma,
                  self.comma_found.eq(1),
                  self.position.eq(i)
            )
        self.sync += self.output.eq(buf >> self.position)


def test_word_aligner():
    dut = WordAligner(2)

    def tb():
        for align in range(20):
            while True:
                for i in range(2):
                    yield dut.input.eq(comma << align)
                    yield
                    if align > 10:
                        yield dut.input.eq(comma >> (20-align))
                    yield
                if (yield dut.comma_found):
                    print(align, (yield dut.position))
                    break

    run_simulation(dut, tb())


if __name__ == "__main__":
    test_word_aligner()
