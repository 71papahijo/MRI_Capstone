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

import experimentExternal as exEl


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
            if board_id == 0: # TODO: later on this will be slightly different as it will need to control timing down the line 
                self.exps[board_id] = exEl.ExperimentExternal(**{**defaults, **args})
            else:
                self.exps[board_id] = exEl.ExperimentExternal(**{**defaults, **args})

    def add_intdict(self, intdict, append=True):
        for exp_id, exp in self.exps.items():
            if exp_id in intdict:
                exp.add_intdict(intdict[exp_id], append)

    def add_flodict(self, flodict, append=True):
        for exp_id, exp in self.exps.items():
            if exp_id in flodict:
                exp.add_flodict(flodict[exp_id], append)
