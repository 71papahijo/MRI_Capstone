import numpy as np
import matplotlib.pyplot as plt
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'marcos_client'))

import multiExp as mEx


# 169.254.138.35 
#169.254.44.172
#   169.254.44.172 
def multi_experiment():
    trig_delay = 10
    trig_length = 20000
    exp = mEx.MultiExperiment(boards={0: dict(ip="169.254.44.172", port = 11111, lo_freq=5, rx_t=3.125)})
                                    #   0: dict(ip="localhost", port = 11112, lo_freq=5, rx_t=3.125)})

    # exp = mEx.MultiExperiment(boards={0: dict(ip="...", port = ""),
    #                                   1: dict(ip="...", port = "")},
    #                         defaults=dict(lo_freq=5, rx_t=3.125))

    event_dict = {
        0: {
            "tx0": (
                        np.array([50, 130, 200, 360]),
                        np.array([0.5, 0, 0.5j, 0]),
                    ),
            "tx1": (np.array([450, 650]), np.array([1, 0])),
            "rx0_en": (np.array([400, 800]), np.array([1, 0])),  # adc 0
            "rx1_en": (np.array([400, 800]), np.array([1, 0])),  # adc 1 - gradx
        },
        # 1: {
        #     "rx0_en": (np.array([400, 800]), np.array([1, 0])),  # adc 0
        # }
    }

    exp.add_flodict(event_dict)
    # exp.plot_sequence()
    rxd, msgs = exp.run(trig_delay, trig_length)  # rxd is the array
    exp.close_server(only_if_sim=True)
    # exp.plot_sequence()

    # plt.plot(np.abs(rxd[0]["rx1"]))   # board 0, adc 1
    plt.figure()
    plt.plot(np.abs(rxd[0]["rx0"]), label="rx0")   # board 0, adc 0
    plt.plot(np.abs(rxd[0]["rx1"]), label="rx1")   # board 0, adc 1
    plt.legend()
    plt.savefig("rx_multi.png", dpi=120)
    print("Received data:")


if __name__ == "__main__":
    multi_experiment()
