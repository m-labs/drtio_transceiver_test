from migen import *
from migen.build.platforms import kc705


class TransceiverTest(Module):
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
        refclk = Signal()
        self.specials += Instance("IBUFDS_GTE2",
            i_CEB=0,
            i_I=clock_pads.p,
            i_IB=clock_pads.n,
            o_O=refclk
        )

        txoutclk = Signal()
        tx_pads = platform.request("user_sma_mgt_tx")
        rx_pads = platform.request("user_sma_mgt_rx")
        gtxe2_channel_parameters = {
            # PMA Attributes
            "p_PMA_RSV": 0x00018480,
            "p_PMA_RSV2": 0x2050,
            "p_PMA_RSV3": 0,
            "p_PMA_RSV4": 0,
            "p_RX_BIAS_CFG": 0b100,
            "p_RX_CM_TRIM": 0b010,
            "p_RX_OS_CFG": 0b10000000,
            "p_RX_CLK25_DIV": 5,
            "p_TX_CLK25_DIV": 5,

            # Power-Down Attributes
            "p_PD_TRANS_TIME_FROM_P2": 0x3c,
            "p_PD_TRANS_TIME_NONE_P2": 0x3c,
            "p_PD_TRANS_TIME_TO_P2": 0x64,

            # TX Buffer Attributes
            "p_TXBUF_EN": "FALSE",
            "p_TX_XCLK_SEL": "TXUSR",

            # FPGA TX Interface Attributes
            "p_TX_DATA_WIDTH": 20,
            "p_TX_INT_DATAWIDTH": 0,

            # CPLL Attributes
            "p_CPLL_CFG": 0xBC07DC,
            "p_CPLL_FBDIV": 4,
            "p_CPLL_FBDIV_45": 5,
            "p_CPLL_REFCLK_DIV": 1,
            "p_RXOUT_DIV": 4,
            "p_TXOUT_DIV": 4,
        }

        self.specials += \
            Instance("GTXE2_CHANNEL",
                # CPLL
                o_CPLLLOCK=platform.request("user_led"),
                i_CPLLLOCKEN=1,
                i_CPLLREFCLKSEL=0b001,
                i_TSTIN=2**20-1,
                i_GTREFCLK0=refclk,

                # TX clock
                o_TXOUTCLK=txoutclk,
                i_TXSYSCLKSEL=0b00,
                i_TXOUTCLKSEL=0b11,

                # RX clock
                i_RXSYSCLKSEL=0b00,

                # Startup/Reset
                i_GTTXRESET=platform.request("user_btn_c"),
                #i_TXDLYSRESET=txdlyreset,
                #o_TXDLYSRESETDONE=txdlyresetdone,
                #o_TXPHALIGNDONE=txphaligndone,

                # TX data
                i_TXUSERRDY=1,
                i_TXCHARDISPMODE=1,
                i_TXCHARDISPVAL=1,
                i_TXDATA=0xff,
                i_TXUSRCLK=ClockSignal("tx"),
                i_TXUSRCLK2=ClockSignal("tx"),

                # TX electrical
                i_TXBUFDIFFCTRL=0b100,
                i_TXDIFFCTRL=0b1000,

                # Pads
                o_GTXTXP=tx_pads.p,
                o_GTXTXN=tx_pads.n,
                i_GTXRXP=rx_pads.p,
                i_GTXRXN=rx_pads.n,

                **gtxe2_channel_parameters
            )

        self.clock_domains.cd_tx = ClockDomain()
        self.specials += Instance("BUFG",
            i_I=txoutclk, o_O=self.cd_tx.clk)

        led = platform.request("user_led")
        counter = Signal(26)
        self.sync.tx += counter.eq(counter + 1)
        self.comb += led.eq(counter[25])


if __name__ == "__main__":
    platform = kc705.Platform()
    top = TransceiverTest(platform)
    platform.build(top)
