"""Обёртка над сокетом с поддержкой контекстного менеджера."""
import socket
from typing import Optional

from src.interfaces import Transport


class Socket(Transport):
    """Сокет, который закрывается через with."""

    def __init__(self, sock: socket.socket):
        self._sock: Optional[socket.socket] = sock

    def __enter__(self) -> "Socket":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        """Закрыть сокет."""
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def send_all(self, data: bytes) -> None:
        """Отправить все данные."""
        self._sock.sendall(data)

    def recv(self, size: int) -> bytes:
        """Принять до size байт."""
        return self._sock.recv(size)
