# only K.28.y control symbols are supported

from migen import *


def disparity(word, nbits):
    n0 = 0
    n1 = 0
    for i in range(nbits):
        if word & (1 << i):
            n1 += 1
        else:
            n0 += 1
    return n1 - n0


def reverse_table(inputs, flips, nbits):
    outputs = [None]*2**nbits
    for i, (word, flip) in enumerate(zip(inputs, flips)):
        if outputs[word] is not None:
            raise ValueError
        outputs[word] = i
        if flip:
            word_n = ~word & (2**nbits-1)
            if outputs[word_n] is not None:
                raise ValueError
            outputs[word_n] = i
    return outputs

# 5b6b

table_5b6b = [
    0b100111,
    0b011101,
    0b101101,
    0b110001,
    0b110101,
    0b101001,
    0b011001,
    0b111000,
    0b111001,
    0b100101,
    0b010101,
    0b110100,
    0b001101,
    0b101100,
    0b011100,
    0b010111,
    0b011011,
    0b100011,
    0b010011,
    0b110010,
    0b001011,
    0b101010,
    0b011010,
    0b111010,
    0b110011,
    0b100110,
    0b010110,
    0b110110,
    0b001110,
    0b101110,
    0b011110,
    0b101011,    
]
table_5b6b_unbalanced = [bool(disparity(c, 6)) for c in table_5b6b]
table_5b6b_flip = list(table_5b6b_unbalanced)
table_5b6b_flip[7] = True

table_6b5b = reverse_table(table_5b6b, table_5b6b_flip, 6)

# 3b4b

table_3b4b = [
    0b1011,
    0b1001,
    0b0101,
    0b1100,
    0b1101,
    0b1010,
    0b0110,
    0b1110,  # primary D.x.7
]
table_3b4b_unbalanced = [bool(disparity(c, 4)) for c in table_3b4b]
table_3b4b_flip = list(table_3b4b_unbalanced)
table_3b4b_flip[3] = True

table_4b3b = reverse_table(table_3b4b, table_3b4b_flip, 4)
# alternative D.x.7
table_4b3b[0b0111] = 0b0111
table_4b3b[0b1000] = 0b0111


class SingleEncoder(Module):
    def __init__(self):
        self.d = Signal(8)
        self.k = Signal()
        self.disp_in = Signal()

        self.output = Signal(10)
        self.disp_out = Signal()

        # # #

        # stage 1: 5b/6b and 3b/4b encoding
        code5b = self.d[:5]
        code6b = Signal(6)
        code6b_unbalanced = Signal()
        code6b_flip = Signal()
        self.sync += [
            If(self.k,
                code6b.eq(0b001111),
                code6b_unbalanced.eq(1),
                code6b_flip.eq(1)
            ).Else(
                code6b.eq(Array(table_5b6b)[code5b]),
                code6b_unbalanced.eq(Array(table_5b6b_unbalanced)[code5b]),
                code6b_flip.eq(Array(table_5b6b_flip)[code5b])
            )
        ]

        code3b = self.d[5:]
        code4b = Signal(4)
        code4b_unbalanced = Signal()
        code4b_flip = Signal()
        self.sync += [
            code4b.eq(Array(table_3b4b)[code3b]),
            code4b_unbalanced.eq(Array(table_3b4b_unbalanced)[code3b]),
            If(self.k,
                code4b_flip.eq(1)
            ).Else(
                code4b_flip.eq(Array(table_3b4b_flip)[code3b])
            )
        ]

        alt7_rd0 = Signal()  # if disparity is -1, use alternative D.x.7
        alt7_rd1 = Signal()  # if disparity is +1, use alternative D.x.7
        self.sync += [
            alt7_rd0.eq(0),
            alt7_rd1.eq(0),
            If(code3b == 7,
                If((code5b == 17) | (code5b == 18) | (code5b == 20),
                    alt7_rd0.eq(1)),
                If((code5b == 11) | (code5b == 13) | (code5b == 14),
                    alt7_rd1.eq(1)),
            )
        ]

        # stage 2 (combinatorial): disparity control
        output_6b = Signal(6)
        disp_inter = Signal()
        self.comb += [
            disp_inter.eq(self.disp_out ^ code6b_unbalanced),
            If(self.disp_in & code6b_flip,
                output_6b.eq(~code6b)
            ).Else(
                output_6b.eq(code6b)
            )
        ]

        output_4b = Signal(4)
        self.comb += [
            # note: alt7_rd0 | alt7_rd1 => disp_inter == disp_in
            If(~self.disp_in & alt7_rd0,
                self.disp_out.eq(~self.disp_in),
                output_4b.eq(0b0111)
            ).Elif(self.disp_in & alt7_rd1,
                self.disp_out.eq(~self.disp_in),
                output_4b.eq(0b1000)
            ).Else(
                self.disp_out.eq(disp_inter ^ code4b_unbalanced),
                If(disp_inter & code4b_flip,
                    output_4b.eq(~code4b)
                ).Else(
                    output_4b.eq(code4b)
                )
            )
        ]

        self.comb += self.output.eq(Cat(output_6b, output_4b))


class Encoder(Module):
    def __init__(self, nwords=1):
        self.d = [Signal(8) for _ in range(nwords)]
        self.k = [Signal() for _ in range(nwords)]
        self.output = [Signal(10) for _ in range(nwords)]

        # # #

        encoders = [SingleEncoder() for _ in nwords]
        self.submodules += encoders

        self.sync += encoders[0].disp_in.eq(encoders[-1].disp_out)
        for e1, e2 in zip(encoders, encoders[1:]):
            self.comb += e2.disp_in.eq(e1.disp_out)

        for d, k, output, e in zip(self.d, self.k, self.output, encoders):
            self.comb += [
                e.d.eq(d),
                e.k.eq(k)
            ]
            self.sync += output.eq(e.output)

