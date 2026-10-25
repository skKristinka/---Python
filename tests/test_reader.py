"""Unit-тесты read_message: чтение сообщения порциями из транспорта."""
import pytest

from src.http.exceptions import ParseError
from src.http.parser import Parser
from src.http.reader import read_message
from src.interfaces import Transport


class FakeTransport(Transport):
    """Транспорт с заранее заданными порциями; eof=False запрещает лишнее чтение."""

    def __init__(self, chunks, eof=True):
        self._chunks = list(chunks)
        self._eof = eof

    def send_all(self, data):
        """Не используется."""

    def recv(self, size):
        """Следующая порция; после неё — пустые байты (закрытие) или ошибка."""
        if self._chunks:
            return self._chunks.pop(0)
        if self._eof:
            return b""
        raise AssertionError("Лишнее чтение после конца сообщения")

    def close(self):
        """Не используется."""


def one_byte_chunks(raw):
    return [raw[i:i + 1] for i in range(len(raw))]


def test_content_length_split_into_single_bytes():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello"
    assert read_message(FakeTransport(one_byte_chunks(raw), eof=False), True) == raw


def test_chunked_stops_at_terminal_chunk():
    raw = (b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
           b"5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n")
    assert read_message(FakeTransport(one_byte_chunks(raw), eof=False), True) == raw


def test_chunked_roundtrip_with_parser():
    raw = (b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
           b"3\r\nabc\r\n0\r\n\r\n")
    message = read_message(FakeTransport([raw[:30], raw[30:]], eof=False), True)
    assert Parser().parse_response(message).body == b"abc"


def test_response_without_length_reads_until_close():
    chunks = [b"HTTP/1.1 200 OK\r\n\r\nabc", b"def"]
    assert read_message(FakeTransport(chunks), True).endswith(b"abcdef")


def test_request_without_body_does_not_wait():
    raw = b"GET / HTTP/1.1\r\nHost: h\r\n\r\n"
    assert read_message(FakeTransport([raw], eof=False), False) == raw


def test_response_204_has_no_body():
    raw = b"HTTP/1.1 204 No Content\r\n\r\n"
    assert read_message(FakeTransport([raw], eof=False), True) == raw


def test_head_too_large():
    with pytest.raises(ParseError):
        read_message(FakeTransport([b"A" * 9000]), True)


def test_closed_before_any_data():
    with pytest.raises(ConnectionError):
        read_message(FakeTransport([]), True)


def test_closed_in_the_middle_of_head():
    with pytest.raises(ParseError):
        read_message(FakeTransport([b"HTTP/1.1 200 OK\r\nContent-Le"]), True)


def test_body_cut_by_close_is_error():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nabc"
    with pytest.raises(ParseError):
        read_message(FakeTransport([raw]), True)


def test_chunked_cut_by_close_is_error():
    raw = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhel"
    with pytest.raises(ParseError):
        read_message(FakeTransport([raw]), True)


def test_bad_chunk_size():
    raw = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nzz\r\nxx\r\n"
    with pytest.raises(ParseError):
        read_message(FakeTransport([raw]), True)


def test_huge_content_length_is_rejected():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 99999999999\r\n\r\n"
    with pytest.raises(ParseError):
        read_message(FakeTransport([raw]), True)
