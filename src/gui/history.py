"""Сохранение истории запросов в JSON."""
import json
import os
from pathlib import Path
from typing import Any, Dict, List

MAX_RECORDS = 1000


class HistoryStore:
    """Хранит историю запросов в JSON-файле."""

    def __init__(self, path):
        self.path = Path(path)

    def load(self) -> List[Dict[str, Any]]:
        """Прочитать историю; битый или отсутствующий файл — пустая история."""
        try:
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError):
            return []
        return data if isinstance(data, list) else []

    def add(self, entry: Dict[str, Any]) -> None:
        """Добавить запись (хранятся последние MAX_RECORDS)."""
        records = (self.load() + [entry])[-MAX_RECORDS:]
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(records, file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)
