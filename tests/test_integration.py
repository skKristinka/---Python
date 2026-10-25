"""Интеграционные тесты: сервер в потоке + HttpClient."""
import pytest


@pytest.mark.skip(reason="Сервер и клиент ещё не реализованы")
def test_get_root_returns_hello():
    """GET / -> 200, тело содержит Hello."""
