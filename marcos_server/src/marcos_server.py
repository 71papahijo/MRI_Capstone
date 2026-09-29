# Top-level MaRCoS server file.
#
# When compiling Verilator simulation, replace this with
# marga_sim_main.py in the marga library.
#
# Overall operation should remain compatible between both, apart from
# the extra Verilator-related objects in marga_sim_main which are
# made use of in hardware.py for emulating PS<->PL communication.


import time

from version import VERSION_MAJOR, VERSION_MINOR, VERSION_DEBUG
from hardware import hardware
from iface import iface


SERVER_VERSION_UINT = None
SERVER_VERSION_STR = None

hw = None
ifa = None


def main(argc, argv):
    global SERVER_VERSION_UINT
    global SERVER_VERSION_STR
    global hw
    global ifa

    print(
        "MaRCoS server, "
        + time.strftime("%b %d %Y")
        + " "
        + time.strftime("%H:%M:%S")
    )

    # Global version string creation
    SERVER_VERSION_STR = (
            str(VERSION_MAJOR)
            + "."
            + str(VERSION_MINOR)
            + "."
            + str(VERSION_DEBUG)
    )

    SERVER_VERSION_UINT = (
            ((VERSION_MAJOR << 16) & 0xff0000)
            | ((VERSION_MINOR << 8) & 0xff00)
            | (VERSION_DEBUG & 0xff)
    )

    print("Server version " + SERVER_VERSION_STR)

    hw = hardware()
    ifa = iface(hw)
    ifa.run_stream()

    # Cleanup
    del hw
    del ifa


if __name__ == "__main__":
    import sys
    main(len(sys.argv), sys.argv)