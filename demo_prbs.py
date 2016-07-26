#!/usr/bin/env python3.5

import argparse

from migen import *
from migen.build.platforms import kc705
from misoc.cores.uart import RS232PHY

from gtx import GTXTransmitter, GTXReceiver
from prbs import PRBSGenerator, PRBSChecker
from wishbonebridge import WishboneStreamingBridge


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
        self.comb += platform.request("sfp_tx_disable_n").eq(1)

        gtx = GTXReceiver(
            clock_pads=platform.request("sgmii_clock"),
            rx_pads=platform.request("sfp_rx"),
            sys_clk_freq=156000000)
        self.submodules += gtx

        checker = ClockDomainsRenamer("rx")(CEInserter()(PRBSChecker(16)))
        self.submodules += checker

        self.sync.rx += [
            checker.ce.eq(~gtx.decoders[0].k),
            checker.i[:8].eq(gtx.decoders[0].d),
            checker.i[8:].eq(gtx.decoders[1].d)
        ]

        error_accumulator = Signal(32)
        self.sync.rx += error_accumulator.eq(
            error_accumulator + checker.error_count)

        uart_phy = ClockDomainsRenamer("rx")(
            RS232PHY(platform.request("serial"), 62500000, 115200))
        bridge = ClockDomainsRenamer("rx")(
            WishboneStreamingBridge(uart_phy, 62500000))
        self.submodules += uart_phy, bridge
        self.comb += [
            bridge.wishbone.ack.eq(bridge.wishbone.cyc & bridge.wishbone.stb),
            bridge.wishbone.dat_r.eq(error_accumulator)
        ]


def build_tx():
    platform = kc705.Platform()
    top = PRBSTX(platform)
    platform.build(top, build_dir="prbs_tx")


def build_rx():
    platform = kc705.Platform()
    top = PRBSRX(platform)
    platform.build(top, build_dir="prbs_rx")


def main():
    parser = argparse.ArgumentParser(description="PRBS demo")
    parser.add_argument("--no-tx", default=False, action="store_true",
                        help="do not build TX bitstream")
    parser.add_argument("--no-rx", default=False, action="store_true",
                        help="do not build RX bitstream")
    args = parser.parse_args()
    if not args.no_tx:
        build_tx()
    if not args.no_rx:
        build_rx()


if __name__ == "__main__":
    main()
