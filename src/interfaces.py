"""Абстрактные интерфейсы (ABC) проекта."""
from abc import ABC, abstractmethod

from src.http.request import Request
from src.http.response import Response


class RequestHandler(ABC):
    """Интерфейс обработчика входящего HTTP-запроса на сервере."""

    @abstractmethod
    def handle(self, request: Request) -> Response:
        """Обработать запрос и вернуть ответ."""


class Transport(ABC):
    """Интерфейс транспорта: отправка и приём байтов."""

    @abstractmethod
    def send_all(self, data: bytes) -> None:
        """Отправить все байты."""

    @abstractmethod
    def recv(self, size: int) -> bytes:
        """Принять до size байт."""

    @abstractmethod
    def close(self) -> None:
        """Закрыть соединение."""
