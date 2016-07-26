from migen.build.generic_platform import *


def get_ttl_extension():
	r = []
	for i in range(32):
		lan = i//2
		name = "LPC:LA{:02d}_".format(lan)
		if lan in {0, 1, 17, 18}:
			name += "CC_"
		if i % 2:
			name += "N"
		else:
			name += "P"
		r.append(("ttl", i, Pins(name), IOStandard("LVCMOS25")))
	return r

ttl_extension = get_ttl_extension()
