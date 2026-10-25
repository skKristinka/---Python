"""TCP-клиент."""
import socket

from src.net.socket_wrapper import Socket


class TcpClient:
    """Устанавливает TCP-соединение с таймаутом."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def connect(self, host: str, port: int) -> Socket:
        """Подключиться и вернуть Socket. Бросает ConnectionError/TimeoutError."""
        raw = socket.create_connection((host, port), timeout=self.timeout)
        return Socket(raw)
