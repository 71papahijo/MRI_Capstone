"""Python port of iface.cpp for the keya branch: TCP and MessagePack interface.

Requires ``msgpack`` (the same dependency used by marcos_client). The
hardware object is injected because hardware.cpp has not been ported. Its
``run_request(action)`` method should call ``action.add_result(name, value)``
for each command it handles and may call the add_error/warning/info methods.
The object may optionally implement ``emergency_stop()``.

This module does not initialize hardware or start a server on import.
"""

from __future__ import annotations

import logging
import socket
from typing import Any

import msgpack
from version import VERSION_MAJOR, VERSION_MINOR, VERSION_DEBUG


LOG = logging.getLogger(__name__)

SERVER_VERSION_UINT = (
    ((VERSION_MAJOR << 16) & 0xFF0000)
    | ((VERSION_MINOR << 8) & 0xFF00)
    | (VERSION_DEBUG & 0xFF)
)
SERVER_VERSION_STR = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_DEBUG}"

MARCOS_REQUEST = 0
MARCOS_EMERGENCY_STOP = 1
MARCOS_CLOSE_SERVER = 2
MARCOS_REPLY = 128
MARCOS_REPLY_ERROR = 129

MAX_SIZE = 32 * 1024 * 1024
MAX_NODES = 8192


def version_str(version: int) -> str:
    """Decode the three low version bytes, like version_str in iface.cpp."""
    return f"{(version >> 16) & 255}.{(version >> 8) & 255}.{version & 255}"


def _uint(value: Any, name: str) -> int:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"{name} must be a 32-bit unsigned integer")
    return value


def _check_nodes(root: Any) -> None:
    """Bound the decoded tree, including map keys, before handling a packet."""
    pending = [root]
    count = 0
    while pending:
        value = pending.pop()
        count += 1
        if count > MAX_NODES:
            raise ValueError("MessagePack request exceeds the node limit")
        if isinstance(value, (list, tuple)):
            pending.extend(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                pending.extend((key, item))


class ServerAction:
    """One request and its six-element MaRCoS reply."""

    def __init__(self, request_root: Any):
        if not isinstance(request_root, (list, tuple)) or len(request_root) != 5:
            raise ValueError("MaRCoS request must be a five-element array")
        self.request_type = _uint(request_root[0], "request type")
        self.reply_index = _uint(request_root[1], "packet index")
        self.request_version = _uint(request_root[3], "protocol version")
        self.request_data = request_root[4]
        if not isinstance(self.request_data, dict):
            raise ValueError("MaRCoS command payload must be a map")

        self.results: dict[str, Any] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self._check_version()

    def _check_version(self) -> None:
        version = self.request_version
        prefix = f"Client version {version_str(version)}"
        suffix = f"server version {SERVER_VERSION_STR}"
        if (version >> 16) & 255 != VERSION_MAJOR:
            self.add_error(f"{prefix} significantly different from {suffix}")
        elif (version >> 8) & 255 != VERSION_MINOR:
            self.add_warning(f"{prefix} different from {suffix}")
        elif version & 255 != VERSION_DEBUG:
            self.add_info(f"{prefix} differs slightly from {suffix}")

    def command_count(self) -> int:
        return len(self.request_data)

    def get_command(self, name: str) -> tuple[Any, int]:
        """Return (argument, status): 1 present, 0 absent, -1 nil."""
        if name not in self.request_data:
            return None, 0
        value = self.request_data[name]
        return (value, -1 if value is None else 1)

    def add_result(self, name: str, value: Any) -> None:
        """Add a command result to the fourth (index 4) reply field."""
        self.results[name] = value

    def add_error(self, message: str) -> None:
        self.errors.append(str(message))

    def add_warning(self, message: str) -> None:
        self.warnings.append(str(message))

    def add_info(self, message: str) -> None:
        self.infos.append(str(message))

    def process_request(self, hardware: Any) -> bool:
        """Handle packet; return True when the server should shut down."""
        if self.request_type == MARCOS_EMERGENCY_STOP:
            stop = getattr(hardware, "emergency_stop", None)
            if stop is None:
                self.add_error("Emergency stop not yet implemented!")
            else:
                try:
                    stop()
                except Exception as exc:
                    LOG.exception("Emergency stop failed")
                    self.add_error(f"Emergency stop failed: {exc}")
            self.add_warning("Tried to carry out emergency stop!")
            return False
        if self.request_type == MARCOS_CLOSE_SERVER:
            self.add_info("Shutting down server.")
            return True

        # In C++, any other packet type is forwarded to hardware as a request.
        try:
            hardware.run_request(self)
        except RuntimeError as exc:
            self.add_error(str(exc))
        return False

    def finish_reply(self) -> list[Any]:
        messages = {}
        if self.errors:
            messages["errors"] = self.errors
        if self.warnings:
            messages["warnings"] = self.warnings
        if self.infos:
            messages["infos"] = self.infos
        return [
            MARCOS_REPLY_ERROR if self.request_type == MARCOS_EMERGENCY_STOP else MARCOS_REPLY,
            (self.reply_index + 1) & 0xFFFFFFFF,
            0,
            SERVER_VERSION_UINT,
            self.results,
            messages,
        ]


class Iface:
    """Single-threaded TCP server, accepting sequential client connections."""

    def __init__(self, hardware: Any, port: int = 11111, host: str = "0.0.0.0"):
        self.hardware = hardware
        self.port = port
        self.host = host
        self._server: socket.socket | None = None

    def run_stream(self) -> None:
        """Serve MessagePack packets until a close-server packet arrives."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            self._server = server
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            server.bind((self.host, self.port))
            server.listen(10)
            running = True
            try:
                while running:
                    conn, _ = server.accept()
                    with conn:
                        unpacker = msgpack.Unpacker(
                            raw=False,
                            max_buffer_size=MAX_SIZE,
                            max_array_len=MAX_NODES,
                            max_map_len=MAX_NODES,
                            strict_map_key=False,
                        )
                        while running:
                            try:
                                chunk = conn.recv(8192)
                                if not chunk:
                                    break
                                unpacker.feed(chunk)
                                for request in unpacker:
                                    _check_nodes(request)
                                    action = ServerAction(request)
                                    running = not action.process_request(self.hardware)
                                    conn.sendall(msgpack.packb(action.finish_reply(), use_bin_type=True))
                                    if not running:
                                        break
                            except (ValueError, msgpack.exceptions.UnpackException, BufferError) as exc:
                                LOG.warning("Invalid MessagePack request: %s", exc)
                                break
                            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                                LOG.info("Client disconnected: %s", exc)
                                break
            finally:
                self._server = None


def run_stream(hardware: Any, port: int = 11111, host: str = "0.0.0.0") -> None:
    """Convenience entry point for an injected Python hardware object."""
    Iface(hardware, port=port, host=host).run_stream()


# marcos_server.py imports the C++-style lowercase class name.
iface = Iface