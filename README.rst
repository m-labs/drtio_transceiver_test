Transceiver test and demonstration for DRTIO
============================================

This repository contains several test and proof-of-concept designs for data and time transfer over high-speed transceivers, which will enable distributed real-time I/O (DRTIO) in ARTIQ.

Communications are between two KC705 boards connected over SFP at 1.25Gbps line rate. Use 1310/1490nm SFPs with a single G.652 fiber (same as White Rabbit - http://www.ohwr.org/projects/white-rabbit/wiki/SFP).

Requires Migen 0.4+ and ARTIQ 2.0+.

Remote LED demonstration
------------------------

Build the designs by running ``remote_led.py``. The four DIP switches on the transmitting KC705 control LEDs 2-6 on the receiving KC705. LEDs 0-1 on both boards blink from the system and transceiver data clocks, respectively. 

Managing multiple KC705 boards with OpenOCD
-------------------------------------------

1. Obtain the serial number of each board using ``lsusb -v``. It should be a number such as ``123456789012``.
2. Run the following command to load a bitstream into the corresponding board's FPGA:
   ``openocd -f board/kc705.cfg -c "ftdi_serial 123456789012; init; pld load 0 bitstream.bit; exit;"``

If you are using the OpenOCD Conda package:

1. locate the OpenOCD scripts directory with:
   ``python3 -c "import artiq.frontend.artiq_flash as af; print(af.scripts_path)"``
2. add ``-s <scripts directory>`` to the OpenOCD command line.
