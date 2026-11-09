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
from concurrent.futures import ThreadPoolExecutor
import time

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

        # Compile all experiments first
        for board_id, exp in self.exps.items():
            if not exp._seq_compiled:
                if board_id == 0:
                    exp.compile(trig_delay=trig_delay, trig_length=trig_length)
                else:
                    exp.compile()

        # Separate controller and followers
        controller = self.exps[0]
        followers = {
            board_id: exp
            for board_id, exp in self.exps.items()
            if board_id != 0
        }

        # Run followers in background threads
        with ThreadPoolExecutor(max_workers=max(1, len(followers))) as executor:

            futures = {}

            for board_id, exp in followers.items():
                print(f"\nStarting follower board {board_id}: {type(exp).__name__}")
                futures[board_id] = executor.submit(exp.run)

            # Give followers time to send their run commands and arm
            time.sleep(0.2)

            # Run controller in main thread (sends trigger)
            print(f"\nRunning controller board 0: {type(controller).__name__}")

            try:
                rxd[0], msgs[0] = controller.run()

            except Exception as e:
                print(f"Controller failed: {e}")
                print("Machine code:", getattr(controller, "_machine_code", None))
                raise

            # Collect follower results
            for board_id, future in futures.items():
                try:
                    rxd[board_id], msgs[board_id] = future.result()

                except Exception as e:
                    print(f"Follower board {board_id} failed: {e}")
                    print("Machine code:", getattr(followers[board_id], "_machine_code", None))
                    raise

        return rxd, msgs

    def close_server(self, only_if_sim=False):
        for exp in self.exps.values():
            exp.close_server(only_if_sim=only_if_sim)