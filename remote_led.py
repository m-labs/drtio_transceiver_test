#!/usr/bin/env python3.5

import argparse

from migen import *
from migen.build.platforms import kc705

from gtx import GTXTransmitter, GTXReceiver


class RemoteLEDTX(Module):
    def __init__(self, platform):
        sys_clock_pads = platform.request("clk156")
        self.clock_domains.cd_sys = ClockDomain(reset_less=True)
        self.specials += Instance("IBUFGDS",
            i_I=sys_clock_pads.p, i_IB=sys_clock_pads.n,
            o_O=self.cd_sys.clk)

        led_clksys = platform.request("user_led")
        counter_clksys = Signal(26)
        self.sync += counter_clksys.eq(counter_clksys + 1)
        self.comb += led_clksys.eq(counter_clksys[25])

        led_clktx = platform.request("user_led")
        counter_clktx = Signal(26)
        self.sync.tx += counter_clktx.eq(counter_clktx + 1)
        self.comb += led_clktx.eq(counter_clktx[25])

        self.comb += platform.request("sfp_tx_disable_n").eq(1)

        gtx = GTXTransmitter(
            clock_pads=platform.request("sgmii_clock"),
            tx_pads=platform.request("sfp_tx"),
            sys_clk_freq=156000000
        )
        self.submodules += gtx

        word = Signal(4)
        for i in range(4):
            self.sync.tx += word[i].eq(platform.request("user_dip_btn"))
        self.comb += [
            gtx.encoder.k[0].eq(1),
            gtx.encoder.d[0].eq((5 << 5) | 28),
            gtx.encoder.k[1].eq(0),
            gtx.encoder.d[1].eq(word),
        ]


class RemoteLEDRX(Module):
    def __init__(self, platform):
        sys_clock_pads = platform.request("clk156")
        self.clock_domains.cd_sys = ClockDomain(reset_less=True)
        self.specials += Instance("IBUFGDS",
            i_I=sys_clock_pads.p, i_IB=sys_clock_pads.n,
            o_O=self.cd_sys.clk)

        led_clksys = platform.request("user_led")
        counter_clksys = Signal(26)
        self.sync += counter_clksys.eq(counter_clksys + 1)
        self.comb += led_clksys.eq(counter_clksys[25])

        led_clkrx = platform.request("user_led")
        counter_clkrx = Signal(26)
        self.sync.rx += counter_clkrx.eq(counter_clkrx + 1)
        self.comb += led_clkrx.eq(counter_clkrx[25])

        self.comb += platform.request("sfp_tx_disable_n").eq(1)

        gtx = GTXReceiver(
            clock_pads=platform.request("sgmii_clock"),
            rx_pads=platform.request("sfp_rx"),
            sys_clk_freq=156000000
        )
        self.submodules += gtx
        
        for i in range(4):
            self.comb += platform.request("user_led").eq(gtx.decoders[1].d[i])


def build_tx():
    platform = kc705.Platform()
    top = RemoteLEDTX(platform)
    platform.build(top, build_dir="remote_led_tx")


def build_rx():
    platform = kc705.Platform()
    top = RemoteLEDRX(platform)
    platform.build(top, build_dir="remote_led_rx")


def main():
    parser = argparse.ArgumentParser(description="Remote-controlled LEDs demo")
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
