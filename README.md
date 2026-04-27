# Мониторинг ГИС Торги (MVP)

Система ежедневно загружает JSON с ГИС Торги, сохраняет данные в PostgreSQL, предоставляет API, отображает список и карту торгов, и отправляет Telegram-оповещения по новым/измененным лотам.

## Быстрый старт

1. Скопировать `.env.example` в `.env` и заполнить значения.
2. Запустить: `docker compose up --build`.
3. Backend API: `http://localhost:8000`.
4. Frontend: `http://localhost:5173`.

## Основные эндпоинты

- `GET /health` - проверка доступности.
- `GET /api/lots` - список лотов с фильтрами `region/status/category`.
- `GET /api/lots/{id}` - карточка лота.
- `GET /api/lots-map` - точки лотов для карты.
- `GET /api/ingest-runs` - история запусков загрузчика (наблюдаемость).

## Тесты

В каталоге `backend`:

```bash
pytest
```
