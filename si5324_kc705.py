# Configures the Si5324 on the KC705 for 62.5MHz in, 62.5MHz out
# Also configures the PCA9548 I2C switch on the KC705 to give access
# to the Si5324.

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
