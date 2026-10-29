"""TCP-сервер: bind, listen, accept."""
import socket
from typing import Optional, Tuple


class TcpServer:
    """Слушающий сокет с коротким таймаутом accept (чтобы цикл мог проверять флаг остановки)."""

    ACCEPT_TIMEOUT = 0.2

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None

    def start(self) -> None:
        """Занять порт и начать слушать. Бросает ConnectionError, если порт недоступен."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.host, self.port))
            sock.listen()
        except OSError as exc:
            sock.close()
            raise ConnectionError(f"Не удалось занять порт {self.port}: {exc}") from exc
        sock.settimeout(self.ACCEPT_TIMEOUT)
        self._sock = sock
        self.port = sock.getsockname()[1]

    def accept(self) -> Optional[Tuple[socket.socket, tuple]]:
        """Принять соединение; None, если за таймаут никто не подключился.

        Бросает OSError, если сервер остановлен.
        """
        sock = self._sock
        if sock is None:
            raise OSError("Сервер остановлен")
        try:
            return sock.accept()
        except TimeoutError:
            return None

    def stop(self) -> None:
        """Закрыть слушающий сокет (освободить порт)."""
        sock, self._sock = self._sock, None
        if sock is not None:
            sock.close()
