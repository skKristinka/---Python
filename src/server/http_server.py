"""HTTP-сервер: приём соединений в отдельном потоке, отдельный поток на каждое соединение."""
import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Set

from src.http.exceptions import ParseError
from src.http.parser import Parser
from src.http.reader import read_message
from src.http.request import Request
from src.http.response import Response
from src.http.serializer import Serializer
from src.interfaces import RequestHandler
from src.net.socket_wrapper import Socket
from src.net.tcp_server import TcpServer

logger = logging.getLogger("http_gui.server")
_TEXT = "text/plain; charset=utf-8"


@dataclass(frozen=True)
class LogEntry:
    """Запись лога запроса для таблицы в GUI."""

    time: str
    method: str
    path: str
    status: int
    ms: float


class HttpServer:
    """HTTP-сервер.

    Принимающий поток слушает порт; каждое соединение обслуживается своим потоком
    (поддерживается keep-alive). Записи лога кладутся в log_queue — GUI забирает их
    из главного потока. Остановка: флаг + закрытие сокетов, без kill.
    """

    def __init__(self, handler: RequestHandler, port: int = 8080,
                 host: str = "127.0.0.1", idle_timeout: float = 5.0):
        self.handler = handler
        self.port = port
        self.host = host
        self.idle_timeout = idle_timeout
        self.log_queue: "queue.Queue[LogEntry]" = queue.Queue()
        self._parser = Parser()
        self._serializer = Serializer()
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._tcp: Optional[TcpServer] = None
        self._thread: Optional[threading.Thread] = None
        self._connections: Set[Socket] = set()
        self._workers: List[threading.Thread] = []

    @property
    def is_running(self) -> bool:
        """Работает ли принимающий поток."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def active_connections(self) -> int:
        """Сколько соединений обслуживается прямо сейчас."""
        with self._lock:
            return len(self._connections)

    def start(self) -> None:
        """Занять порт и запустить сервер в фоновом потоке.

        Бросает RuntimeError, если сервер уже запущен, и ConnectionError, если порт занят.
        """
        if self.is_running:
            raise RuntimeError("Сервер уже запущен")
        tcp = TcpServer(self.host, self.port)
        tcp.start()
        self.port = tcp.port
        self._tcp = tcp
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._accept_loop, args=(tcp,),
                                        name="http-accept", daemon=True)
        self._thread.start()
        logger.info("Сервер запущен на %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Остановить: выставить флаг, закрыть сокеты, дождаться потоков."""
        self._stop_flag.set()
        if self._tcp is not None:
            self._tcp.stop()
            self._tcp = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        with self._lock:
            connections = list(self._connections)
            workers = list(self._workers)
        for conn in connections:
            conn.shutdown()
        for worker in workers:
            worker.join(timeout=2)
        logger.info("Сервер остановлен")

    def _accept_loop(self, tcp: TcpServer) -> None:
        """Принимать соединения, пока не выставлен флаг остановки."""
        while not self._stop_flag.is_set():
            try:
                accepted = tcp.accept()
            except OSError:
                break
            if accepted is None:
                continue
            raw, _ = accepted
            raw.settimeout(self.idle_timeout)
            self._spawn_worker(Socket(raw))

    def _spawn_worker(self, sock: Socket) -> None:
        """Запустить поток обслуживания соединения."""
        worker = threading.Thread(target=self._serve_connection, args=(sock,),
                                  name="http-conn", daemon=True)
        with self._lock:
            self._connections.add(sock)
            self._workers.append(worker)
        worker.start()

    def _serve_connection(self, sock: Socket) -> None:
        """Обслужить соединение и убрать его из списков."""
        try:
            with sock:
                self._serve_requests(sock)
        except OSError as exc:
            logger.debug("Соединение прервано: %s", exc)
        finally:
            with self._lock:
                self._connections.discard(sock)
                if threading.current_thread() in self._workers:
                    self._workers.remove(threading.current_thread())

    def _serve_requests(self, sock: Socket) -> None:
        """Цикл запросов одного соединения (keep-alive)."""
        while not self._stop_flag.is_set():
            try:
                raw = read_message(sock, is_response=False)
                started = time.perf_counter()
                request = self._parser.parse_request(raw)
            except (ConnectionError, TimeoutError):
                return
            except ParseError as exc:
                self._reject(sock, exc)
                return
            response = self._dispatch(request)
            keep_alive = self._wants_keep_alive(request) and not self._stop_flag.is_set()
            response.headers["Connection"] = "keep-alive" if keep_alive else "close"
            sock.send_all(self._serializer.serialize_response(response))
            self._log(request.method, request.path, response.status, started)
            if not keep_alive:
                return

    def _dispatch(self, request: Request) -> Response:
        """Вызвать обработчик; его падение не должно ронять сервер."""
        try:
            return self.handler.handle(request)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Ошибка обработчика %s %s", request.method, request.path)
            return Response(status=500, headers={"Content-Type": _TEXT},
                            body=b"500 Internal Server Error")

    def _reject(self, sock: Socket, exc: ParseError) -> None:
        """Ответить 400 на некорректный запрос и закрыть соединение."""
        started = time.perf_counter()
        logger.warning("Некорректный запрос: %s", exc)
        response = Response(status=400, headers={"Content-Type": _TEXT, "Connection": "close"},
                            body=b"400 Bad Request")
        sock.send_all(self._serializer.serialize_response(response))
        self._log("-", "-", 400, started)

    @staticmethod
    def _wants_keep_alive(request: Request) -> bool:
        """HTTP/1.1 — keep-alive по умолчанию, HTTP/1.0 — только по запросу клиента."""
        connection = request.headers.get("Connection", "").lower()
        if request.version == "HTTP/1.1":
            return connection != "close"
        return connection == "keep-alive"

    def _log(self, method: str, path: str, status: int, started: float) -> None:
        """Записать строку лога в очередь для GUI и в logging."""
        ms = (time.perf_counter() - started) * 1000
        entry = LogEntry(datetime.now().strftime("%H:%M:%S"), method, path, status, round(ms, 1))
        self.log_queue.put(entry)
        logger.info("%s %s -> %d (%.1f мс)", method, path, status, ms)
