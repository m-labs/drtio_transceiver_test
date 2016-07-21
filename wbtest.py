from migen import *
from migen.build.platforms import kc705

from misoc.cores.uart.core import RS232PHY

import wishbonebridge


class WBTest(Module):
    def __init__(self, platform):
        sys_clock_pads = platform.request("clk156")
        self.clock_domains.cd_sys = ClockDomain(reset_less=True)
        self.specials += Instance("IBUFGDS",
            i_I=sys_clock_pads.p, i_IB=sys_clock_pads.n,
            o_O=self.cd_sys.clk)

        self.submodules.phy = RS232PHY(platform.request("serial"), 156000000, 115200)
        self.submodules.bridge = wishbonebridge.WishboneStreamingBridge(self.phy, 156000000)
        self.comb += [
            self.bridge.wishbone.ack.eq(self.bridge.wishbone.stb),
            self.bridge.wishbone.dat_r.eq(0xdeadbeef)
        ]


if __name__ == "__main__":
    platform = kc705.Platform()
    top = WBTest(platform)
    platform.build(top, build_dir="wbtest")
