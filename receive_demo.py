from migen import *
from migen.build.platforms import kc705


class ReceiveDemo(Module):
    def __init__(self, platform):
        sys_clock_pads = platform.request("clk156")
        self.clock_domains.cd_sys = ClockDomain(reset_less=True)
        self.specials += Instance("IBUFGDS",
            i_I=sys_clock_pads.p, i_IB=sys_clock_pads.n,
            o_O=self.cd_sys.clk)

        led = platform.request("user_led")
        counter = Signal(26)
        self.sync += counter.eq(counter + 1)
        self.comb += led.eq(counter[25])

        clock_pads = platform.request("sgmii_clock")
        refclk_div2 = Signal()
        self.specials += Instance("IBUFDS_GTE2",
            i_CEB=0,
            i_I=clock_pads.p,
            i_IB=clock_pads.n,
            o_ODIV2=refclk_div2
        )

        rxoutclk = Signal()
        rxdata = Signal(64)
        rx_pads = platform.request("sfp_rx")
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

                # Startup/Reset
                i_GTRXRESET=platform.request("user_btn_c"),
                #o_RXRESETDONE=,
                #i_RXDLYSRESET=,
                #o_RXDLYSRESETDONE=,
                #o_RXPHALIGNDONE=,

                # RX AFE
                p_RX_DFE_XYD_CFG=0,
                i_RXDFEXYDEN=1,
                i_RXDFEXYDHOLD=0,
                i_RXDFEXYDOVRDEN=0,
                i_RXLPMEN=0,

                # RX clock
                p_RXBUF_EN="FALSE",
                p_RX_XCLK_SEL="RXUSR",
                i_RXDDIEN=1,
                i_RXSYSCLKSEL=0b00,
                i_RXOUTCLKSEL=0b010,
                o_RXOUTCLK=rxoutclk,
                i_RXUSRCLK=ClockSignal("rx"),
                i_RXUSRCLK2=ClockSignal("rx"),
                p_RXCDR_CFG=0x03000023FF10100020,

                # RX Clock Correction Attributes
                p_CLK_CORRECT_USE="FALSE",
                p_CLK_COR_SEQ_1_1=0b0100000000,
                p_CLK_COR_SEQ_2_1=0b0100000000,
                p_CLK_COR_SEQ_1_ENABLE=0b1111,
                p_CLK_COR_SEQ_2_ENABLE=0b1111,

                # RX data
                p_RX_DATA_WIDTH=20,
                p_RX_INT_DATAWIDTH=0,
                i_RXUSERRDY=1,
                o_RXDATA=rxdata,
                #o_RXCHARISK=,
                #o_RXDISPERR=,
                #o_RXNOTINTABLE=,

                # disable TX
                i_TXPD=0b11,

                # Pads
                i_GTXRXP=rx_pads.p,
                i_GTXRXN=rx_pads.n,
            )

        self.clock_domains.cd_rx = ClockDomain()
        self.specials += Instance("BUFG",
            i_I=rxoutclk, o_O=self.cd_rx.clk)

        led = platform.request("user_led")
        counter = Signal(26)
        self.sync.rx += counter.eq(counter + 1)
        self.comb += led.eq(counter[25])

        for i in range(4):
            self.comb += platform.request("user_led").eq(rxdata[i])


if __name__ == "__main__":
    platform = kc705.Platform()
    top = ReceiveDemo(platform)
    platform.build(top, build_dir="receive_demo")
