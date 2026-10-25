# HTTP-клиент и сервер с GUI на Python

Десктопное приложение: HTTP-клиент и HTTP-сервер, написанные «с нуля» на сокетах, с графическим интерфейсом (Tkinter). Сеть работает в фоновых потоках, GUI не замерзает.

## Возможности
- **Клиент:** URL, метод GET/POST, заголовки, тело, ответ (статус, заголовки, тело)
- **Сервер:** запуск/остановка по порту, лог запросов (время, метод, путь, статус, мс)
- Маршруты сервера: `/`, `/echo`, `/time`, `/headers`, `/status/<code>`, остальное — 404

## Установка и запуск
```bash
git clone <URL-репозитория>
cd http_gui
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

## Проверка сервера
```bash
curl -v http://localhost:8080/
curl -v -X POST -d "hello" http://localhost:8080/echo
curl -v http://localhost:8080/status/418
```

## Тесты и линтеры
```bash
pytest tests/ -v
flake8 src/ tests/
```

## Структура
```
src/
  http/     Url, Request, Response, Parser, Serializer
  net/      Socket, TcpClient, TcpServer
  client/   HttpClient
  server/   HttpServer, Router, handlers
  gui/      App, ClientTab, ServerTab, widgets
  main.py   точка входа
tests/      unit и интеграционные тесты
docs/       UML-диаграмма (PlantUML)
```
Подробнее — в [documentation.md](documentation.md), правила работы с git — в [CONTRIBUTING.md](CONTRIBUTING.md).
