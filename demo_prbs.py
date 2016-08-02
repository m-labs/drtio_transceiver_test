#!/usr/bin/env python3.5

import argparse
from operator import or_
from functools import reduce

from migen import *
from migen.genlib.cdc import GrayCounter, NoRetiming, MultiReg, GrayDecoder
from migen.build.platforms import kc705
from misoc.cores.uart import RS232PHY
from misoc.interconnect import wishbone

from gtx import GTXTransmitter, GTXReceiver
from prbs import PRBSGenerator, PRBSChecker
from i2c import *
from sequencer import Sequencer
from si5324_kc705 import get_i2c_program
from wishbonebridge import WishboneStreamingBridge
from comm_uart import CommUART


class PRBSTX(Module):
    def __init__(self, platform):
        sys_clock_pads = platform.request("clk156")
        self.clock_domains.cd_sys = ClockDomain(reset_less=True)
        self.specials += Instance("IBUFGDS",
            i_I=sys_clock_pads.p, i_IB=sys_clock_pads.n,
            o_O=self.cd_sys.clk)
        self.comb += platform.request("sfp_tx_disable_n").eq(1)

        gtx = GTXTransmitter(
            clock_pads=platform.request("sgmii_clock"),
            tx_pads=platform.request("sfp_tx"),
            sys_clk_freq=156000000)
        self.submodules += gtx

        frame_counter = Signal(4)
        header = Signal()
        self.sync.tx += [
            frame_counter.eq(frame_counter + 1),
            header.eq(frame_counter == 0)
        ]

        generator = ClockDomainsRenamer("tx")(CEInserter()(PRBSGenerator(16)))
        self.submodules += generator

        self.comb += [
            If(header,
                gtx.encoder.k[0].eq(1),
                gtx.encoder.d[0].eq((5 << 5) | 28),
                gtx.encoder.k[1].eq(0),
                gtx.encoder.d[1].eq(0),
                generator.ce.eq(0)
            ).Else(
                gtx.encoder.k[0].eq(0),
                gtx.encoder.d[0].eq(generator.o[:8]),
                gtx.encoder.k[1].eq(0),
                gtx.encoder.d[1].eq(generator.o[8:]),
                generator.ce.eq(1)
            )
        ]


class PRBSRX(Module):
    def __init__(self, platform):
        sys_clock_pads = platform.request("clk156")
        self.clock_domains.cd_sys = ClockDomain(reset_less=True)
        self.specials += Instance("IBUFGDS",
            i_I=sys_clock_pads.p, i_IB=sys_clock_pads.n,
            o_O=self.cd_sys.clk)
        sys_clk_freq = 156000000
        self.comb += platform.request("sfp_tx_disable_n").eq(1)

        gtx = GTXReceiver(
            clock_pads=platform.request("sgmii_clock"),
            rx_pads=platform.request("sfp_rx"),
            sys_clk_freq=sys_clk_freq)
        self.submodules += gtx

        # PRBS checker
        checker = ClockDomainsRenamer("rx")(CEInserter()(PRBSChecker(16)))
        self.submodules += checker

        self.sync.rx += [
            checker.ce.eq(~gtx.decoders[0].k),
            checker.i[:8].eq(gtx.decoders[0].d),
            checker.i[8:].eq(gtx.decoders[1].d)
        ]

        error_accumulator = ClockDomainsRenamer("rx")(GrayCounter(32))
        self.submodules += error_accumulator
        error_bits = [checker.errors[i] for i in range(len(checker.errors))]
        self.comb += error_accumulator.ce.eq(reduce(or_, error_bits))

        error_decoder = GrayDecoder(32)
        self.submodules += error_decoder
        self.specials += [
            NoRetiming(error_accumulator.q),
            MultiReg(error_accumulator.q, error_decoder.i)
        ]

        # Wishbone target - I2C
        i2c_master = I2CMaster(platform.request("i2c"))
        self.submodules += i2c_master

        # Wishbone target - PRBS error count
        checker_wb = wishbone.Interface()
        self.sync += [
            checker_wb.dat_r.eq(error_decoder.o),
            checker_wb.ack.eq(0),
            If(checker_wb.cyc & checker_wb.stb & ~checker_wb.ack,
                checker_wb.ack.eq(1))
        ]

        # Wishbone master - Sequencer
        sequencer = Sequencer(get_i2c_program(sys_clk_freq))
        self.submodules += sequencer

        # Wishbone master - UART bridge
        uart_phy = RS232PHY(platform.request("serial"), sys_clk_freq, 115200)
        bridge = WishboneStreamingBridge(uart_phy, sys_clk_freq)
        self.submodules += uart_phy, bridge

        # Wishbone interconnect
        interconnect = wishbone.InterconnectShared(
            [sequencer.bus, bridge.wishbone],
            [(lambda a: a[4] == 0, i2c_master.bus),
             (lambda a: a[4] == 1, checker_wb)],
            register=True)
        self.submodules += interconnect


def build_tx():
    platform = kc705.Platform()
    top = PRBSTX(platform)
    platform.build(top, build_dir="prbs_tx")


def build_rx():
    platform = kc705.Platform()
    top = PRBSRX(platform)
    platform.build(top, build_dir="prbs_rx")


def readout(port):
    with CommUART(port) as comm:
        print(comm.read(0x40))


def main():
    parser = argparse.ArgumentParser(description="PRBS demo")
    parser.add_argument("--no-tx", default=False, action="store_true",
                        help="do not build TX bitstream")
    parser.add_argument("--no-rx", default=False, action="store_true",
                        help="do not build RX bitstream")
    parser.add_argument("--readout", metavar="SERIAL_PORT",
                        default=None, type=str,
                        help="read out error counter value from the board "
                             "on the specified serial device. Disables all "
                             "bitstream builds.")
    args = parser.parse_args()
    if args.readout is not None:
        readout(args.readout)
    else:
        if not args.no_tx:
            build_tx()
        if not args.no_rx:
            build_rx()


if __name__ == "__main__":
    main()
