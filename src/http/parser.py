"""Разбор сырых HTTP-запросов и ответов."""
from src.http.request import Request
from src.http.response import Response

MAX_HEADER_SIZE = 8 * 1024


class Parser:
    """Парсер HTTP (запрос/ответ, Content-Length, chunked)."""

    def parse_request(self, raw: bytes) -> Request:
        """Разобрать байты в Request. Бросает ParseError."""
        raise NotImplementedError

    def parse_response(self, raw: bytes) -> Response:
        """Разобрать байты в Response (Content-Length и chunked)."""
        raise NotImplementedError
