"""Обработчики маршрутов: /, /echo, /time, /headers, /status/<code>."""
from src.http.request import Request
from src.http.response import Response


def index(req: Request) -> Response:
    """GET / — HTML-страница Hello."""
    raise NotImplementedError


def echo(req: Request) -> Response:
    """POST /echo — вернуть тело, сохранив Content-Type."""
    raise NotImplementedError


def server_time(req: Request) -> Response:
    """GET /time — текущее время в JSON."""
    raise NotImplementedError


def headers(req: Request) -> Response:
    """GET /headers — заголовки запроса в JSON."""
    raise NotImplementedError
