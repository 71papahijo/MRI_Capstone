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

import experimentController as exCtrl
import experimentFollower as exFol
import experimentExternal as exExt


'''
    exp = mEx.MultiExperiment(boards={0: dict(ip="...", lo_freq=5, rx_t=3.125),
                              1: dict(ip="...", lo_freq=5, rx_t=3.125)})
'''


class MultiExperiment:
    def __init__(self, boards, defaults = None):
        defaults = defaults or {}
        self.boards = boards
        self.event_dict = {}
        self.exps = {} # list of experiments

        for board_id, args in boards.items():
            self.event_dict[board_id] = {}
            if board_id == 0:  # main system synchronizer
                #self.exps[board_id] = exCtrl.ExperimentController(**{**defaults, **args})
                self.exps[board_id] = exCtrl.ExperimentController(**{**defaults, **args})
            else: # recieve synchronization signals and send responses
                self.exps[board_id] = exFol.ExperimentFollower(**{**defaults, **args})

    def add_intdict(self, intdict, append=True):
        for exp_id, exp in self.exps.items():
            if exp_id in intdict:
                exp.add_intdict(intdict[exp_id], append)

    def add_flodict(self, flodict, append=True):
        for exp_id, exp in self.exps.items():
            if exp_id in flodict:
                exp.add_flodict(flodict[exp_id], append)
                print(f"Added flodict for board {exp_id}")
                print(flodict[exp_id])

    def plot_sequence(self):
        return {
            board_id: exp.plot_sequence()
            for board_id, exp in self.exps.items()
        }
    def compile(self, trig_delay=0, trig_length=2):
        print(f"Compiling multi-experiment with trig_delay={trig_delay} and trig_length={trig_length}")
        for board_id, e in self.exps.items():
            if board_id == 0:
                print(f"Compiling board {board_id} with trig_delay={trig_delay} and trig_length={trig_length}")
                e.compile(trig_delay=trig_delay, trig_length=trig_length)
            else:
                e.compile()

    def run(self, trig_delay, trig_length):
        rxd = {}
        msgs = {}
        print(f"Running multi-experiment with trig_delay={trig_delay} and trig_length={trig_length}")

        for e in self.exps.values():
            if not e._seq_compiled:
                e.compile(trig_delay = trig_delay, trig_length = trig_length)

        for board_id, exp in self.exps.items():
            print(f"\nRunning board {board_id}: {type(exp).__name__}")

            try:
                # Run normally; compilation happens through the usual path.
                rxd[board_id], msgs[board_id] = exp.run()

            except Exception as e:
                print(f"Board {board_id} failed: {e}")
                print("Machine code:", getattr(exp, "_machine_code", None))
                raise

        return rxd, msgs



    












    '''
    def run(self):
            """ compile the TX and grad data, send everything over.
            Returns the resultant data """
    
            if not self._seq_compiled:
                self.compile()
    
            if self._flush_old_rx:
                rx_data_old, _ = sc.command({'read_rx': 0}, self._s)
                # TODO: do something with RX data previously collected by the server
    
            bytecode = self._machine_code.tobytes()
            log.info("Sending run_seq (%d bytes) to MaRCoS", len(bytecode))
            try:
                rx_data, msgs = sc.command({'run_seq': bytecode}, self._s)
            except (OSError, ConnectionError) as exc:
                raise ConnectionError(
                    f"MaRCoS closed while running the sequence ({exc}). "
                    "Do not Ping during a scan. On the Red Pitaya, watch marcos_server for an MPack error."
                ) from exc
    
            rxd = rx_data[4]['run_seq']
            rxd_iq = {}
    
            # (1 << 24) just for the int->float conversion to be reasonable - exact value doesn't matter for now
            rx0_norm_factor = self._rx0_cic_factor / (1 << 24)
            rx1_norm_factor = self._rx0_cic_factor / (1 << 24)
    
            try:
                rxd_iq['rx0'] = rx0_norm_factor * ( np.array(rxd['rx0_i']).astype(np.int32).astype(float) + \
                                 1j * np.array(rxd['rx0_q']).astype(np.int32).astype(float) )
            except (KeyError, TypeError):
                pass
    
            try:
                rxd_iq['rx1'] = rx1_norm_factor * ( np.array(rxd['rx1_i']).astype(np.int32).astype(float) + \
                                 1j * np.array(rxd['rx1_q']).astype(np.int32).astype(float) )
            except (KeyError, TypeError):
                pass
    
            return rxd_iq, msgs
    
    
    '''

    def close_server(self, only_if_sim=False):
        
        for exp in self.exps.values():
            exp.close_server(only_if_sim=only_if_sim)
