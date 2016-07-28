from artiq.experiment import *


class Line(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.leds = [self.get_device("led" + str(i)) for i in range(8)]
        self.remote_leds = [self.get_device("remote_led" + str(i)) for i in range(8)]

    @kernel
    def run(self):
        self.core.reset()
        while True:
            with parallel:
                for led in self.leds:
                    led.pulse(50*ms)
                for led in self.remote_leds:
                    led.pulse(50*ms)
