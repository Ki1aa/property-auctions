# Мониторинг ГИС Торги (MVP)

> Контекст для AI-агентов: [AGENTS.md](AGENTS.md) - постоянный контекст и соглашения, [WORKLOG.md](WORKLOG.md) - журнал работ.

Система загружает данные ГИС Торги, сохраняет данные в локальную БД SQLite (на этапе разработки), предоставляет API, отображает список извещений и поддерживает оповещения.

## Текущий режим разработки

Сейчас проект работает в dev-режиме на локальной SQLite:

- схема создается автоматически при старте backend через `Base.metadata.create_all(...)`;
- по умолчанию используется `DATABASE_URL=sqlite+pysqlite:///../data/app.db`;
- миграции Alembic сохраняются в проекте и будут использоваться при переходе к production;
- для существующей SQLite после изменения моделей запускайте `cd backend && python scripts/dev_sync_schema.py`: скрипт добавляет новые колонки и недостающие индексы; внешние ключи SQLite не умеет добавлять без rebuild таблицы, поэтому скрипт выводит предупреждение.

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

`INGEST_SOURCE_URL` поддерживает два формата:
- URL карточки открытых данных (например, `.../new/public/opendata/...`);
- прямой URL на `data-*.json`.

Если указан URL карточки, backend автоматически извлекает ссылки на `data-*.json`, выбирает самую актуальную версию и загружает ее.

## Offline demo-данные

Если live-доступ к `torgi.gov.ru` недоступен из-за VPN/маршрутизации, MVP можно наполнить сохранённой выборкой из `data/raw`:

```bash
cd backend
python scripts/load_demo_tyumen_data.py --reset
```

Скрипт не ходит в сеть: он загружает `data/raw/torgi_opendata_tyumen_union.json` и сохранённые detail JSON из `data/raw/torgi_sample_lots_full_20260507`. При `--reset` dev-таблицы очищаются и получается воспроизводимый набор для демонстрации Dashboard/Lots.

## Discovery chain ingestion

Ingestion использует 3 уровня discovery источника:

1. **Primary:** `TORGI_OPENDATA_REGISTRY_URL` (машиночитаемый реестр `list.json`).
2. **Fallback:** `TORGI_OPENDATA_CARD_URL` (HTML-карточка набора).
3. **Fallback-2:** прямые `INGEST_SOURCE_URL` + `INGEST_STRUCTURE_URL`.

Поддерживаются режимы:

- `INGEST_MODE=operational` - ежедневная загрузка с догрузкой пропущенных дней по watermark.
- `INGEST_MODE=backfill` - загрузка диапазона по `BACKFILL_FROM` / `BACKFILL_TO`.

Каждый `data-*.json` обрабатывается только с соответствующей `structure-*.json`. Если версия структуры не поддерживается, файл сохраняется в raw и маркируется как `schema_migration_required` в `ingest_manifest`.

## Backfill запуск

Пример запуска backfill вручную:

```bash
cd backend
python scripts/run_backfill_ingest.py --from-date 2026-04-01 --to-date 2026-04-10
```

Логи загрузок и идемпотентность фиксируются в таблице `ingest_manifest` (`source_url + sha256` не обрабатывается повторно).

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
- `GET /api/lots` - страница лотов: JSON `{ items, total, limit, offset }` с фильтрами `region/status/municipality/category/is_izhs/has_cadastral/has_price_per_sotka/has_positive_discount/...`, пагинацией `limit`/`offset`, сортировкой `sort` (`updated_at_desc`, `price_per_sotka_asc`, `price_per_sotka_desc`, `discount_to_baseline_desc`). В элементах: `start_price_per_sotka`, `start_price_per_sqm` (из извещения), `baseline_price_per_sotka`, `discount_to_baseline`, `valuation_confidence` (внутренний baseline по загруженным торгам, не рыночная оценка).
- `GET /api/export/lots.csv` - выгрузка CSV с теми же фильтрами, `sort` и baseline-колонками, параметр `max_rows` (по умолчанию 10000, макс. 50000).
- `GET /api/lots/quality?region=72` - метрики качества данных для Dashboard: ИЖС-кандидаты, доля с муниципалитетом/кадастром/площадью/ценой/baseline.
- `GET /api/lots/{id}` - карточка лота.
- `GET /api/lots-map` - точки лотов для карты.
- `GET /api/ingest-runs` - история запусков загрузчика с диагностикой файлов: `processed_files`, `failed_files`, `last_error_source_url`, `error_kind`.
- `GET /api/ingest-status` - текущее состояние ingest: идёт ли загрузка, включён ли планировщик, следующий запуск, интервал и текущая область ingest (`target_region_codes`; пусто означает все регионы).
- `POST /api/ingest-runs/start` - ручной запуск operational ingest в фоне; если загрузка уже идёт, возвращает `started=false`.
- `GET /api/opendata-notices` - страница извещений: JSON `{ items, total, limit, offset }` с фильтрами `document_type/bidd_type_code/reg_num`, пагинацией `limit`/`offset` и серверной сортировкой `sort` (`publish_date_desc`, `publish_date_asc`, `reg_num_asc`, `reg_num_desc`, `document_type_asc`, `document_type_desc`, `bidd_type_code_asc`, `bidd_type_code_desc`).

## Тесты

В каталоге `backend`:

```bash
pytest
```

В каталоге `frontend`:

```bash
npm run test
npm run build
```
