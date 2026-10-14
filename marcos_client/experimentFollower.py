import socket, time, warnings
import numpy as np
import matplotlib.pyplot as plt

import local_config as marcos_cfg
import grad_board as gb
import server_comms as sc
import marcompile as fc
# import common.logger as logger
# log = logger.get_logger()
import logging
log = logging.getLogger(__name__)

import pdb
st = pdb.set_trace

import experiment as exp

class ExperimentFollower(exp.Experiment) :
    '''
    Follower for participating in experiments coordinated by an ExperimentController.
    '''
    
    def __init__(self,
        ip = None,
        port = None,
        lo_freq=1, # MHz
        rx_t=3.125, # us; multiples of 1/122.88, such as 3.125, are exact, others will be rounded to the nearest multiple of the 122.88 MHz clock
        seq_dict=None,
        seq_csv=None,
        rx_lo=0, # which of internal NCO local oscillators (LOs), out of 0, 1, 2, to use for each channel
        grad_max_update_rate=0.2, # MSPS, across all channels in parallel, best-effort
        gpa_fhdo_offset_time=0, # when GPA-FHDO is used, offset the Y, Z and Z2 gradient times by 1x, 2x and 3x this value to emulate 'simultaneous' updates
        print_infos=True, # show server info messages
        assert_errors=True, # halt on server errors
        init_gpa=False, # initialise the GPA (will reset its outputs when the Experiment object is created)
        initial_wait=None, # initial pause before experiment begins - required to configure the LOs and RX rate; must be at least a few us. Is suitably set based on grad_max_update_rate by default.
        auto_leds=True, # automatically scan the LED pattern from 0 to 255 as the sequence runs (set to off if you wish to manually control the LEDs)
        prev_socket=None, # previously-opened socket, if want to maintain status etc
        fix_cic_scale=True, # scale the RX data precisely based on the rate being used; otherwise a 2x variation possible in data amplitude based on rate
        set_cic_shift=False, # program the CIC internal bit shift to maintain the gain within a factor of 2 independent of rate; required if the open-source CIC is used in the design
        allow_user_init_cfg=False, # allow user-defined alteration of marga configuration set by init, namely RX rate, LO properties etc; see the compile() method for details
        halt_and_reset=False, # upon connecting to the server, halt any existing sequences that may be running
        flush_old_rx=False, # when debugging or developing new code, you may accidentally fill up the RX FIFOs - they will not automatically be cleared in case there is important data inside. Setting this true will always read them out and clear them before running a sequence. More advanced manual code can read RX from existing sequences.
    ):

        # create socket early so that destructor works
        self._close_socket = True
        self._s = None
        if prev_socket is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                log.info("Connecting to MaRCoS at %s:%s", ip, port)
                sock.connect((ip, port))
            except OSError as exc:
                sock.close()
                log.error(
                    "MaRCoS connection failed (%s:%s): %s",
                    ip,
                    port,
                    exc,
                )
                raise ConnectionError(
                    f"Cannot reach MaRCoS at {ip}:{port}: {exc}"
                ) from exc
            sock.settimeout(None)
            self._s = sock
        else:
            self._s = prev_socket
            self._close_socket = False # do not close previous socket

        self.set_lo_freq(lo_freq)

        if not hasattr(rx_t, "__len__"):
            rx_t = rx_t, rx_t # extend to 2 elements

        # TODO: enable variable rates during a single TR
        self._rx_divs = np.round(np.array(rx_t) * marcos_cfg.fpga_clk_freq_MHz).astype(np.uint32)
        self._rx_ts = self._rx_divs / marcos_cfg.fpga_clk_freq_MHz

        if not hasattr(rx_lo, "__len__"):
            rx_lo = rx_lo, rx_lo # extend to 2 elements
        self._rx_lo = rx_lo

        assert marcos_cfg.grad_board in ('ocra1', 'gpa-fhdo'), "Unknown gradient board!"
        if marcos_cfg.grad_board == 'ocra1':
            gradb_class = gb.OCRA1
            self._gpa_fhdo_offset_time = 0
        else:
            gradb_class = gb.GPAFHDO
            self._gpa_fhdo_offset_time = gpa_fhdo_offset_time
        self.gradb = gradb_class(self.server_command, grad_max_update_rate)

        if initial_wait is None:
            # auto-set the initial wait to be long enough for initial gradient configuration to finish, plus 1us for miscellaneous startup
            self._initial_wait = 1 + 1/grad_max_update_rate

        self._auto_leds = auto_leds

        assert (seq_csv is None) or (seq_dict is None), "Cannot supply both a sequence dictionary and a CSV file."
        self._csv = None
        self._seq = None
        if seq_dict is not None:
            self.add_flodict(seq_dict)
        elif seq_csv is not None:
            self._csv = seq_csv # None unless a CSV was supplied

        self._print_infos = print_infos
        self._assert_errors = assert_errors

        if init_gpa:
            try:
                self.gradb.init_hw()
            except (OSError, ConnectionError) as exc:
                raise ConnectionError(
                    f"GPA initialization failed on {ip}:{port}: {exc}. "
                    "Turn off Initialize GPA in Settings if no gradient board is attached."
                ) from exc

        if halt_and_reset:
            try:
                halted = sc.command({'halt_and_reset': 0}, self._s)[0][4]['halt_and_reset']
            except (OSError, ConnectionError) as exc:
                raise ConnectionError(
                    f"MaRCoS halt_and_reset failed on {ip}:{port}: {exc}"
                ) from exc
            assert halted, "Could not halt the execution of an existing sequence. Please file a bug report."

        self._fix_cic_scale = fix_cic_scale
        self._set_cic_shift = set_cic_shift
        self._flush_old_rx = flush_old_rx
        self._allow_user_init_cfg = allow_user_init_cfg
