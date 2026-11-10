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
    exp = mEx.MultiExperiment(boards={0: dict(ip="169.254.44.172", port = 11111, lo_freq=5, rx_t=3.125, set_cic_shift=True),
                                      1: dict(ip="169.254.93.61", port = 11111, lo_freq=5, rx_t=3.125, set_cic_shift=True)})

    # exp = mEx.MultiExperiment(boards={0: dict(ip="...", port = ""),
    #                                   1: dict(ip="...", port = "")},
    #                         defaults=dict(lo_freq=5, rx_t=3.125))

    event_dict = {
        0: {
            "tx0": (np.array([400,500,600,700,900]), np.array([.25,.50,.75,1, 0]),),
            # "tx1": (np.array([400,500,600, 700,800]), np.array([.25,.5,.75,1, 0])),
            # "rx0_en": (np.array([400, 800]), np.array([1, 0])),  # adc 0
            "rx1_en": (np.array([400, 600]), np.array([1, 0])), 
        },
        1: {
            "rx0_en": (np.array([600, 800]), np.array([1, 0])),
            "rx1_en": (np.array([800, 1000]), np.array([1, 0])), 
        }
    }

    exp.add_flodict(event_dict)
    # exp.plot_sequence()
    rxd, msgs = exp.run(trig_delay, trig_length)  # rxd is the array
    exp.close_server(only_if_sim=True)
    # exp.plot_sequence()

    # plt.plot(np.abs(rxd[0]["rx1"]))   # board 0, adc 1
    plt.figure()
    # plt.plot(np.abs(rxd[0]["rx0"]), label="rx0")   # board 0, adc 0
    plt.plot(np.abs(rxd[0]["rx1"]), label="rx1_b0")   # board 0, adc 1
    plt.plot(np.abs(rxd[1]["rx1"]), label="rx1_b1")   # board 1, adc 1
    plt.plot(np.abs(rxd[1]["rx0"]), label="rx0_b1")   # board 1, adc 0
    plt.legend()
    plt.savefig("rx_multi_raw.png", dpi=120)
    print("Received data:")




       # One aligned plot
    fig, ax = plt.subplots(figsize=(12, 6))
    ax_tx = ax.twinx()

    rx_t_us = 3.125  # Same rx_t configured for both boards

    # RX channels and their corresponding enable signals
    rx_channels = [
        (0, "rx1", "rx1_en"),
        (1, "rx0", "rx0_en"),
        (1, "rx1", "rx1_en"),
    ]

    # Plot RX data during its actual enabled window
    for board, channel, enable_signal in rx_channels:

        times, values = event_dict[board][enable_signal]

        # Find the beginning and end of the enabled interval
        active_indices = np.where(values == 1)[0]
        start_idx = active_indices[0]
        start_time = times[start_idx]

        stop_indices = np.where(
            (np.arange(len(values)) > start_idx) & (values == 0)
        )[0]

        if len(stop_indices) == 0:
            raise ValueError(f"No disable event found for {enable_signal}")

        end_time = times[stop_indices[0]]

        data = np.abs(rxd[board][channel])

        # Time corresponding to each received sample
        t = start_time + np.arange(len(data)) * rx_t_us

        ax.plot(t, data, label=f"{channel}_b{board}")

        print(
            f"Board {board} {channel}: "
            f"{start_time}-{end_time} us, "
            f"{len(data)} samples"
        )

    # Plot TX directly from event_dict
    for board, events in event_dict.items():
        for signal, (times, values) in events.items():

            if signal.startswith("tx"):
                ax_tx.step(
                    times,
                    values,
                    where="post",
                    linestyle="--",
                    linewidth=2,
                    label=f"{signal}_b{board}"
                )

    # Axis formatting
    ax.set_xlabel("Experiment time (us)")
    ax.set_ylabel("RX magnitude")
    ax_tx.set_ylabel("TX state")
    ax_tx.set_ylim(-0.1, 1.2)

    # Overall experiment time range
    all_times = [
        time
        for events in event_dict.values()
        for times, values in events.values()
        for time in times
    ]

    ax.set_xlim(min(all_times), max(all_times))

    # Combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax_tx.get_legend_handles_labels()

    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    ax.grid(True)
    fig.tight_layout()
    fig.savefig("rx_multi_aligned.png", dpi=120)
    plt.show()


if __name__ == "__main__":
    multi_experiment()
