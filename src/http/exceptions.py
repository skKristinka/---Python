"""Исключения HTTP-слоя."""


class ParseError(Exception):
    """Ошибка разбора URL, запроса или ответа."""


class HttpError(Exception):
    """HTTP-ошибка с кодом статуса."""

    def __init__(self, status: int, message: str = ""):
        super().__init__(f"HTTP {status} {message}".strip())
        self.status = status
