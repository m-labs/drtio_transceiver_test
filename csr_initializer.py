from collections import namedtuple

from migen import *
from migen.genlib.fsm import *
from misoc.interconnect import wishbone


# Instruction set:
#  <2> OP  <6> ADDRESS  <8> DATA_BSEL
#
# OP=00: end program, ADDRESS=don't care, DATA_BSEL=don't care
# OP=01: write, ADDRESS=address, DATA_BSEL=data
# OP=10: read until bit is at 0, ADDRESS=address, DATA_BSEL[0:3]=bit sel
# OP=11: read until bit is at 1, ADDRESS=address, DATA_BSEL[0:3]=bit sel


InstEnd = namedtuple("InstEnd", "")
InstWrite = namedtuple("InstWrite", "address data")
InstReadUntil0 = namedtuple("InstReadUntil0", "address bsel")
InstReadUntil1 = namedtuple("InstReadUntil1", "address bsel")


def encode(inst):
    address, data_bsel = 0, 0
    if isinstance(inst, InstEnd):
        opcode = 0b00
    elif isinstance(inst, InstWrite):
        opcode = 0b01
        address = inst.address
        data_bsel = inst.data
    elif isinstance(inst, InstReadUntil0):
        opcode = 0b10
        address = inst.address
        data_bsel = inst.bsel
    elif isinstance(inst, InstReadUntil1):
        opcode = 0b11
        address = inst.address
        data_bsel = inst.bsel
    else:
        raise ValueError
    return (opcode << 14) | (address << 8) | data_bsel


class CSRInitializer(Module):
    def __init__(self, program, bus=None):
        if bus is None:
            bus = wishbone.Interface()
        self.bus = bus

        # # #

        assert isinstance(program[-1], InstEnd)
        program_e = [encode(inst) for inst in program]
        mem = Memory(16, len(program), init=program_e)
        self.specials += mem

        mem_port = mem.get_port()
        self.specials += mem_port

        fsm = FSM(reset_state="FETCH")
        self.submodules += fsm

        i_opcode = mem_port.dat_r[14:16]
        i_address = mem_port.dat_r[8:14]
        i_data = mem_port.dat_r[0:8]
        i_bsel = mem_port.dat_r[0:3]
        i_bsel_r = Signal(4)

        self.sync += [
            self.bus.adr.eq(i_address),
            self.bus.sel.eq(1),
            self.bus.dat_w.eq(i_data),
            i_bsel_r.eq(i_bsel)
        ]

        fsm.act("FETCH", NextState("DECODE"))
        fsm.act("DECODE",
            If(i_opcode == 0b00,
                NextState("END")
            ).Elif(i_opcode == 0b01,
                NextState("WRITE")
            ).Elif(i_opcode == 0b10,
                NextState("READ0")
            ).Elif(i_opcode == 0b11,
                NextState("READ1")
            )
        )
        fsm.act("WRITE",
            self.bus.cyc.eq(1),
            self.bus.stb.eq(1),
            self.bus.we.eq(1),
            If(self.bus.ack,
                NextValue(mem_port.adr, mem_port.adr + 1),
                NextState("FETCH")
            )
        )
        fsm.act("READ0",
            self.bus.cyc.eq(1),
            self.bus.stb.eq(1),
            If(self.bus.ack & ~((self.bus.dat_r >> i_bsel_r)[0]),
                NextValue(mem_port.adr, mem_port.adr + 1),
                NextState("FETCH")
            )
        )
        fsm.act("READ1",
            self.bus.cyc.eq(1),
            self.bus.stb.eq(1),
            If(self.bus.ack & (self.bus.dat_r >> i_bsel_r)[0],
                NextValue(mem_port.adr, mem_port.adr + 1),
                NextState("FETCH")
            )
        )
        fsm.act("END", NextState("END"))
