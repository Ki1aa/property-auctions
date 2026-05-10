# Мониторинг ГИС Торги (MVP)

> Контекст для AI-агентов: [AGENTS.md](AGENTS.md) - постоянный контекст и соглашения, [WORKLOG.md](WORKLOG.md) - журнал работ.

Система загружает данные ГИС Торги, сохраняет данные в локальную БД SQLite (на этапе разработки), предоставляет API, отображает список лотов и поддерживает Telegram-оповещения. Продуктовый контракт MVP описан в [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md).

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

Ingestion использует устойчивую цепочку discovery источника:

1. **Primary:** `TORGI_OPENDATA_REGISTRY_URL` (машиночитаемый реестр `list.json`) и `meta.json` набора.
2. **Fallback:** `TORGI_OPENDATA_CARD_URL` (HTML-карточка набора).
3. **Override:** `INGEST_SOURCE_URL` как URL карточки OpenData или прямой `data-*.json`; `INGEST_STRUCTURE_URL` нужен только для прямого JSON без выводимой `structure-*`.

Поддерживаются режимы:

- `INGEST_MODE=operational` - ежедневная загрузка с догрузкой пропущенных дней по watermark.
- `INGEST_MODE=backfill` - загрузка диапазона по `BACKFILL_FROM` / `BACKFILL_TO`.

Каждый `data-*.json` обрабатывается только с соответствующей `structure-*.json`. Если версия структуры не поддерживается, файл сохраняется в raw и маркируется как `schema_migration_required` в `ingest_manifest`.

В MVP по умолчанию включён продуктовый фильтр `INGEST_ONLY_LAND_LOTS=true`: в `lots` сохраняются только земельные участки / права на земельные участки. Автомобили, древесина, помещения и другие имущественные лоты отсекаются после detail-fetch по виду торгов `ZK`, признакам земли в title/category/ВРИ/адресе и ИЖС-маркерам. Для исследовательской загрузки всего реестра флаг можно временно выключить.

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
- `GET /api/lots` - страница лотов: JSON `{ items, total, limit, offset }` с фильтрами `region/status/municipality/category/is_izhs/has_cadastral/has_price_per_sotka/has_positive_discount/...`, пагинацией `limit`/`offset`, сортировкой `sort` (`updated_at_desc`, `price_per_sotka_asc`, `price_per_sotka_desc`, `discount_to_baseline_desc`). В элементах: `start_price_per_sotka`, `start_price_per_sqm` (из извещения), `baseline_price_per_sotka`, `discount_to_baseline`, `valuation_confidence` (внутренний baseline по загруженным торгам, не рыночная оценка), `nspd_map_url` при наличии кадастра. Если НСПД-обогащение нашло `card_id/card_type` и центроид, URL ведёт прямо в карточку участка через `selectedCard`; иначе открывает карту с кадастром в query и, при наличии центроида, с нужным zoom/координатами. `domclick_map_url` появляется при наличии координат/НСПД-центроида и ведёт на карту Домклик вокруг участка (`offer_type=lot`, bbox `sw/ne`, радиус `MARKETPLACE_MAP_RADIUS_KM`).
- `GET /api/export/lots.csv` - выгрузка CSV с теми же фильтрами, `sort` и baseline-колонками, параметр `max_rows` (по умолчанию 10000, макс. 50000).
- `GET /api/lots/quality?region=72` - метрики качества данных для Dashboard: ИЖС-кандидаты, доля с муниципалитетом/кадастром/площадью/ценой/baseline.
- `GET /api/lots/{id}` - карточка лота.
- `GET /api/lots-map` - точки лотов для карты.
- `GET /api/ingest-runs` - история запусков загрузчика с диагностикой файлов: `processed_files`, `failed_files`, `last_error_source_url`, `error_kind`.
- `GET /api/ingest-status` - текущее состояние ingest: идёт ли загрузка, включён ли планировщик, следующий запуск, интервал и текущая область ingest (`target_region_codes`; пусто означает все регионы).
- `POST /api/ingest-runs/start` - ручной запуск operational ingest в фоне; если загрузка уже идёт, возвращает `started=false`.
- `GET /api/opendata-notices` - страница извещений: JSON `{ items, total, limit, offset }` с фильтрами `document_type/bidd_type_code/reg_num`, пагинацией `limit`/`offset` и серверной сортировкой `sort` (`publish_date_desc`, `publish_date_asc`, `reg_num_asc`, `reg_num_desc`, `document_type_asc`, `document_type_desc`, `bidd_type_code_asc`, `bidd_type_code_desc`).

## Telegram-алерты

