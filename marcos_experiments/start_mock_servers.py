"""Start mock MaRCoS servers on several local ports (default 11111 and 11112).

The real Verilator simulation hardcodes port 11111, so it cannot be run twice.
These mocks accept connections and send a valid reply to every request, which
is enough to construct Experiment objects and test the multi-board wiring.
They do not simulate hardware, so run_seq returns no RX data.

Usage:
    python start_mock_servers.py                 # ports 11111 11112
    python start_mock_servers.py 11111 11112 11113
"""
import socket
import sys
import threading

import msgpack

REPLY_PKT = 128
SERVER_VERSION = (1 << 16) | (0 << 8) | 5


def make_reply(request):
    packet_idx = request[1] if len(request) > 1 else 0
    data = request[4] if len(request) > 4 and isinstance(request[4], dict) else {}

    reply_data = {}
    for key in data:
        if key == "are_you_real":
            reply_data[key] = "simulation"
        elif key == "halt_and_reset":
            reply_data[key] = True
        else:
            reply_data[key] = 0

    return [REPLY_PKT, packet_idx, 0, SERVER_VERSION, reply_data, {}]


def handle_client(conn, port):
    unpacker = msgpack.Unpacker(raw=False)
    with conn:
        while True:
            buf = conn.recv(4096)
            if not buf:
                break
            unpacker.feed(buf)
            for request in unpacker:
                if request[0] == 2:  # close_server_pkt
                    return
                conn.sendall(msgpack.packb(make_reply(request)))
    print(f"[port {port}] client disconnected")


def serve(port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen()
    print(f"[port {port}] mock MaRCoS server listening")
    while True:
        conn, addr = srv.accept()
        print(f"[port {port}] client connected from {addr}")
        threading.Thread(target=handle_client, args=(conn, port), daemon=True).start()


def main():
    ports = [int(p) for p in sys.argv[1:]] or [11111, 11112]
    for port in ports:
        threading.Thread(target=serve, args=(port,), daemon=True).start()
    print("Press Ctrl+C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping mock servers.")


if __name__ == "__main__":
    main()
