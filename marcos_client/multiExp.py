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

    def plot_sequence(self):
        return {
            board_id: exp.plot_sequence()
            for board_id, exp in self.exps.items()
        }

    def run(self):
        rxd = {}
        msgs = {}
        for board_id, exp in self.exps.items():
            rxd[board_id], msgs[board_id] = exp.run()
        return rxd, msgs

    def close_server(self, only_if_sim=False):
        for exp in self.exps.values():
            exp.close_server(only_if_sim=only_if_sim)
