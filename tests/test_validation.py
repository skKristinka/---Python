"""Unit-тесты проверки пользовательского ввода."""
import pytest

from src.gui.validation import (ValidationError, normalize_url, validate_headers,
                                validate_port, validate_redirects, validate_timeout)


def test_url_is_kept():
    assert normalize_url("  http://localhost:8080/x?a=1 ") == "http://localhost:8080/x?a=1"


def test_url_without_scheme_gets_http():
    assert normalize_url("example.com/path") == "http://example.com/path"


@pytest.mark.parametrize("raw", ["", "   ", "ftp://host/", "http://", "http://h:99999/"])
def test_url_invalid(raw):
    with pytest.raises(ValidationError):
        normalize_url(raw)


@pytest.mark.parametrize("raw, expected", [("1", 1), ("8080", 8080), (" 65535 ", 65535)])
def test_port_valid(raw, expected):
    assert validate_port(raw) == expected


@pytest.mark.parametrize("raw", ["0", "65536", "-1", "abc", "", "80.5", "８０"])
def test_port_invalid(raw):
    with pytest.raises(ValidationError):
        validate_port(raw)


@pytest.mark.parametrize("raw, expected", [("5", 5.0), ("0,5", 0.5), (" 2.5 ", 2.5)])
def test_timeout_valid(raw, expected):
    assert validate_timeout(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-1", "301", "abc", "", "nan", "inf"])
def test_timeout_invalid(raw):
    with pytest.raises(ValidationError):
        validate_timeout(raw)


@pytest.mark.parametrize("raw, ok", [("0", True), ("10", True), ("11", False), ("-1", False),
                                     ("x", False)])
def test_redirects(raw, ok):
    if ok:
        assert validate_redirects(raw) == int(raw)
    else:
        with pytest.raises(ValidationError):
            validate_redirects(raw)


def test_headers_ok_and_empty_rows_skipped():
    rows = [("Accept", " text/html "), ("", ""), ("X-Test", "1")]
    assert validate_headers(rows) == {"Accept": "text/html", "X-Test": "1"}


@pytest.mark.parametrize("rows", [
    [("Bad Name", "v")],
    [("", "value-without-name")],
    [("X-A", "line1\nline2")],
    [("Имя", "v")],
])
def test_headers_invalid(rows):
    with pytest.raises(ValidationError):
        validate_headers(rows)


def test_header_error_mentions_row_number():
    with pytest.raises(ValidationError) as info:
        validate_headers([("A", "1"), ("B C", "2")])
    assert "Строка 2" in str(info.value)
