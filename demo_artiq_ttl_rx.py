#!/usr/bin/env python3.5

from migen import *
from migen.build.platforms import kc705
from misoc.cores.uart import RS232PHY

from gtx import GTXReceiver
from ttl_xm105 import ttl_extension
from sequencer import Sequencer
from i2c import I2CMaster
from si5324_kc705 import get_i2c_program, Si5324ClockRouter


class ARTIQTTLRX(Module):
    def __init__(self, platform):
        platform.add_extension(ttl_extension)

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

        # clean up GTX clock using Si5324
        i2c_master = I2CMaster(platform.request("i2c"))
        sequencer = Sequencer(get_i2c_program(sys_clk_freq))
        si5324_clock_router = Si5324ClockRouter(platform, sys_clk_freq)
        self.submodules += i2c_master, sequencer, si5324_clock_router
        self.comb += sequencer.bus.connect(i2c_master.bus)

        # decode frames
        back_buffer = Signal(32)
        front_buffer = Signal(32)
        frame_hi = Signal()
        self.sync.rx_clean += [
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
                ),
                frame_hi.eq(1)
            )
        ]

        # drive TTLs
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
