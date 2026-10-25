"""TCP-сервер: bind, listen, accept."""
import socket
from typing import Optional, Tuple


class TcpServer:
    """Слушающий сокет."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None

    def start(self) -> None:
        """Занять порт и начать слушать."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen()

    def accept(self) -> Tuple[socket.socket, tuple]:
        """Принять одно соединение (блокирующий вызов)."""
        return self._sock.accept()

    def stop(self) -> None:
        """Закрыть слушающий сокет (освободить порт)."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None
