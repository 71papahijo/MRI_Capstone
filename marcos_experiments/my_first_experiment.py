import numpy as np
import matplotlib.pyplot as plt
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'marcos_client'))

import experiment as ex


def my_first_experiment():
    exp = ex.Experiment(lo_freq=5, rx_t=3.125)

    event_dict = {
        "tx0": (
            np.array([50, 130, 200, 360]),
            np.array([0.5, 0, 0.5j, 0]),
        ),  # tx0_i, tx0_q:: -1 to 1; -j to j
        # "tx1": (np.array([500, 700]), np.array([0.2, 0])),
        # "grad_vx": (np.array([200, 700]), np.array([0.2, 0])),
        # "grad_vy": (np.array([300, 700]), np.array([0.2, 0])),
        # "grad_vz": (np.array([500, 700]), np.array([0.2, 0])),
        "tx1": (np.array([450, 650]), np.array([1, 0])),
        "rx0_en": (np.array([400, 800]), np.array([1, 0])),  # adc 0
        "rx1_en": (np.array([400, 800]), np.array([1, 0])),  # adc 1 - gradx
    }
    exp.add_flodict(event_dict)
    exp.plot_sequence()

    rxd, msgs = exp.run()  # rxd is the array
    print("run finished", {k: v.shape for k, v in rxd.items()})
    exp.close_server(only_if_sim=True)

    plt.figure()
    for i in plt.get_fignums():
        plt.figure(i).savefig(f"fig{i}.png", dpi=120)
    plt.show()

    plt.figure()
    plt.plot(np.abs(rxd["rx0"]), label="rx0")
    plt.plot(np.abs(rxd["rx1"]), label="rx1")
    plt.legend()
    plt.savefig("rx.png", dpi=120)


if __name__ == "__main__":
    my_first_experiment()