После ingest при событиях `new_lot` / `changed_lot` backend может отправить компактную карточку в Telegram: вердикт, причина попадания, `regNum + lotNumber`, кадастр, земля, цена за сотку, baseline и ссылки на монитор, публичную карточку ГИС Торги `/new/public/notices/view/{regNum}`, НСПД-карту/deep link, карту Домклик вокруг участка при наличии координат и сырой JSON извещения. Текстовый поиск на Домклик/Авито/Циан опционален через `INCLUDE_MARKETPLACE_SEARCH_URLS=true`; в MVP он выключен по умолчанию, потому что площадки могут открывать капчу или пустую выдачу.

1. Создайте бота в [@BotFather](https://t.me/BotFather), получите `TELEGRAM_BOT_TOKEN`.
2. Узнайте `TELEGRAM_CHAT_ID`: для личного чата напишите боту `/start`, затем используйте [@userinfobot](https://t.me/userinfobot) или `getUpdates` у Bot API; для канала добавьте бота администратором, id обычно вида `-100...`.
3. Пропишите переменные в `.env` (см. [.env.example](.env.example)). Для ссылки «Монитор» в алерте задайте `APP_PUBLIC_BASE_URL` (публичный URL SPA без слэша в конце).
4. Проверка без ingest: из каталога `backend` выполните `python scripts/send_telegram_test.py` (сообщение по умолчанию можно заменить флагом `--text`).
5. Типичные ошибки Bot API: **403 Forbidden** — бот не может писать в чат (не нажали `/start` в личке, бот не админ в канале, неверный `chat_id`); **401** — неверный токен. Чтобы сократить шум, включите `TELEGRAM_ALERT_ONLY_IZHS=true` (только лоты-кандидаты ИЖС).

Дополнительно: `TELEGRAM_DISABLE_WEB_PAGE_PREVIEW`, лимит длины, таймаут, повтор при 429 и `TELEGRAM_PROXY_URL` для HTTP(S)-прокси к Bot API — в `.env.example`.

**Чеклист production (MVP push в Telegram):**

- `RUN_INGEST_ON_STARTUP=false` — чтобы при каждом рестарте не стартовал тяжёлый ingest; полагайтесь на APScheduler и/или ручной `POST /api/ingest-runs/start`.
- `TELEGRAM_ALERTS_ENABLED=true`, заданы `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`; при обслуживании БД без шума можно временно выставить `false`.
- Если `send_telegram_test.py` падает на `ConnectTimeout` к `api.telegram.org`, задайте `TELEGRAM_PROXY_URL` или передайте разово `--proxy-url http://127.0.0.1:7890`, затем повторите smoke.
- `APP_PUBLIC_BASE_URL` — публичный URL SPA для ссылки «Монитор» в алерте.
- Хост с маршрутом к `torgi.gov.ru` (часто нужен IP в РФ); при необходимости `TARGET_REGION_CODES` для сужения объёма.
- Опционально `NSPD_ENABLED=true` на той же машине, если доступен `nspd.gov.ru`; политики слияния `NSPD_MERGE_*` — в `.env.example`. Для локального split tunneling с self-signed TLS цепочкой можно временно ставить `NSPD_VERIFY_TLS=false`, после чего `domclick_map_url` начнёт появляться у лотов с найденным центроидом.
- Умный поток: `TELEGRAM_ALERT_SKIP_LOW_SIGNAL`, `TELEGRAM_ALERT_MIN_DISCOUNT_TO_BASELINE`, `TELEGRAM_ALERT_REQUIRE_BASELINE_FOR_DISCOUNT`, `TELEGRAM_ALERT_REQUIRE_CADASTRAL`, `TELEGRAM_ALERT_ONLY_IZHS` — комбинируйте по сценарию. `TELEGRAM_ALERT_SKIP_LOW_SIGNAL=true` убирает сообщения без практического сигнала: не ИЖС, нет кадастра, нет цены за сотку/baseline. Для самого тихого MVP-потока обычно включают ИЖС + кадастр + минимальный дисконт, а baseline-required включают только когда база уже достаточно наполнена.

**Качество кадастра / парсера:** периодически прогоняйте `python scripts/verify_detail_parser_window.py` (см. [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), задача B) на машине с доступом к Торгам.

## НСПД-обогащение существующих лотов

Если в БД уже есть лоты с кадастровыми номерами, их можно отдельно проверить через НСПД, не дожидаясь нового ingest:

```bash
cd backend
python scripts/enrich_lots_nspd.py --region 72 --limit 50 --force
```

`--force` нужен для ручного запуска, если в `.env` оставлено `NSPD_ENABLED=false`. Для безопасной проверки без записи в БД используйте `--dry-run`. Скрипт пишет отчёт в `data/raw/nspd_enrich_report.json`.

Если при split tunneling НСПД открывается, но Python падает с `CERTIFICATE_VERIFY_FAILED` / self-signed chain, для локального dev можно временно задать `NSPD_VERIFY_TLS=false`. В production оставляйте `true`.

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
