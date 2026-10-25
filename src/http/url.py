"""Разбор URL вида http://host:port/path?query."""
import re
from dataclasses import dataclass

from src.http.exceptions import ParseError

_URL_RE = re.compile(
    r"^(?P<scheme>https?)://(?P<host>[^/:?#]+)(?::(?P<port>\d+))?"
    r"(?P<path>/[^?#]*)?(?:\?(?P<query>[^#]*))?(?:#.*)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Url:
    """Разобранный URL."""

    scheme: str
    host: str
    port: int
    path: str = "/"
    query: str = ""

    @classmethod
    def parse(cls, raw: str) -> "Url":
        """Разобрать строку в Url. Бросает ParseError при неверном формате."""
        match = _URL_RE.match(raw.strip())
        if not match:
            raise ParseError(f"Некорректный URL: {raw!r}")
        scheme = match.group("scheme").lower()
        port_s = match.group("port")
        port = int(port_s) if port_s else (443 if scheme == "https" else 80)
        if not 1 <= port <= 65535:
            raise ParseError(f"Порт вне диапазона 1-65535: {port}")
        return cls(scheme, match.group("host"), port,
                   match.group("path") or "/", match.group("query") or "")

    @property
    def target(self) -> str:
        """Путь вместе с query для строки запроса."""
        return f"{self.path}?{self.query}" if self.query else self.path
