"""Маршрутизация запросов."""
from typing import Callable, Dict, List, Tuple

from src.http.request import Request
from src.http.response import Response
from src.interfaces import RequestHandler

Handler = Callable[[Request], Response]


class Router(RequestHandler):
    """Сопоставляет (метод, путь) с обработчиком; query-строка при поиске отбрасывается."""

    def __init__(self) -> None:
        self._routes: Dict[Tuple[str, str], Handler] = {}
        self._prefixes: List[Tuple[str, str, Handler]] = []

    def route(self, method: str, path: str, handler: Handler) -> None:
        """Зарегистрировать маршрут с точным путём."""
        self._routes[(method.upper(), path)] = handler

    def route_prefix(self, method: str, prefix: str, handler: Handler) -> None:
        """Зарегистрировать маршрут по префиксу пути (например, /status/)."""
        self._prefixes.append((method.upper(), prefix, handler))

    def handle(self, request: Request) -> Response:
        """Реализация интерфейса RequestHandler."""
        return self.dispatch(request)

    def dispatch(self, req: Request) -> Response:
        """Найти обработчик и вызвать его; иначе 404."""
        method = req.method.upper()
        path = req.path.split("?", 1)[0]
        handler = self._routes.get((method, path))
        if handler is None:
            for prefix_method, prefix, prefix_handler in self._prefixes:
                if prefix_method == method and path.startswith(prefix):
                    handler = prefix_handler
                    break
        if handler is None:
            return Response(status=404, headers={"Content-Type": "text/plain; charset=utf-8"},
                            body=b"404 Not Found")
        return handler(req)
