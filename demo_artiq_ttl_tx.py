#!/usr/bin/env python3.5

import argparse

from migen import *
from migen.fhdl.specials import Keep

from misoc.targets.kc705 import MiniSoC, soc_kc705_args, soc_kc705_argdict
from misoc.integration.builder import builder_args, builder_argdict

from artiq.gateware.soc import AMPSoC, build_artiq_soc
from artiq.gateware import rtio
from artiq.gateware.rtio.phy import ttl_simple

from ttl_xm105 import ttl_extension
from gtx import GTXTransmitter


class RemoteTTLChannels(Module):
    def __init__(self, clock_pads, tx_pads, sys_clk_freq, **kwargs):
        self.clock_domains.cd_rtio = ClockDomain()
        self.rtio_channels = []

        # # #

        gtx = GTXTransmitter(
            clock_pads=clock_pads,
            tx_pads=tx_pads,
            sys_clk_freq=sys_clk_freq)
        self.submodules += gtx

        self.comb += [
            self.cd_rtio.clk.eq(ClockSignal("tx")),
            self.cd_rtio.rst.eq(ResetSignal("tx")),
        ]

        ttl_values = Signal(32)
        frame_counter = Signal(max=3)
        self.sync.tx += [
            If(frame_counter == 0,
                gtx.encoder.k[0].eq(1),
                gtx.encoder.d[0].eq((5 << 5) | 28),
                gtx.encoder.k[1].eq(0),
                gtx.encoder.d[1].eq(0),
                frame_counter.eq(1),
            ).Elif(frame_counter == 1,
                gtx.encoder.k[0].eq(0),
                gtx.encoder.d[0].eq(ttl_values[0:8]),
                gtx.encoder.k[1].eq(0),
                gtx.encoder.d[1].eq(ttl_values[8:16]),
                frame_counter.eq(2)
            ).Else(
                gtx.encoder.k[0].eq(0),
                gtx.encoder.d[0].eq(ttl_values[16:24]),
                gtx.encoder.k[1].eq(0),
                gtx.encoder.d[1].eq(ttl_values[24:32]),
                frame_counter.eq(0)
            )
        ]

        for i in range(32):
            value = ttl_values[i]

            rtlink = rtio.rtlink.Interface(rtio.rtlink.OInterface(1))
            probes = [value]
            override_en = Signal()
            override_o = Signal()
            overrides = [override_en, override_o]

            channel = rtio.Channel(rtlink, probes, overrides, **kwargs)
            self.rtio_channels.append(channel)

            value_k = Signal()
            self.sync.rio_phy += [
                If(rtlink.o.stb,
                    value_k.eq(rtlink.o.data)
                ),
                If(override_en,
                    value.eq(override_o)
                ).Else(
                    value.eq(value_k)
                )
            ]


class ARTIQTTLTX(MiniSoC, AMPSoC):
    csr_map = {
        # mapped on Wishbone instead
        "timer_kernel": None,
        "rtio": None,

        "rtio_crg": 13,
        "kernel_cpu": 14,
        "rtio_moninj": 15,
        "rtio_analyzer": 16
    }
    csr_map.update(MiniSoC.csr_map)
    mem_map = {
        "timer_kernel":  0x10000000, # (shadow @0x90000000)
        "rtio":          0x20000000, # (shadow @0xa0000000)
        "mailbox":       0x70000000  # (shadow @0xf0000000)
    }
    mem_map.update(MiniSoC.mem_map)

    def __init__(self, **kwargs):
        MiniSoC.__init__(self,
                         cpu_type="or1k",
                         sdram_controller_type="minicon",
                         l2_size=128*1024,
                         with_timer=False,
                         ident="DRTIO_DEMO",
                         **kwargs)
        AMPSoC.__init__(self)

        platform = self.platform
        platform.add_extension(ttl_extension)

        rtio_channels = []
        phy = ttl_simple.Output(platform.request("user_sma_gpio_p"))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))
        phy = ttl_simple.Output(platform.request("user_sma_gpio_n"))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))
        for i in range(8):
            phy = ttl_simple.Output(platform.request("user_led"))
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))
        for i in range(22):
            phy = ttl_simple.Output(platform.request("ttl"))
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))
        self.comb += platform.request("sfp_tx_disable_n").eq(1)
        self.submodules.remote_ttl_channels = RemoteTTLChannels(
            clock_pads=platform.request("sgmii_clock"),
            tx_pads=platform.request("sfp_tx"),
            sys_clk_freq=125000000)
        rtio_channels += self.remote_ttl_channels.rtio_channels
        self.config["RTIO_REGULAR_TTL_COUNT"] = len(rtio_channels)
        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        sma = platform.request("user_sma_clock_p")
        self.comb += sma.eq(ClockSignal("tx"))

        self.submodules.rtio = rtio.RTIO(rtio_channels)
        self.register_kernel_cpu_csrdevice("rtio")
        self.config["RTIO_FINE_TS_WIDTH"] = self.rtio.fine_ts_width
        self.submodules.rtio_moninj = rtio.MonInj(rtio_channels)

        self.specials += [
            Keep(self.rtio.cd_rsys.clk),
            Keep(self.remote_ttl_channels.cd_rtio.clk),
            Keep(self.ethphy.crg.cd_eth_rx.clk),
            Keep(self.ethphy.crg.cd_eth_tx.clk),
        ]

        platform.add_period_constraint(self.rtio.cd_rsys.clk, 8.)
        platform.add_period_constraint(self.remote_ttl_channels.cd_rtio.clk, 16.)
        platform.add_period_constraint(self.ethphy.crg.cd_eth_rx.clk, 8.)
        platform.add_period_constraint(self.ethphy.crg.cd_eth_tx.clk, 8.)
        platform.add_false_path_constraints(
            self.rtio.cd_rsys.clk,
            self.remote_ttl_channels.cd_rtio.clk,
            self.ethphy.crg.cd_eth_rx.clk,
            self.ethphy.crg.cd_eth_tx.clk)

        self.submodules.rtio_analyzer = rtio.Analyzer(self.rtio,
            self.get_native_sdram_if())


def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ remote TTL demo (transmitter)")
    builder_args(parser)
    soc_kc705_args(parser)
    args = parser.parse_args()

    soc = ARTIQTTLTX(**soc_kc705_argdict(args))
    build_artiq_soc(soc, builder_argdict(args))


if __name__ == "__main__":
    main()
