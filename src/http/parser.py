"""Разбор сырых HTTP-запросов и ответов."""
import re
from typing import Dict, Tuple

from src.http.exceptions import ParseError
from src.http.request import Request
from src.http.response import Response

MAX_HEADER_SIZE = 8 * 1024
_HEAD_END = b"\r\n\r\n"
_VERSIONS = ("HTTP/1.0", "HTTP/1.1")
_METHOD_RE = re.compile(r"^[A-Z]+$")
_TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_HEX_RE = re.compile(rb"^[0-9A-Fa-f]+$")
_NO_BODY_STATUSES = (204, 304)


class Parser:
    """Парсер HTTP (запрос/ответ, Content-Length, chunked)."""

    def parse_request(self, raw: bytes) -> Request:
        """Разобрать байты в Request. Бросает ParseError."""
        head, rest = self._split(raw)
        lines = head.split("\r\n")
        method, path, version = self._parse_request_line(lines[0])
        headers = self._parse_headers(lines[1:])
        if version == "HTTP/1.1" and "Host" not in headers:
            raise ParseError("Отсутствует обязательный заголовок Host")
        body = self._read_body(headers, rest, until_close=False)
        return Request(method=method, path=path, version=version, headers=headers, body=body)

    def parse_response(self, raw: bytes) -> Response:
        """Разобрать байты в Response (Content-Length и chunked)."""
        head, rest = self._split(raw)
        lines = head.split("\r\n")
        version, status, reason = self._parse_status_line(lines[0])
        headers = self._parse_headers(lines[1:])
        if status in _NO_BODY_STATUSES or 100 <= status < 200:
            body = b""
        else:
            body = self._read_body(headers, rest, until_close=True)
        return Response(status=status, reason=reason, version=version,
                        headers=headers, body=body)

    @staticmethod
    def _split(raw: bytes) -> Tuple[str, bytes]:
        """Отделить заголовки (текст) от тела (байты)."""
        idx = raw.find(_HEAD_END)
        if idx == -1:
            if len(raw) > MAX_HEADER_SIZE:
                raise ParseError("Заголовки превышают 8 КБ")
            raise ParseError("Неполное сообщение: нет пустой строки после заголовков")
        if idx > MAX_HEADER_SIZE:
            raise ParseError("Заголовки превышают 8 КБ")
        return raw[:idx].decode("iso-8859-1"), raw[idx + len(_HEAD_END):]

    @staticmethod
    def _parse_request_line(line: str) -> Tuple[str, str, str]:
        """Разобрать «METHOD /path HTTP/1.1»."""
        parts = line.split(" ")
        if len(parts) != 3:
            raise ParseError(f"Некорректная строка запроса: {line!r}")
        method, path, version = parts
        if not _METHOD_RE.match(method):
            raise ParseError(f"Некорректный метод: {method!r}")
        if not path.startswith("/"):
            raise ParseError(f"Путь должен начинаться с '/': {path!r}")
        if version not in _VERSIONS:
            raise ParseError(f"Неподдерживаемая версия: {version!r}")
        return method, path, version

    @staticmethod
    def _parse_status_line(line: str) -> Tuple[str, int, str]:
        """Разобрать «HTTP/1.1 200 OK»."""
        parts = line.split(" ", 2)
        if len(parts) < 2 or parts[0] not in _VERSIONS:
            raise ParseError(f"Некорректная строка статуса: {line!r}")
        if not (parts[1].isdigit() and len(parts[1]) == 3):
            raise ParseError(f"Некорректный код статуса: {parts[1]!r}")
        status = int(parts[1])
        if not 100 <= status <= 599:
            raise ParseError(f"Код статуса вне диапазона 100-599: {status}")
        reason = parts[2] if len(parts) == 3 else ""
        return parts[0], status, reason

    @staticmethod
    def _parse_headers(lines) -> Dict[str, str]:
        """Разобрать строки «Name: value»; имена приводятся к виду Title-Case."""
        headers: Dict[str, str] = {}
        for line in lines:
            name, sep, value = line.partition(":")
            if not sep or not _TOKEN_RE.match(name):
                raise ParseError(f"Некорректный заголовок: {line!r}")
            headers[name.title()] = value.strip()
        return headers

    def _read_body(self, headers: Dict[str, str], rest: bytes, until_close: bool) -> bytes:
        """Прочитать тело по Transfer-Encoding / Content-Length."""
        if "chunked" in headers.get("Transfer-Encoding", "").lower():
            return self._decode_chunked(rest)
        length = headers.get("Content-Length")
        if length is not None:
            if not length.isdigit():
                raise ParseError(f"Некорректный Content-Length: {length!r}")
            size = int(length)
            if len(rest) < size:
                raise ParseError("Тело короче, чем указано в Content-Length")
            return rest[:size]
        return rest if until_close else b""

    @staticmethod
    def _decode_chunked(data: bytes) -> bytes:
        """Собрать тело из чанков (Transfer-Encoding: chunked)."""
        pos = 0
        out = bytearray()
        while True:
            eol = data.find(b"\r\n", pos)
            if eol == -1:
                raise ParseError("Неполное chunked-тело: нет размера чанка")
            size_raw = data[pos:eol].split(b";", 1)[0].strip()
            if not _HEX_RE.match(size_raw):
                raise ParseError(f"Некорректный размер чанка: {size_raw!r}")
            size = int(size_raw, 16)
            pos = eol + 2
            if size == 0:
                return bytes(out)
            chunk = data[pos:pos + size]
            if len(chunk) < size or data[pos + size:pos + size + 2] != b"\r\n":
                raise ParseError("Неполный или повреждённый чанк")
            out += chunk
            pos += size + 2
