"""Маршрутизация запросов."""
from typing import Callable, Dict, Tuple

from src.http.request import Request
from src.http.response import Response

Handler = Callable[[Request], Response]


class Router:
    """Сопоставляет (метод, путь) с обработчиком."""

    def __init__(self) -> None:
        self._routes: Dict[Tuple[str, str], Handler] = {}

    def route(self, method: str, path: str, handler: Handler) -> None:
        """Зарегистрировать маршрут."""
        self._routes[(method.upper(), path)] = handler

    def dispatch(self, req: Request) -> Response:
        """Найти обработчик; /status/<code>; иначе 404."""
        handler = self._routes.get((req.method.upper(), req.path))
        if handler:
            return handler(req)
        if req.method.upper() == "GET" and req.path.startswith("/status/"):
            try:
                return Response(status=int(req.path.rsplit("/", 1)[-1]))
            except ValueError:
                pass
        return Response(status=404, body=b"404 Not Found")
