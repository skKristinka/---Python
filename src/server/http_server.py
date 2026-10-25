"""HTTP-сервер, работающий в отдельном потоке."""
import queue
import threading
from typing import Optional

from src.server.router import Router


class HttpServer:
    """Принимает соединения в потоке, пишет лог в очередь для GUI."""

    def __init__(self, router: Router, port: int = 8080):
        self.router = router
        self.port = port
        self.log_queue: "queue.Queue[tuple]" = queue.Queue()
        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Запустить сервер в фоновом потоке."""
        raise NotImplementedError

    def stop(self) -> None:
        """Остановить: выставить флаг и закрыть сокет."""
        raise NotImplementedError
