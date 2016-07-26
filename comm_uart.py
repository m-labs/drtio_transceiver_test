import logging
import serial


logger = logging.getLogger(__name__)


class CommUART:
    msg_type = {
        "write": 0x01,
        "read":  0x02
    }
    def __init__(self, port, baudrate=115200):
        self.port = serial.serial_for_url(port, baudrate)

    def close(self):
        self.port.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def read(self, addr, length=None):
        data = []
        length_int = 1 if length is None else length
        self.port.write([self.msg_type["read"], length_int])
        self.port.write((addr//4).to_bytes(4, byteorder="big"))
        for i in range(length_int):
            value = int.from_bytes(self.port.read(4), "big")
            logger.debug("read %08x @ %08x", value, addr + 4*i)
            if length is None:
                return value
            data.append(value)
        return data

    def write(self, addr, data):
        data = data if isinstance(data, list) else [data]
        length = len(data)
        offset = 0
        while length:
            size = min(length, 255)
            self.port.write([self.msg_type["write"], size])
            self.port.write(((addr+offset)//4).to_bytes(4, byteorder="big"))
            for i, value in enumerate(data[offset:offset+size]):
                self.port.write(value.to_bytes(4, byteorder="big"))
                logger.debug("write %08x @ %08x", value, addr + offset, 4*i)
            offset += size
            length -= size
