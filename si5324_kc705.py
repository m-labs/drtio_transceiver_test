# Configures the Si5324 on the KC705 for 62.5MHz in, 62.5MHz out
# Also configures the PCA9548 I2C switch on the KC705 to give access
# to the Si5324.

from migen import *

from i2c import *
from sequencer import *


def get_i2c_program(sys_clk_freq):
    # NOTE: the logical parameters DO NOT MAP to physical values written
    # into registers. They have to be mapped; see the datasheet.
    # DSPLLsim reports the logical parameters in the design summary, not
    # the physical register values (but those are present separately).
    N1_HS  = 0   # 4
    NC1_LS = 19  # 20
    N2_HS  = 1   # 5
    N2_LS  = 511 # 512
    N31    = 31  # 32

    i2c_sequence = [
        # PCA9548: select channel 7
        [(0x74 << 1), 1 << 7],
        # Si5324: configure
        [(0x68 << 1), 2,   0b0010 | (4 << 4)], # BWSEL=4
        [(0x68 << 1), 3,   0b0101 | 0x10],     # SQ_ICAL=1
        [(0x68 << 1), 6,            0x07],     # SFOUT1_REG=b111
        [(0x68 << 1), 25,  (N1_HS  << 5 ) & 0xff],
        [(0x68 << 1), 31,  (NC1_LS >> 16) & 0xff],
        [(0x68 << 1), 32,  (NC1_LS >> 8 ) & 0xff],
        [(0x68 << 1), 33,  (NC1_LS)       & 0xff],
        [(0x68 << 1), 40,  (N2_HS  << 5 ) & 0xff |
                           (N2_LS  >> 16) & 0xff],
        [(0x68 << 1), 41,  (N2_LS  >> 8 ) & 0xff],
        [(0x68 << 1), 42,  (N2_LS)        & 0xff],
        [(0x68 << 1), 43,  (N31    >> 16) & 0xff],
        [(0x68 << 1), 44,  (N31    >> 8)  & 0xff],
        [(0x68 << 1), 45,  (N31)          & 0xff],
        [(0x68 << 1), 137,          0x01],     # FASTLOCK=1
        [(0x68 << 1), 136,          0x40],     # ICAL=1
    ]

    program = [
        InstWrite(I2C_CONFIG_ADDR, int(sys_clk_freq/1e3)),
    ]
    for subseq in i2c_sequence:
        program += [
            InstWrite(I2C_XFER_ADDR, I2C_START),
            InstWait(I2C_XFER_ADDR, I2C_IDLE),
        ]
        for octet in subseq:
            program += [
                InstWrite(I2C_XFER_ADDR, I2C_WRITE | octet),
                InstWait(I2C_XFER_ADDR, I2C_IDLE),
            ]
        program += [
            InstWrite(I2C_XFER_ADDR, I2C_STOP),
            InstWait(I2C_XFER_ADDR, I2C_IDLE),
        ]
    program += [
        InstEnd(),
    ]
    return program


class Si5324ClockRouter(Module):
    def __init__(self, platform, sys_clk_freq):
        # Reset
        si5324_rst_n = platform.request("si5324").rst_n
        reset_val = int(sys_clk_freq/20e3)
        reset_ctr = Signal(max=reset_val+1, reset=reset_val)
        self.sync += \
            If(reset_ctr != 0,
                reset_ctr.eq(reset_ctr - 1)
            ).Else(
                si5324_rst_n.eq(1)
            )

        # Clock to Si5324
        si5324_clkin = platform.request("si5324_clkin")
        self.specials += \
            Instance("OBUFDS",
                i_I=ClockSignal("rx"),
                o_O=si5324_clkin.p, o_OB=si5324_clkin.n
            )

        # Clock from Si5324
        si5324_clkout = platform.request("si5324_clkout")
        rx_clean_unbuffered = Signal()
        self.clock_domains.cd_rx_clean = ClockDomain(reset_less=True)
        self.specials += [
            Instance("IBUFDS_GTE2",
                     i_I=si5324_clkout.p, i_IB=si5324_clkout.n,
                     o_O=rx_clean_unbuffered),
            Instance("BUFG",
                     i_I=rx_clean_unbuffered,
                     o_O=self.cd_rx_clean.clk),
        ]

        # Debug SMAs
        sma = platform.request("user_sma_clock_p")
        self.comb += sma.eq(ClockSignal("rx"))
        sma = platform.request("user_sma_clock_n")
        self.comb += sma.eq(ClockSignal("rx_clean"))
