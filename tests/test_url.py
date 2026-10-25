"""Unit-тесты разбора URL."""
import pytest

from src.http.exceptions import ParseError
from src.http.url import Url


def test_full_url():
    url = Url.parse("http://host:8080/path?q=1")
    assert (url.host, url.port, url.path, url.query) == ("host", 8080, "/path", "q=1")


def test_default_port_http():
    assert Url.parse("http://host/path").port == 80


def test_default_port_https():
    assert Url.parse("https://host/").port == 443


def test_default_path():
    assert Url.parse("http://host").path == "/"


def test_target_with_query():
    assert Url.parse("http://h/p?a=b").target == "/p?a=b"


@pytest.mark.parametrize("bad", ["garbage", "", "ftp://host/", "http://", "http://h:99999/"])
def test_invalid(bad):
    with pytest.raises(ParseError):
        Url.parse(bad)
