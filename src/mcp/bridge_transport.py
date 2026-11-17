"""TCP framing for an explicitly selected Rhino bridge endpoint."""
from dataclasses import dataclass
import socket


@dataclass(frozen=True)
class BridgeTransport:
    host: str
    port: int

    def __call__(self, payload: bytes, timeout: float = 60.0) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout)
            connection.connect((self.host, self.port))
            connection.sendall(len(payload).to_bytes(4, "big"))
            connection.sendall(payload)
            header = self._receive(connection, 4, "header")
            length = int.from_bytes(header, "big")
            return self._receive(connection, length, "body").decode("utf-8")

    @staticmethod
    def _receive(connection, length, part):
        data = bytearray()
        while len(data) < length:
            chunk = connection.recv(min(16384, length - len(data)))
            if not chunk:
                raise ConnectionError(f"Bridge closed connection while reading response {part}.")
            data.extend(chunk)
        return data
