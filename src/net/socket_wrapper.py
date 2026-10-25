"""Обёртка над сокетом с поддержкой контекстного менеджера."""
import socket
from typing import Optional

from src.interfaces import Transport


class Socket(Transport):
    """Сокет, который гарантированно закрывается через with."""

    def __init__(self, sock: socket.socket):
        self._sock: Optional[socket.socket] = sock

    def __enter__(self) -> "Socket":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _require(self) -> socket.socket:
        """Вернуть живой сокет или бросить ConnectionError."""
        if self._sock is None:
            raise ConnectionError("Сокет уже закрыт")
        return self._sock

    def close(self) -> None:
        """Закрыть сокет (повторный вызов безопасен)."""
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def send_all(self, data: bytes) -> None:
        """Отправить все данные."""
        self._require().sendall(data)

    def recv(self, size: int) -> bytes:
        """Принять до size байт (пустые байты — соединение закрыто)."""
        return self._require().recv(size)
