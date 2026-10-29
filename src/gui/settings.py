"""Настройки приложения."""
from dataclasses import dataclass


@dataclass
class Settings:
    """Настройки, общие для вкладок (передаются явно, без глобального состояния)."""

    timeout: float = 5.0
    max_redirects: int = 0
    theme: str = "light"
    save_history: bool = False
