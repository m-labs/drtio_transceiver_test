#!/usr/bin/env python3.5

from migen import *
from migen.build.platforms import kc705
from misoc.cores.uart import RS232PHY

from gtx import GTXReceiver
from ttl_xm105 import ttl_extension
from wishbonebridge import WishboneStreamingBridge


class ARTIQTTLRX(Module):
    def __init__(self, platform):
        platform.add_extension(ttl_extension)

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

        sma = platform.request("user_sma_clock_p")
        self.comb += sma.eq(ClockSignal("rx"))

        back_buffer = Signal(32)
        front_buffer = Signal(32)
        frame_hi = Signal()
        self.sync.rx += [
            If(gtx.decoders[0].k,
                front_buffer.eq(back_buffer),
                frame_hi.eq(0)
            ).Else(
                If(frame_hi,
                    back_buffer[16:].eq(
                        Cat(gtx.decoders[0].d, gtx.decoders[1].d))
                ).Else(
                    back_buffer[:16].eq(
                        Cat(gtx.decoders[0].d, gtx.decoders[1].d))
                )
            )
        ]

        self.comb += [
            platform.request("user_sma_gpio_p").eq(front_buffer[0]),
            platform.request("user_sma_gpio_n").eq(front_buffer[1])
        ]
        for i in range(8):
            self.comb += platform.request("user_led").eq(front_buffer[2+i])
        for i in range(22):
            self.comb += platform.request("ttl").eq(front_buffer[10+i])


def main():
    platform = kc705.Platform()
    top = ARTIQTTLRX(platform)
    platform.build(top, build_dir="artiq_ttl_rx")

if __name__ == "__main__":
    main()
