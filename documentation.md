# Документация проекта

## 1. Назначение
Приложение для изучения HTTP «под капотом»: клиент и сервер на сокетах, GUI на Tkinter, многопоточность.

## 2. Архитектура
Слои: `http` (модели и разбор) → `net` (сокеты) → `client`/`server` (логика) → `gui` (интерфейс).
Диаграмма классов: [docs/class_diagram.puml](docs/class_diagram.puml).

## 3. Модули
| Модуль | Классы | Назначение |
|---|---|---|
| `src/interfaces.py` | `RequestHandler`, `Transport` | Абстрактные интерфейсы (ABC) |
| `src/http` | `Url`, `Request`, `Response`, `Parser`, `Serializer` | Модели, разбор и сборка HTTP |
| `src/net` | `Socket`, `TcpClient`, `TcpServer` | Работа с сокетами, контекстный менеджер |
| `src/client` | `HttpClient` | GET/POST, таймаут, редиректы |
| `src/server` | `HttpServer`, `Router`, handlers | Сервер в потоке, маршруты |
| `src/gui` | `App`, `ClientTab`, `ServerTab`, `HeaderTable`, `LogTable` | Интерфейс |

## 4. Многопоточность
- Запрос клиента и сервер выполняются в фоновых потоках.
- Результат передаётся в GUI через `queue.Queue` и `root.after`.
- Остановка сервера: флаг `threading.Event` + закрытие сокета.

## 5. Исключения
`ParseError`, `HttpError(status)`, встроенные `ConnectionError`, `TimeoutError`.

## 6. Тестирование
Unit: `tests/test_url.py`, `tests/test_serializer.py`. Интеграционные: `tests/test_integration.py`. GUI — вручную по сценариям G1–G6.

## 7. Ветки и CI
`main` ← `develop` ← `feature/*`. CI (GitHub Actions) запускает flake8 и pytest на каждый push и pull request.
