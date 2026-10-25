"""HTTP-клиент."""
from typing import Dict, Optional

from src.http.response import Response


class HttpClient:
    """Отправляет GET/POST и возвращает Response."""

    def __init__(self, timeout: float = 5.0, max_redirects: int = 0):
        self.timeout = timeout
        self.max_redirects = max_redirects

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Response:
        """GET-запрос."""
        raise NotImplementedError

    def post(self, url: str, body: bytes, content_type: str = "text/plain",
             headers: Optional[Dict[str, str]] = None) -> Response:
        """POST-запрос."""
        raise NotImplementedError
