"""TCP-клиент."""
import socket
import ssl

from src.net.socket_wrapper import Socket


class TcpClient:
    """Устанавливает TCP-соединение (опционально TLS) с таймаутом."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def connect(self, host: str, port: int, use_tls: bool = False) -> Socket:
        """Подключиться и вернуть Socket.

        Бросает TimeoutError (таймаут) и ConnectionError (отказ, DNS, TLS).
        """
        try:
            raw = socket.create_connection((host, port), timeout=self.timeout)
        except socket.gaierror as exc:
            raise ConnectionError(f"Не удалось определить адрес хоста {host!r}") from exc
        except (TimeoutError, ConnectionError):
            raise
        except OSError as exc:
            raise ConnectionError(f"Не удалось подключиться к {host}:{port}: {exc}") from exc
        if use_tls:
            raw = self._wrap_tls(raw, host)
        return Socket(raw)

    @staticmethod
    def _wrap_tls(raw: socket.socket, host: str) -> socket.socket:
        """Включить TLS поверх соединения (проверка сертификата включена)."""
        try:
            return ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        except TimeoutError:
            raw.close()
            raise
        except OSError as exc:
            raw.close()
            raise ConnectionError(f"Ошибка TLS-соединения с {host}: {exc}") from exc
