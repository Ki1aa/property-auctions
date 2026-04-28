# Мониторинг ГИС Торги (MVP)

Система загружает данные ГИС Торги, сохраняет данные в локальную БД SQLite (на этапе разработки), предоставляет API, отображает список извещений и поддерживает оповещения.

## Текущий режим разработки

Сейчас проект работает в dev-режиме на локальной SQLite:

- схема создается автоматически при старте backend через `Base.metadata.create_all(...)`;
- по умолчанию используется `DATABASE_URL=sqlite+pysqlite:///../data/app.db`;
- миграции Alembic сохраняются в проекте и будут использоваться при переходе к production.

## Быстрый старт (dev)

1. Скопируйте `.env.example` в `.env` и при необходимости измените значения.
2. Установите зависимости:

```bash
cd backend && python -m pip install -r requirements.txt
cd ../frontend && npm ci
```

3. Запустите backend:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. В отдельном терминале запустите frontend:

```bash
cd frontend
npm run dev
```

5. Проверьте сервисы:
   - Backend API: `http://localhost:8000`
   - Frontend: `http://localhost:5173`
   - Healthcheck: `GET http://localhost:8000/health`

## План по миграциям (к production)

Когда приложение стабилизируется и будет готово к production:

- переключить `DATABASE_URL` на PostgreSQL;
- применять изменения схемы через Alembic (`alembic revision`, `alembic upgrade head`);
- отключить автосоздание схемы через `create_all` в runtime.

Создать новую миграцию:

```bash
alembic revision --autogenerate -m "describe change"
```

Применить миграции:

```bash
alembic upgrade head
```

Проверить текущую ревизию:

```bash
alembic current
```

## Основные эндпоинты

- `GET /health` - проверка доступности.
- `GET /api/lots` - список лотов с фильтрами `region/status/category`.
- `GET /api/lots/{id}` - карточка лота.
- `GET /api/lots-map` - точки лотов для карты.
- `GET /api/ingest-runs` - история запусков загрузчика.
- `GET /api/opendata-notices` - список извещений с фильтрами `document_type/bidd_type_code/reg_num`.

## Тесты

В каталоге `backend`:

```bash
pytest
```
