"""Чтение целого HTTP-сообщения из транспорта (сокета)."""
import re
from typing import Optional

from src.http.exceptions import ParseError
from src.http.parser import MAX_HEADER_SIZE, Parser, is_ascii_digits
from src.interfaces import Transport

MAX_BODY_SIZE = 10 * 1024 * 1024
_RECV_SIZE = 4096
_HEAD_END = b"\r\n\r\n"
_HEX_RE = re.compile(rb"^[0-9A-Fa-f]+$")


def read_message(transport: Transport, is_response: bool) -> bytes:
    """Прочитать сообщение целиком: заголовки, затем тело.

    Тело определяется по chunked / Content-Length; у ответа без них оно идёт
    до закрытия соединения, у запроса его нет.
    Бросает ConnectionError (ничего не получено) и ParseError (мусор, обрыв).
    """
    buf = bytearray()
    idx = _read_head(transport, buf)
    body_start = idx + len(_HEAD_END)
    lines = bytes(buf[:idx]).decode("iso-8859-1").split("\r\n")
    headers = Parser.parse_headers(lines[1:])
    if is_response and _has_no_body(lines[0]):
        return bytes(buf)
    if "chunked" in headers.get("Transfer-Encoding", "").lower():
        while _chunked_end(buf, body_start) is None:
            _fill(transport, buf, body_start)
        return bytes(buf)
    length = headers.get("Content-Length")
    if length is not None:
        if not is_ascii_digits(length):
            raise ParseError(f"Некорректный Content-Length: {length!r}")
        if int(length) > MAX_BODY_SIZE:
            raise ParseError("Тело превышает допустимый размер")
        while len(buf) - body_start < int(length):
            _fill(transport, buf, body_start)
        return bytes(buf)
    if is_response:
        _read_until_close(transport, buf, body_start)
    return bytes(buf)


def _read_head(transport: Transport, buf: bytearray) -> int:
    """Читать, пока не придёт пустая строка; вернуть её позицию."""
    while True:
        idx = buf.find(_HEAD_END)
        if idx != -1:
            if idx > MAX_HEADER_SIZE:
                raise ParseError("Заголовки превышают 8 КБ")
            return idx
        if len(buf) > MAX_HEADER_SIZE:
            raise ParseError("Заголовки превышают 8 КБ")
        chunk = transport.recv(_RECV_SIZE)
        if not chunk:
            if not buf:
                raise ConnectionError("Соединение закрыто, данные не получены")
            raise ParseError("Соединение закрыто до конца заголовков")
        buf += chunk


def _fill(transport: Transport, buf: bytearray, body_start: int) -> None:
    """Дочитать порцию тела; обрыв посреди тела — ParseError."""
    chunk = transport.recv(_RECV_SIZE)
    if not chunk:
        raise ParseError("Соединение закрыто до получения всего сообщения")
    buf += chunk
    if len(buf) - body_start > MAX_BODY_SIZE:
        raise ParseError("Тело превышает допустимый размер")


def _read_until_close(transport: Transport, buf: bytearray, body_start: int) -> None:
    """Читать тело до закрытия соединения."""
    while True:
        chunk = transport.recv(_RECV_SIZE)
        if not chunk:
            return
        buf += chunk
        if len(buf) - body_start > MAX_BODY_SIZE:
            raise ParseError("Тело превышает допустимый размер")


def _has_no_body(status_line: str) -> bool:
    """У ответов 1xx, 204 и 304 тела нет."""
    parts = status_line.split(" ", 2)
    status = int(parts[1]) if len(parts) > 1 and is_ascii_digits(parts[1]) else 0
    return status in (204, 304) or 100 <= status < 200


def _chunked_end(buf: bytearray, pos: int) -> Optional[int]:
    """Позиция конца chunked-тела или None, если оно пришло не целиком."""
    while True:
        eol = buf.find(b"\r\n", pos)
        if eol == -1:
            return None
        size_raw = bytes(buf[pos:eol]).split(b";", 1)[0].strip()
        if not _HEX_RE.match(size_raw):
            raise ParseError(f"Некорректный размер чанка: {size_raw!r}")
        size = int(size_raw, 16)
        pos = eol + 2
        if size == 0:
            return _trailers_end(buf, pos)
        if len(buf) < pos + size + 2:
            return None
        pos += size + 2


def _trailers_end(buf: bytearray, pos: int) -> Optional[int]:
    """Пропустить необязательные trailer-заголовки до пустой строки."""
    while True:
        eol = buf.find(b"\r\n", pos)
        if eol == -1:
            return None
        if eol == pos:
            return eol + 2
        pos = eol + 2
