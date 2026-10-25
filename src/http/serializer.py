"""Сборка HTTP-сообщений в байты."""
from email.utils import formatdate
from typing import Dict

from src.http.request import Request
from src.http.response import Response


def _has(headers: Dict[str, str], name: str) -> bool:
    """Есть ли заголовок (без учёта регистра)."""
    return name.lower() in (key.lower() for key in headers)


def _without(headers: Dict[str, str], *names: str) -> Dict[str, str]:
    """Копия заголовков без перечисленных (без учёта регистра)."""
    skip = {name.lower() for name in names}
    return {k: v for k, v in headers.items() if k.lower() not in skip}


class Serializer:
    """Сериализатор Request/Response в байты."""

    def serialize_request(self, request: Request) -> bytes:
        """Собрать запрос; заголовки заканчиваются пустой строкой."""
        headers = dict(request.headers)
        if request.body and not _has(headers, "Content-Length"):
            headers["Content-Length"] = str(len(request.body))
        start = f"{request.method} {request.path} {request.version}"
        return self._build(start, headers, request.body)

    def serialize_response(self, response: Response) -> bytes:
        """Собрать ответ; добавить Content-Length и Date."""
        headers = _without(response.headers, "Content-Length", "Transfer-Encoding")
        headers["Content-Length"] = str(len(response.body))
        if not _has(headers, "Date"):
            headers["Date"] = formatdate(usegmt=True)
        start = f"{response.version} {response.status} {response.reason}"
        return self._build(start, headers, response.body)

    @staticmethod
    def _build(start: str, headers: Dict[str, str], body: bytes) -> bytes:
        """Склеить стартовую строку, заголовки и тело."""
        lines = [start] + [f"{name}: {value}" for name, value in headers.items()]
        for line in lines:
            if "\r" in line or "\n" in line:
                raise ValueError("CR/LF внутри стартовой строки или заголовка запрещены")
        head = "\r\n".join(lines) + "\r\n\r\n"
        return head.encode("iso-8859-1") + body
