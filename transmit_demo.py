from migen import *
from migen.build.platforms import kc705


class TransmitDemo(Module):
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

        clock_pads = platform.request("sgmii_clock")
        refclk_div2 = Signal()
        self.specials += Instance("IBUFDS_GTE2",
            i_CEB=0,
            i_I=clock_pads.p,
            i_IB=clock_pads.n,
            o_ODIV2=refclk_div2
        )

        txoutclk = Signal()
        tx_pads = platform.request("sfp_tx")
        self.specials += \
            Instance("GTXE2_CHANNEL",
                # PMA Attributes
                p_PMA_RSV=0x00018480,
                p_PMA_RSV2=0x2050,
                p_PMA_RSV3=0,
                p_PMA_RSV4=0,
                p_RX_BIAS_CFG=0b100,
                p_RX_CM_TRIM=0b010,
                p_RX_OS_CFG=0b10000000,
                p_RX_CLK25_DIV=5,
                p_TX_CLK25_DIV=5,

                # Power-Down Attributes
                p_PD_TRANS_TIME_FROM_P2=0x3c,
                p_PD_TRANS_TIME_NONE_P2=0x3c,
                p_PD_TRANS_TIME_TO_P2=0x64,

                # CPLL
                p_CPLL_CFG=0xBC07DC,
                p_CPLL_FBDIV=4,
                p_CPLL_FBDIV_45=5,
                p_CPLL_REFCLK_DIV=1,
                p_RXOUT_DIV=2,
                p_TXOUT_DIV=2,
                o_CPLLLOCK=platform.request("user_led"),
                i_CPLLLOCKEN=1,
                i_CPLLREFCLKSEL=0b001,
                i_TSTIN=2**20-1,
                i_GTREFCLK0=refclk_div2,

                # TX clock
                p_TXBUF_EN="FALSE",
                p_TX_XCLK_SEL="TXUSR",
                o_TXOUTCLK=txoutclk,
                i_TXSYSCLKSEL=0b00,
                i_TXOUTCLKSEL=0b11,

                # disable RX
                i_RXPD=0b11,

                # Startup/Reset
                i_GTTXRESET=platform.request("user_btn_c"),
                #i_TXDLYSRESET=txdlyreset,
                #o_TXDLYSRESETDONE=txdlyresetdone,
                #o_TXPHALIGNDONE=txphaligndone,

                # TX data
                p_TX_DATA_WIDTH=20,
                p_TX_INT_DATAWIDTH=0,
                i_TXUSERRDY=1,
                i_TXCHARDISPMODE=0,
                i_TXCHARDISPVAL=0,
                i_TXDATA=0b0001111100011111,
                i_TXUSRCLK=ClockSignal("tx"),
                i_TXUSRCLK2=ClockSignal("tx"),

                # TX electrical
                i_TXBUFDIFFCTRL=0b100,
                i_TXDIFFCTRL=0b1000,

                # Pads
                o_GTXTXP=tx_pads.p,
                o_GTXTXN=tx_pads.n,
            )

        self.clock_domains.cd_tx = ClockDomain()
        self.specials += Instance("BUFG",
            i_I=txoutclk, o_O=self.cd_tx.clk)


if __name__ == "__main__":
    platform = kc705.Platform()
    top = TransmitDemo(platform)
    platform.build(top, build_dir="transmit_demo")
