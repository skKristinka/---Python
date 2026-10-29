"""Выполнение HTTP-запроса клиента в фоновом потоке."""
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from src.client.http_client import HttpClient
from src.http.exceptions import HttpError, ParseError
from src.http.response import Response

logger = logging.getLogger("http_gui.client")


@dataclass(frozen=True)
class RequestSpec:
    """Параметры запроса, уже прошедшие проверку."""

    method: str
    url: str
    headers: Dict[str, str]
    body: bytes
    timeout: float
    max_redirects: int


@dataclass(frozen=True)
class RequestResult:
    """Результат: либо response, либо текст ошибки."""

    spec: RequestSpec
    response: Optional[Response]
    error: Optional[str]
    elapsed_ms: float


def describe_error(exc: Exception) -> str:
    """Текст ошибки для области ответа."""
    return f"{type(exc).__name__}: {exc}"


class RequestWorker:
    """Запускает запрос в потоке и кладёт RequestResult в очередь (для root.after)."""

    def __init__(self, client_factory: Callable[..., HttpClient] = HttpClient):
        self._factory = client_factory

    def submit(self, spec: RequestSpec, results: "queue.Queue[RequestResult]") -> threading.Thread:
        """Запустить запрос в фоне; результат придёт в results."""
        thread = threading.Thread(target=self._run, args=(spec, results),
                                  name="http-client", daemon=True)
        thread.start()
        return thread

    def _run(self, spec: RequestSpec, results: "queue.Queue[RequestResult]") -> None:
        started = time.perf_counter()
        response: Optional[Response] = None
        error: Optional[str] = None
        try:
            client = self._factory(timeout=spec.timeout, max_redirects=spec.max_redirects)
            response = client.request(spec.method, spec.url, spec.headers, spec.body)
        except (ConnectionError, TimeoutError, ParseError, HttpError, ValueError) as exc:
            error = describe_error(exc)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Непредвиденная ошибка запроса")
            error = f"Непредвиденная ошибка — {describe_error(exc)}"
        elapsed = (time.perf_counter() - started) * 1000
        if error:
            logger.warning("%s %s -> ошибка: %s", spec.method, spec.url, error)
        else:
            logger.info("%s %s -> %d (%.0f мс)", spec.method, spec.url, response.status, elapsed)
        results.put(RequestResult(spec, response, error, elapsed))
