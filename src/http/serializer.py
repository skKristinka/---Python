"""Сборка HTTP-сообщений в байты."""
from src.http.request import Request
from src.http.response import Response


class Serializer:
    """Сериализатор Request/Response в байты."""

    def serialize_request(self, request: Request) -> bytes:
        """Собрать запрос; заголовки заканчиваются пустой строкой."""
        raise NotImplementedError

    def serialize_response(self, response: Response) -> bytes:
        """Собрать ответ; добавить Content-Length и Date."""
        raise NotImplementedError
