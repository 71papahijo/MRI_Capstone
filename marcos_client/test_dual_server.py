# run_multi_sim.py
import os, socket, subprocess, time, sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'marcos_client'))
import multiExp as mEx

# Same paths test_base.py uses; adjust to match
from test_base import marga_sim_path

from pathlib import Path

SIM_BIN = str(
    Path(__file__).resolve().parents[1]
    / "marga" / "build" / "marga_sim"
)

# Hardcoded for 2 boards
SIMS = {
    0: dict(ip="localhost", port=11111, mem="/tmp/marcos_server_mem_0", csv="/tmp/marga_sim_0.csv"),
    1: dict(ip="localhost", port=11112, mem="/tmp/marcos_server_mem_1", csv="/tmp/marga_sim_1.csv"),
}


def start_sims():
    subprocess.call(["killall", "marga_sim"], stderr=subprocess.DEVNULL)  # once, before starting either
    procs = {}
    for bid, s in SIMS.items():
        subprocess.call(["fallocate", "-l", "516KiB", s["mem"]])
        env = dict(os.environ, MARGA_PORT=str(s["port"]), MARGA_MEM=s["mem"])
        procs[bid] = subprocess.Popen([SIM_BIN, "csv", s["csv"]], env=env)

    for bid, s in SIMS.items():
        for _ in range(100):
            try:
                socket.create_connection((s["ip"], s["port"]), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError(f"sim {bid} never started listening on {s['port']}")
    return procs


def multi_experiment():
    exp = mEx.MultiExperiment(boards={0: dict(ip="localhost", port = 11111, lo_freq=5, rx_t=3.125),
                                  1: dict(ip="localhost", port = 11112, lo_freq=5, rx_t=3.125)})

    event_dict = {
        0: {
            "tx0": (np.array([50, 130, 200, 360]), np.array([0.5, 0, 0.5j, 0])),
            "rx1_en": (np.array([400, 800]), np.array([1, 0])),
        },
        1: {
            "tx0": (np.array([50, 130, 200, 360]), np.array([0.5, 0, 0.5j, 0])),
            "rx0_en": (np.array([400, 800]), np.array([1, 0])),
        },
    }
    exp.add_flodict(event_dict)
    exp.plot_sequence()
    rxd, msgs = exp.run()
    exp.close_server(only_if_sim=True)

    plt.figure()
    plt.plot(np.abs(rxd[0]["rx1"]), label="board 0, adc 1")
    plt.plot(np.abs(rxd[1]["rx0"]), label="board 1, adc 0")
    plt.legend()

    for i in plt.get_fignums():
        plt.figure(i).savefig(f"fig{i}.png", dpi=120)

    plt.close("all")
    

    


if __name__ == "__main__":
    procs = start_sims()
    try:
        multi_experiment()
    finally:
        for p in procs.values():
            p.terminate()