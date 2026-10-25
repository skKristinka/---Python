"""HTTP-клиент."""
from typing import Dict, Optional
from urllib.parse import urljoin

from src.http.exceptions import HttpError, ParseError
from src.http.parser import Parser
from src.http.reader import read_message
from src.http.request import Request
from src.http.response import Response
from src.http.serializer import Serializer
from src.http.url import Url
from src.net.tcp_client import TcpClient

USER_AGENT = "http_gui/1.0"
_REDIRECT_STATUSES = (301, 302, 303, 307, 308)
_BODY_METHODS = ("POST", "PUT", "PATCH")


def _drop_headers(headers: Dict[str, str], *names: str) -> Dict[str, str]:
    """Копия заголовков без перечисленных (без учёта регистра)."""
    skip = {name.lower() for name in names}
    return {k: v for k, v in headers.items() if k.lower() not in skip}


class HttpClient:
    """Отправляет GET/POST и возвращает Response.

    timeout — таймаут соединения и каждого чтения (сек);
    max_redirects — сколько редиректов 3xx следовать (0 — не следовать);
    raise_for_status — бросать HttpError для статусов 4xx/5xx.
    """

    def __init__(self, timeout: float = 5.0, max_redirects: int = 0,
                 raise_for_status: bool = False, tcp_client: Optional[TcpClient] = None):
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.raise_for_status = raise_for_status
        self._tcp = tcp_client or TcpClient(timeout)
        self._parser = Parser()
        self._serializer = Serializer()

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Response:
        """GET-запрос."""
        return self.request("GET", url, headers)

    def post(self, url: str, body: bytes, content_type: str = "text/plain",
             headers: Optional[Dict[str, str]] = None) -> Response:
        """POST-запрос с телом."""
        merged = _drop_headers(headers or {}, "Content-Type")
        merged["Content-Type"] = content_type
        return self.request("POST", url, merged, body)

    def request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None,
                body: bytes = b"") -> Response:
        """Выполнить запрос; при необходимости следовать редиректам."""
        method = method.upper()
        headers = dict(headers or {})
        redirects = 0
        while True:
            response = self._send_once(method, Url.parse(url), headers, body)
            location = response.headers.get("Location")
            if (response.status not in _REDIRECT_STATUSES or not location
                    or redirects >= self.max_redirects):
                break
            redirects += 1
            url = urljoin(url, location)
            if response.status == 303 or (response.status in (301, 302) and method == "POST"):
                method, body = "GET", b""
                headers = _drop_headers(headers, "Content-Type", "Content-Length")
        if self.raise_for_status and response.status >= 400:
            raise HttpError(response.status, response.reason)
        return response

    def _send_once(self, method: str, url: Url, headers: Dict[str, str],
                   body: bytes) -> Response:
        """Одно соединение: отправить запрос, прочитать и разобрать ответ."""
        request = Request(method=method, path=url.target,
                          headers=self._build_headers(method, url, headers, body), body=body)
        try:
            data = self._serializer.serialize_request(request)
        except ValueError as exc:
            raise ParseError(f"Некорректный запрос: {exc}") from exc
        try:
            with self._tcp.connect(url.host, url.port, url.scheme == "https") as sock:
                sock.send_all(data)
                raw = read_message(sock, is_response=True)
        except ConnectionRefusedError as exc:
            raise ConnectionError(f"Соединение отклонено: {url.host}:{url.port}") from exc
        except TimeoutError as exc:
            raise TimeoutError(f"Превышено время ожидания ({self.timeout} с)") from exc
        return self._parser.parse_response(raw)

    @staticmethod
    def _build_headers(method: str, url: Url, headers: Dict[str, str],
                       body: bytes) -> Dict[str, str]:
        """Заголовки по умолчанию + пользовательские (они главнее)."""
        default_port = 443 if url.scheme == "https" else 80
        host = url.host if url.port == default_port else f"{url.host}:{url.port}"
        result = {"Host": host, "User-Agent": USER_AGENT, "Accept": "*/*",
                  "Connection": "close"}
        for name, value in headers.items():
            result = _drop_headers(result, name)
            result[name] = value
        has_length = any(k.lower() == "content-length" for k in result)
        if method in _BODY_METHODS and not has_length:
            result["Content-Length"] = str(len(body))
        return result
