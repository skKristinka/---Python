"""Общие фикстуры: тестовый TCP-сервер со сценариями ответов."""
import socket
import threading
import time

import pytest


class ScriptedServer:
    """TCP-сервер для тестов: на i-е соединение отвечает i-м сценарием.

    Сценарий — список: байты отправляются, число означает паузу в секундах.
    После сценария соединение закрывается. Полученные запросы — в self.requests.
    """

    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.requests = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen()
        self.port = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self):
        """Запустить поток сервера."""
        self._thread.start()

    def close(self):
        """Закрыть слушающий сокет."""
        self._sock.close()

    def _serve(self):
        for script in self.scripts:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(2)
                self.requests.append(self._read_request(conn))
                for piece in script:
                    if isinstance(piece, (int, float)):
                        time.sleep(piece)
                    else:
                        conn.sendall(piece)

    @staticmethod
    def _read_request(conn):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return data
            data += chunk
        head, _, body = data.partition(b"\r\n\r\n")
        length = 0
        for line in head.split(b"\r\n")[1:]:
            name, _, value = line.partition(b":")
            if name.strip().lower() == b"content-length":
                length = int(value)
        while len(body) < length:
            body += conn.recv(4096)
        return head + b"\r\n\r\n" + body


@pytest.fixture
def scripted_server():
    """Фабрика тестовых серверов; все закрываются после теста."""
    servers = []

    def make(scripts):
        server = ScriptedServer(scripts)
        server.start()
        servers.append(server)
        return server

    yield make
    for server in servers:
        server.close()
