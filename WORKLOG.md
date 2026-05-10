# WORKLOG - Журнал работ

> **Append-only.** Свежие записи **сверху**.
> Перед началом работы агент читает [AGENTS.md](AGENTS.md) и минимум 1-3 свежих записи отсюда.
> После завершения работы агент **обязательно** добавляет новую запись по шаблону в конце файла.

---

## 2026-05-12 - CI: Alembic `ModuleNotFoundError: app` при `upgrade head`

**Что сделано:** В [`backend/alembic/env.py`](backend/alembic/env.py) перед импортом `app.*` в `sys.path` добавлен корень `backend/` (родитель каталога `alembic/`). В [`.github/workflows/ci.yml`](.github/workflows/ci.yml) для job `migrations` задан `PYTHONPATH: ${{ github.workspace }}/backend`.

**Проверки:** `pytest` — 132 passed.

---

## 2026-05-12 - Лот vs извещение: заголовок строки и ingest title

**Что сделано:** `lot_preferred_list_title` перед fallback на `lots.title` отдаёт `Лот {N} · {regNum}` (и для мультилота без кадастра то же вместо голого «Лот N»). OpenData-ветка `normalize_lot`: в `title` не пишется `noticeName` — приоритет `lots[].lotName`/name, иначе `Лот 1 · {regNum}`. Detail multi-lot без `lotName`: `Лот {N} · {regNum}` вместо склейки с прежним `normalized['title']`. Экспорт CSV и `/api/lots-map` используют preferred title (CSV с batch последних snapshot). Тесты: `test_lot_identity`, `test_normalizer_notices`.

**Файлы:** `backend/app/services/lot_identity.py`, `backend/app/services/ingest/normalizer.py`, `backend/app/services/ingest/service.py`, `backend/app/api.py`, тесты.

**Проверки:** `pytest` — 132 passed.

---

## 2026-05-12 - ПКК на карточке лота: live resolve через геопортал

**Что сделано:** Модуль [`backend/app/services/nspd/resolve_pkk_link.py`](backend/app/services/nspd/resolve_pkk_link.py): при `GET /api/lots/{id}` при `NSPD_ENABLED` и `NSPD_RESOLVE_PKK_LINK_ON_DETAIL` (default true) один запрос `fetch_nspd_features_sync` по кадастру, выбор feature, сборка URL с `selectedCard`; иначе прежний `nspd_lot_map_url`. In-memory TTL-кэш по кадастру 1 ч. Настройка в [`config.py`](backend/app/config.py), [`.env.example`](.env.example). Тесты в [`test_api.py`](backend/tests/test_api.py). Документация: [README.md](README.md), [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md).

**Проверки:** `pytest` — 129 passed.

---

## 2026-05-12 - Dev SQLite: dev_sync_schema + backfill lot_notice_attributes

**Что сделано:** На локальной БД выполнены `python backend/scripts/dev_sync_schema.py` и `python backend/scripts/backfill_lot_notice_attributes.py` (3987 лотов). `pytest` — 126 passed.

---

## 2026-05-12 - API/UI: канон координат и характеристики лота в карточке

**Что сделано:** `GET /api/lots/{id}` отдаёт `notice_attributes` (из `lot_notice_attributes`) и `map_anchor_*`. `map_centroid_available` и `/api/lots-map` учитывают якорь и тот же приоритет, что `lot_map_display_coordinates`. Домклик on-map и ПКК/НСПД deep link по лоту используют `lot_map_display_coordinates` вместо дублирующей логики. На `LotDetailPage` — таблица характеристик ГИС и подсказка по источнику якоря; мини-карта берёт `map_anchor` первым. Тесты API для атрибутов, якоря и точки только с `map_anchor`.

**Файлы:** `backend/app/api.py`, `backend/app/services/external_lot_links.py`, `backend/tests/test_api.py`, `frontend/src/pages/LotDetailPage.tsx`, `AGENTS.md`.

**Проверки:** `pytest` (126), `npx tsc --noEmit`, `npm run test -- --run`.

---

## 2026-05-11 - UI: один пункт «Домклик» (карта, иначе поиск по кадастру)

**Что сделано:** В `LotExternalLinks` одна ссылка «Домклик»: `domclick_map_url ?? domclick_search_url_cadastral`; подсказка зависит от режима. Убраны отдельные строки поиск/карта/расширенный поиск. На `LotDetailPage` сноска про Домклик обновлена под одну ссылку.

**Файлы:** `frontend/src/components/LotExternalLinks.tsx`, `frontend/src/pages/LotDetailPage.tsx`.

**Проверки:** `npx tsc --noEmit`, `npm run test -- --run` — ok.

---

## 2026-05-11 - UI: убрана ссылка «JSON извещения» из блока ссылок лота

**Что сделано:** В `LotExternalLinks` (таблица `/lots` и блок «Ссылки» на `/lots/:id`) удалена строка со ссылкой на JSON извещения; поле `jsonFallbackHref` убрано.

**Файлы:** `frontend/src/components/LotExternalLinks.tsx`, `frontend/src/pages/LotDetailPage.tsx`.

**Проверки:** `npx tsc --noEmit` — ok.

---

## 2026-05-11 - Домклик on-map: региональный host, точные sw/ne, координаты лота

**Что сделано:** `domclick_land_map_url` строит ссылку вида `{base}?deal_type=sale&category=living&offer_type=lot&sw=lat,lon&ne=...&offset=0` с высокой точностью координат; база задаётся `DOMCLICK_ON_MAP_BASE_URL` (по умолчанию `https://domclick.ru/search/on-map`, можно региональный поддомен). Опционально `DOMCLICK_ON_MAP_AIDS`. Координаты по-прежнему: `nspd_centroid_*`, иначе `latitude`/`longitude` из лота.

**Файлы:** `backend/app/config.py`, `external_lot_links.py`, `.env.example`, `test_external_lot_links.py`.

**Проверки:** `pytest` — ok.

---

## 2026-05-11 - Ссылки на лотах: колонка, ПКК, Домклик

**Что сделано:** Таблица `/lots`: колонка «Ссылки», вертикальный список — Карточка (внутренняя), Лот (ГИС Торги), Извещение, JSON при наличии, ПКК, при отличии от ПКК — НСПД (карточка), Домклик: поиск (кадастр, по умолчанию включён отдельным флагом), Домклик: карта (объявления рядом), расширенный поиск при флаге. Карточка лота: тот же компонент `LotExternalLinks`, при `APP_PUBLIC_BASE_URL` — «Карточка в мониторе». API: `pkk_map_url` = `pkk_lot_map_url(lot)` (как `nspd_lot_map_url`: зум/центр/`selectedCard` при обогащении). Настройка `DOMCLICK_CADASTRAL_SEARCH_ENABLED` (default true). Telegram: те же подписи ссылок, ПКК без дубля НСПД при совпадении URL.

**Затронутые файлы:** `backend/app/config.py`, `external_lot_links.py`, `api.py`, `alerts/service.py`, `.env.example`, тесты; `frontend` — `LotExternalLinks.tsx`, `LotsTable.tsx`, `LotDetailPage.tsx`, `styles.css`.

**Проверки:** `pytest` — 122 passed; `npx tsc --noEmit`, `npm run test -- --run` — ok.

---

## 2026-05-11 - API/UI: заголовок строки «Лот» — про лот, не извещение

**Что сделано:** Поле `title` в ответах `/api/lots` и в базовой части `/api/lots/{id}` считается через `lot_preferred_list_title`: приоритет `lotName` / `lotDescription` из последнего `LotSnapshot` (`_notice_lot`), для мультилотов без имени — `Лот {n}` и кадастр, для однолотовых с кадастром — кадастр вместо названия извещения, иначе прежний `lots.title`. Список лотов подгружает последний snapshot пакетно (`max(id)` по `lot_id`).

**Затронутые файлы:** `backend/app/services/lot_identity.py`, `backend/app/api.py`, тесты `test_lot_identity.py`, `test_api.py`.

**Проверки:** `python -m pytest -q` в `backend` — 120 passed.

---

## 2026-05-11 - UI: убран столбец «Baseline» в таблице лотов

**Что сделано:** На странице `/lots` в `LotsTable` удалены колонка Baseline (₽/сотка и дисконт); карточка лота и Dashboard не менялись.

**Затронутые файлы:** `frontend/src/components/LotsTable.tsx`, `frontend/src/styles.css`.

**Проверки:** `npx tsc --noEmit` в `frontend` — ok.

---

## 2026-05-11 - ГИС Торги: `torgi_url` с маршрутом `/(lotInfo:info)`

**Что сделано:** Публичная ссылка на карточку лота (`torgi_lot_html_url` / `torgi_public_url`) дополнена суффиксом `/(lotInfo:info)`, как в официальной SPA (пример: `.../lot/21000023470000000037_1/(lotInfo:info)`), чтобы открывалась вкладка сведений о лоте.

**Затронутые файлы:** `backend/app/services/external_lot_links.py`, тесты `test_external_lot_links.py`, `test_api.py`; документация `docs/MVP_PRODUCT_CONTRACT.md`, `AGENTS.md`, `README.md`, `DEVELOPMENT_PLAN.md`.

**Проверки:** `python -m pytest tests/test_external_lot_links.py tests/test_api.py -q` — 35 passed.

---

## 2026-05-10 - UI: убран столбец «Уверенность» в таблице лотов

**Что сделано:** На странице `/lots` в `LotsTable` удалены колонка и стили «Уверенность» (baseline `valuation_confidence`); на карточке лота (`/lots/:id`) блок не трогался.

**Затронутые файлы:** `frontend/src/components/LotsTable.tsx`, `frontend/src/styles.css`.

**Проверки:** `npx tsc --noEmit` в `frontend` — ok.

---

## 2026-05-10 - MVP-подготовка: все регионы в UI, Telegram только 72

**Что сделано:** Разделены область загрузки/интерфейса и область Telegram-оповещений. Добавлена настройка `TELEGRAM_ALERT_REGION_CODES` (default `72`): база и интерфейс могут работать по всем регионам при пустом `TARGET_REGION_CODES`, а Telegram отправляет только разрешённые регионы. В Telegram-сообщения и digest добавлено примечание о фильтре Тюменской области; `changed_lot` теперь отправляется только при изменении цены (`start_price` / `current_price`), а не при любом изменении snapshot. Ошибки отправки Telegram больше не валят ingest.

**UI/API:** `/api/ingest-status` теперь возвращает `ingest_only_land_lots` и `telegram_alert_region_codes`; страница `/ingest` показывает, что интерфейс/БД идут по всем регионам или по фильтру, а Telegram — отдельно. Dashboard считает качество по всей базе, подписывает, что интерфейс показывает все регионы, и оставляет отдельный shortlist для Telegram-региона 72. `/api/lots-map` и встроенная карта карточки используют fallback на `nspd_centroid_*`, поэтому лоты с НСПД-центроидом попадают на карту.

**Документация:** Обновлены `.env.example`, `README.md`, `docs/MVP_PRODUCT_CONTRACT.md`, `AGENTS.md`: для MVP-показа рекомендовано `TARGET_REGION_CODES=` и `TELEGRAM_ALERT_REGION_CODES=72`.

**Проверки:** `python -m pytest -q` в `backend` — 117 passed; `npx.cmd tsc --noEmit` — ok; `npm.cmd run test -- --run` — 3 passed; `npm.cmd run build` — ok, с прежним предупреждением Vite о крупном lazy chunk карты.

**Нужно вручную в окружении:** Не редактировался реальный `.env`. Перед показом/перезапуском backend нужно выставить `TARGET_REGION_CODES=` (пусто, все регионы в БД/UI) и `TELEGRAM_ALERT_REGION_CODES=72` (Telegram только Тюменская область).

---

## 2026-05-10 - Ревизия кода и логики сервиса

**Что сделано:** Проведена обзорная ревизия backend/frontend без изменения бизнес-кода. Проверены основные контуры: ingest/discovery/detail-parser, multi-lot identity, NSPD enrichment, API `/lots`/`/lots-map`/`/ingest-status`, Telegram alerts/digest, frontend Dashboard/Lots/LotDetail/IngestRuns, миграционная цепочка Alembic.

**Текущее runtime-состояние:** backend на `http://127.0.0.1:8001` отвечает `GET /health`; `/api/lots/quality?region=72`: `total=115`, `izhs_candidates=68`, `with_cadastral=86`, `with_area=115`, `with_price_per_sotka=49`, `with_baseline=49`, `with_positive_discount=24`, `with_nspd_enriched=80`, `with_map_centroid=70`; ingest сейчас не выполняется, планировщик включен.

**Сильные стороны:** пайплайн ingest уже идемпотентный и наблюдаемый; detail-parser покрывает коды ВРИ и текстовые fallback'и; multi-lot извещения имеют стабильную identity; API/UI честно отделяют внутренний baseline от рыночной оценки; Telegram-сообщения содержат рабочие ссылки и фильтры шума; PostgreSQL/Alembic цепочка актуальна, один head `20260511_13_digest_items`.

**Риски / TODO:** `/api/lots-map` и встроенная карта карточки пока используют только `lots.latitude/longitude`, поэтому не показывают лоты с NSPD-центроидом; detail-fetch failures и достижение `INGEST_DETAIL_MAX_PER_RUN` помечают файл как processed, из-за чего часть лотов может остаться без деталей до ручного репроцессинга; сбой Telegram send сейчас может поднять исключение на критическом пути ingest; повторный прогон файла с неподдерживаемой schema version может конфликтовать с уникальным `ingest_manifest(source_url, sha256)`; сортировка/фильтр по дисконту и baseline считаются in-memory; production еще требует auth/ограничение для ручного запуска ingest и реальную интеграцию рыночных аналогов.

**Проверки:** `python -m pytest -q` в `backend` - 115 passed; `npx.cmd tsc --noEmit` в `frontend` - ok; `npm.cmd run test -- --run` - 3 passed; `npm.cmd run build` - ok, с ожидаемым предупреждением Vite о крупном lazy chunk `TradesMap`.

---

## 2026-05-10 - PostgreSQL schema, backfill, NSPD enrichment и restart backend

**Что сделано:** После проверки новой удалённой БД `app-gis-torgi-alert` применены Alembic-миграции на PostgreSQL. Для совместимости с PostgreSQL/Alembic укорочены revision id двух последних миграций: `20260510_12_notice_identity` и `20260511_13_digest_items`, потому что стандартная колонка `alembic_version.version_num` имеет длину 32 символа.

**Загрузка данных:** Выполнен backfill закрытого окна `2026-05-01..2026-05-09` с `TELEGRAM_ALERTS_ENABLED=false`, `TARGET_REGION_CODES=72`, `INGEST_ONLY_LAND_LOTS=true`, `INGEST_DETAIL_MAX_PER_RUN=1000`. Результат: `fetched_count=8670`, `upserted_count=118`, `changed_count=118`, `processed_files=10`, `failed_files=0`.

**НСПД:** Dry-run `--limit 5` прошёл `matched=5/5`; применено обогащение по региону 72: `selected=86`, `matched=80`, `failed=6` (`http=6`). После enrichment в БД: `with_nspd_enriched=80`, `with_map_centroid=70`, `with_nspd_card=80`.

**Итоговые метрики PostgreSQL:** `lots=115`, `opendata_notices=108`, `ingest_manifest=10`, `ingest_runs=1`, `alert_events=0`, `telegram_digest_items=0`, `izhs_candidates=68`, `with_cadastral=86`, `category=ZK` для всех лотов, keyword-проверка авто/древесины/помещений/транспорта — 0 совпадений.

**Runtime:** Старый backend на 8001 остановлен, затем backend перезапущен на `http://127.0.0.1:8001` уже с PostgreSQL `.env` и переменными `TARGET_REGION_CODES=72`, `INGEST_ONLY_LAND_LOTS=true`, `NSPD_VERIFY_TLS=false`; frontend продолжает отвечать на `http://127.0.0.1:5173`.

**Проверки:** `GET /health`, `GET /api/ingest-status`, `GET /api/lots/quality`, `GET /api/lots?limit=1&has_cadastral=true`, `GET /` frontend — ok. Визуально проверены `/`, `/lots`; консоль браузера без ошибок, ссылки `ГИС лот`/`Извещение`/`ПКК`/`НСПД`/`Домклик` отображаются. `python -m pytest -q` в `backend`: 115 passed. `npx.cmd tsc --noEmit` в `frontend`: ok.

**Известные проблемы / TODO:** Dashboard shortlist всё ещё показывает ИЖС-кандидатов с отрицательным дисконтом; стоит либо фильтровать только `has_positive_discount=true`, либо переименовать блок в «ИЖС с рассчитанным baseline».

---

## 2026-05-10 - Проверка удалённой PostgreSQL после смены DATABASE_URL

**Что сделано:** Повторно проверена свежая конфигурация `.env` без вывода секрета. `DATABASE_URL` теперь указывает на существующую БД `app-gis-torgi-alert` через `postgresql+psycopg`.

**Результат проверки:** подключение к PostgreSQL проходит (`PostgreSQL 16.13`, schema `public`, `select 1` ok). База пустая: `tables_count=0`, отсутствуют `alembic_version`, `lots`, `opendata_notices`, `ingest_manifest`, `ingest_runs`, `alert_events`, `telegram_digest_items`, `market_comparables`.

**Текущий runtime:** уже запущенный backend на `http://127.0.0.1:8001` всё ещё отвечает и показывает прежние 115 лотов, но это старый процесс/старая БД в памяти процесса; его ответы не подтверждают работу новой PostgreSQL-БД.

**TODO:** Выполнить `python -m alembic upgrade head` на новой БД, затем перезапустить backend и загрузить данные/backfill уже в PostgreSQL.

---

## 2026-05-10 - Повторная проверка удалённой PostgreSQL-БД

**Что сделано:** Повторно проверена текущая строка `DATABASE_URL` без вывода секрета. Схема драйвера теперь корректная: `postgresql+psycopg`.

**Результат проверки:** целевая БД из `.env` (`gis-torgi-alert`) по-прежнему отсутствует на сервере. Через служебную БД `postgres` найдена похожая существующая база `app-gis-torgi-alert`; подключение к ней проходит, но она пустая: нет `alembic_version`, `lots`, `opendata_notices`, `ingest_manifest`, `ingest_runs`, `alert_events`, `telegram_digest_items`, `market_comparables`.

**Права:** пользователь не имеет `CREATEDB`, но в базе `app-gis-torgi-alert` имеет `USAGE/CREATE` для schema `public` и право `CREATE` в базе, то есть миграции схемы должны иметь возможность создать таблицы.

**TODO:** Либо создать на сервере БД `gis-torgi-alert`, либо изменить имя БД в `DATABASE_URL` на `app-gis-torgi-alert`, затем выполнить `alembic upgrade head` и перезапустить backend уже с новой БД.

---

## 2026-05-10 - Проверка подключения к удалённой PostgreSQL-БД

**Что сделано:** Проверена новая конфигурация `DATABASE_URL` без вывода секрета из `.env`. Текущий уже запущенный backend на 8001 продолжает отвечать, но новая конфигурация при свежем подключении пока неработоспособна.

**Результат проверки:** строка подключения указывает на PostgreSQL и сервер доступен через служебную БД `postgres`; драйвер `psycopg` v3 установлен. При подключении к целевой БД сервер возвращает `database does not exist`. У текущего пользователя нет права `CREATEDB`, поэтому создать базу с этой учётной записью нельзя.

**Известные проблемы / TODO:** В `DATABASE_URL` нужно использовать схему `postgresql+psycopg://...`, как в README/`.env.example`; схема `postgresql://...` заставляет SQLAlchemy искать `psycopg2`. На сервере нужно создать целевую БД или указать существующую, затем выполнить `alembic upgrade head` и перезапустить backend.

---

## 2026-05-10 - Проверка состояния сервиса и dev-перезапуск backend на 8001

**Что сделано:** Проверено текущее состояние ветки `codex/gis_torgi_v2`: рабочее дерево чистое, ветка синхронизирована с `origin/codex/gis_torgi_v2` на коммите `49778ed`. Проверены live API и UI: frontend отвечает на `http://127.0.0.1:5173`, актуальный backend поднят на `http://127.0.0.1:8001` из-за прежней проблемы с портом 8000. Backend перезапущен на 8001 с `TARGET_REGION_CODES=72`, `INGEST_ONLY_LAND_LOTS=true`, `NSPD_VERIFY_TLS=false`; `/api/ingest-status` подтверждает `target_region_codes=72`, сам land-filter проверен через settings.

**Метрики dev-БД:** `lots=115`, `izhs_candidates=68`, `with_cadastral=86`, `with_nspd_enriched=80`, `with_map_centroid=70`, `with_notice_identity=115`; `market_comparables=0`, `alert_events=0`, `telegram_digest_items=0`.

**Проверки:** `GET /health`, `GET /api/ingest-status`, `GET /api/lots/quality`, `GET /api/lots?limit=1&has_cadastral=true`, `GET /` frontend; визуально проверены страницы `/`, `/lots`, `/ingest` без ошибок консоли. `python -m pytest` в `backend`: 115 passed. `npx.cmd tsc --noEmit` в `frontend`: ok.

**Известные проблемы / TODO:** `/api/ingest-status` не показывает `ingest_only_land_lots`, хотя настройка есть и применяется; Dashboard-блок «Потенциально интересные ИЖС-кандидаты» сейчас выводит ИЖС с любым baseline, а в текущей БД ИЖС с положительным дисконтом нет, поэтому текст/фильтр блока нужно уточнить.

---

## 2026-05-10 - Push в GitHub: ветка codex/gis_torgi_v2

**Что сделано:** Закоммичены накопленные изменения (ПКК/НСПД, Домклик, Telegram-алерты, демо-скрипт, UI/API/тесты/доки) и выполнен `git push origin codex/gis_torgi_v2` (`5394c44..e1d45b4`).

---

## 2026-05-10 - Перезапуск dev: порт 8001 из-за «фантома» на 8000; проверка ПКК/НСПД

**Что сделано:** На Windows `127.0.0.1:8000` оставался отвечать старый экземпляр API (`pkk_map_url` = null при живом `nspd_map_url`); новый uvicorn не мог занять порт (ошибка bind). Остановлены видимые `python`/Vite; актуальный backend поднят на **8001**, Vite на **5173** с `VITE_API_BASE_URL=http://127.0.0.1:8001`. Проверка: `GET /api/lots?has_cadastral=true` — `pkk_map_url` с `query=...`, `nspd_map_url` с `selectedCard` при обогащении; открыт `/lots` в браузере.

**Проверки:** `Invoke-RestMethod` к `http://127.0.0.1:8001/api/lots?limit=1&has_cadastral=true`.

**Известные проблемы / TODO:** Слушатель на `:8000` с PID без живого процесса в `tasklist` — при необходимости перезагрузка ОС или разбор портов; до этого для dev использовать 8001 или освободить 8000 вручную.

---

## 2026-05-10 - ПКК: рабочие ссылки через НСПД; Домклик domclick.ru; таблица лотов

**Что сделано:**
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): `pkk_map_url` / `rosreestr_cadastral_map_url` = тот же `nspd.gov.ru/map` с ПКК-слоем и `query` по кадастру (старый `pkk.rosreestr.ru/#/search` часто не открывается); карта Домклик всегда с `https://domclick.ru/search/on-map`; нормализация `http://torgi.gov.ru` → `https` для JSON/официальных href.
- UI: [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx) — ссылка «НСПД», если `nspd_map_url` отличается от ПКК (обогащённый deep link); подписи ПКК уточнены в [LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx), Telegram «ПКК (НСПД)».
- Тесты и [AGENTS.md](AGENTS.md) обновлены под новые URL.

**Проверки:** `python -m pytest` в `backend`; `npx tsc --noEmit` в `frontend`.

---

## 2026-05-10 - Скрипт демо-алерта Telegram (как в проде)

**Что сделано:** [backend/scripts/send_telegram_demo_alert.py](backend/scripts/send_telegram_demo_alert.py) — in-memory SQLite, несколько лотов для baseline, один синтетический ИЖС-лот с кадастром и дисконтом к baseline; вызов `notify_lot_event` (тот же HTML, что при ingest). Команда: `python scripts/send_telegram_demo_alert.py` из `backend/`. В [AGENTS.md](AGENTS.md) добавлена строка в список скриптов.

---

## 2026-05-10 - Telegram: меньше шума без regNum ГИС; подсказка в тексте алерта

**Что сделано:**
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): уточнён `_is_low_signal_alert` — после базовой проверки (не ИЖС, нет кадастра, нет ₽/сотки и дисконта) дополнительно не слать алерт, если нет `regNum` извещения и нет положительного `discount_to_baseline` (отсекаются тестовые строки с ценой/площадью без привязки к ГИС).
- Строка «ГИС: извещение не определено» дополняется `source_id` или `id лота` для отладки.
- Тест [backend/tests/test_alerts_service.py](backend/tests/test_alerts_service.py) `test_notify_skips_lot_with_price_per_sotka_but_no_gis_notice`.

**Проверки:** `python -m pytest` в `backend`: 115 passed.

---

## 2026-05-10 - Лоты: убраны быстрые фильтры «С ₽/сотка» и «С дисконтом»

**Что сделано:**
- [frontend/src/pages/LotsPage.tsx](frontend/src/pages/LotsPage.tsx): удалены чекбоксы и query/API-параметры `has_price_per_sotka`, `has_positive_discount`; сортировки по сотке и дисконту в выпадающем списке сохранены.
- [frontend/src/pages/DashboardPage.tsx](frontend/src/pages/DashboardPage.tsx): shortlist ИЖС больше не накладывает эти два фильтра при загрузке.

**Проверки:** `npx tsc --noEmit`, `npm run test` в `frontend`.

---

## 2026-05-10 - Убраны Авито/Циан из ссылок; колонка «Домклик»

**Что сделано:**
- API/UI/Telegram: удалены поля и ссылки Авито и Циан; из [backend/app/config.py](backend/app/config.py) убраны `INCLUDE_MARKETPLACE_QUICK_LINKS`, шаблоны Avito/Cian; [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py) — только Домклик (карта + опциональный поиск).
- Таблица лотов: подпись ссылки на карту — «Домклик» вместо «Цены рядом» ([frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx)).
- Документация и `.env.example` синхронизированы; [backend/scripts/check_external_hosts.py](backend/scripts/check_external_hosts.py) — без avito/cian.

**Проверки:**
- `pytest` в `backend`: 114 passed.
- `npx tsc --noEmit`, `npm run test` в `frontend`: ок.

---

## 2026-05-11 - План roadmap: агрегаторы, НСПД, Telegram digest, рынок, prod-CI

**Что сделано:**
- Региональные шаблоны Авито/Циан для ряда субъектов РФ; скрипт [backend/scripts/check_external_hosts.py](backend/scripts/check_external_hosts.py) (DNS + HEAD, IP для WireSock).
- Расширен land-filter (лес/квартира и др. маркеры); скрипт закрытого backfill-окна [backend/scripts/run_backfill_closed_window.py](backend/scripts/run_backfill_closed_window.py); `/api/lots/quality` — счётчики НСПД и центроида; API/UI: `nspd_data_status`, `map_centroid_available`, рыночные поля и `investment_score` через [backend/app/services/market_median.py](backend/app/services/market_median.py); импорт аналогов [backend/scripts/import_market_comparables_json.py](backend/scripts/import_market_comparables_json.py).
- НСПД: `--only-missing`, детализация ошибок в отчёте enrich; регрессия ссылок (тесты domclick/NSPD уже были — добавлен тест региональных quick links).
- Telegram: `TELEGRAM_DIGEST_*`, очередь `telegram_digest_items`, `flush_telegram_digest`, APScheduler job; `TELEGRAM_ALERT_REQUIRE_DISCOUNT_OR_PER_SOTKA`; блок «Почему интересно»; `/api/ingest-status` — поля digest.
- Prod/dev: `create_all` только для SQLite; Docker CMD `alembic upgrade head`; CI job `migrations` на PostgreSQL; README — docker, backup, скрипты.

**Проверки:**
- `python -m pytest` в `backend`: 115 passed.
- `npx tsc --noEmit`, `npm run test`, `npm run build` в `frontend`: ок.

---

## 2026-05-10 - ПКК Росреестра (`pkk_map_url`) и актуализация тестов

**Что сделано:**
- `pkk_map_url` / `rosreestr_cadastral_map_url` в [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): ссылка на поиск ПКК по кадастровому номеру (`pkk.rosreestr.ru`).
- Тесты: [backend/tests/test_external_lot_links.py](backend/tests/test_external_lot_links.py), [backend/tests/test_api.py](backend/tests/test_api.py) (`pkk_map_url` в деталях лота), [backend/tests/test_alerts_service.py](backend/tests/test_alerts_service.py) (домен ПКК и подписи «НСПД (ФГИС ЕГРН)», «Домклик (цены участков рядом)»).

**Проверки:**
- `pytest` в `backend`: 116 passed.
- `npx tsc --noEmit`, `npm run test` в `frontend`: ок.

---

## 2026-05-10 - Верификация ссылок ГИС для multi-lot (продолжение)

**Что сделано:**
- Live API: `GET /api/lots/101` и лот `101` в `GET /api/lots?limit=500` — `torgi_url` = `https://torgi.gov.ru/new/public/lots/lot/21000030190000000072_2`, `torgi_notice_url` на извещение без номера лота.
- SQL по `data/app.db`: для всех групп с `notice_lot_count > 1` минимальный числовой `notice_lot_number` равен `1` (в демо-наборе нет извещения, где нумерация внутренних лотов начинается не с единицы).
- Кейс «внутренний лот не первый» покрыт тестом [backend/tests/test_api.py](backend/tests/test_api.py) `test_lots_list_uses_stored_notice_identity_for_torgi_lot_url` (`notice_lot_number=7`, список `/api/lots` без подгрузки `LotSnapshot`).

**Проверки:**
- `python -m pytest` в `backend`: 111 passed.

**Следующее:** при появлении в прод-данных извещения с `lotNumber` не с `1` — повторить spot-check; опционально `git commit` / `push` ветки `codex/gis_torgi_v2` по запросу.

---

## 2026-05-10 - Стабильная идентичность multi-lot извещений

**Что сделано:**
- Добавлены поля `lots.notice_reg_num`, `lots.notice_lot_number`, `lots.notice_lot_count` для стабильной привязки внутренних лотов к извещению ГИС Торги.
- Добавлена Alembic-миграция `20260510_12_lot_notice_identity_fields`; `dev_sync_schema.py` применён к локальной SQLite.
- Ingest теперь сохраняет `notice_*` при detail-fetch и multi-lot split; event-документы ищут связанные лоты также по `Lot.notice_reg_num`.
- Вынесен общий helper [backend/app/services/lot_identity.py](backend/app/services/lot_identity.py), чтобы API, Telegram и external links использовали одинаковую логику fallback.
- Добавлен backfill [backend/scripts/backfill_lot_notice_identity.py](backend/scripts/backfill_lot_notice_identity.py); текущая dev-БД обновлена: `115` из `115` лотов получили `notice_reg_num` и `notice_lot_number`.
- Обновлены [backend/scripts/link_lots_to_notices.py](backend/scripts/link_lots_to_notices.py) и demo-loader, чтобы при догонке/демо тоже заполнялись новые поля.
- Обновлена документация: [AGENTS.md](AGENTS.md), [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md).

**Проверки:**
- `python -m pytest tests/test_lot_identity.py tests/test_external_lot_links.py tests/test_api.py tests/test_ingest_service.py`: 49 passed.
- `python -m pytest` в `backend`: 111 passed.
- `npx.cmd tsc --noEmit` в `frontend`: прошло.
- `npm.cmd run test -- --run`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- Live API `GET http://localhost:8000/api/lots?limit=1&has_cadastral=true`: `notice_lot_number=1`, `notice_lot_count=5`, `torgi_url=https://torgi.gov.ru/new/public/lots/lot/22000004000000000180_1`.
- `GET http://localhost:8000/health`: `{"status":"ok"}`; `GET http://localhost:5173`: HTTP 200.

**TODO:**
- При следующем clean ingest проверить несколько свежих multi-lot извещений, где первый внутренний `lotNumber` не равен `1`, чтобы подтвердить, что список `/api/lots` строит ссылку строго из сохранённого `notice_lot_number`.

---

## 2026-05-10 - Быстрые ссылки Авито/Циан по кадастру

**Что сделано:**
- Добавлен флаг `INCLUDE_MARKETPLACE_QUICK_LINKS=true`: API/UI/Telegram теперь показывают быстрые кадастровые ссылки на Авито и Циан даже при выключенном расширенном `INCLUDE_MARKETPLACE_SEARCH_URLS`.
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): добавлены региональные шаблоны для Тюменской области:
  - Авито: `https://www.avito.ru/tyumen/zemelnye_uchastki?q={q}`;
  - Циан: `https://tyumen.cian.ru/kupit-zemelniy-uchastok-tyumenskaya-oblast/?text={q}`.
- [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx): в таблице лотов добавлены короткие действия `Авито` и `Циан`.
- [frontend/src/styles.css](frontend/src/styles.css): исправлен mobile overflow карточки лота; строки `card__row` на узких экранах переходят в вертикальный layout, примечания переносят длинные кадастровые номера.
- Обновлена документация: [.env.example](.env.example), [AGENTS.md](AGENTS.md), [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md).

**Проверки:**
- `python -m pytest tests/test_external_lot_links.py tests/test_api.py tests/test_alerts_service.py`: 42 passed.
- `python -m pytest` в `backend`: 106 passed.
- `npx.cmd tsc --noEmit` в `frontend`: прошло.
- `npm.cmd run test -- --run`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- Live API `GET http://127.0.0.1:8000/api/lots?limit=1&has_cadastral=true`: для лота `101` появились `avito_search_url_cadastral` и `cian_search_url_cadastral`.
- Визуально проверены `http://localhost:5173/lots` и `http://localhost:5173/lots/101`; скриншоты сохранены в `data/tmp/visual-review/`.
- `GET http://localhost:8000/health`: `{"status":"ok"}`; `GET http://localhost:5173`: HTTP 200.

**TODO:**
- Позже можно добавить региональные шаблоны Авито/Циан для других регионов, когда ingest снова будет загружать не только `72`.

---

## 2026-05-10 - Проверка кода и визуальная оценка сервиса

**Что сделано:**
- Проведён review текущего diff после разведения ссылок ГИС Торги на `torgi_url` (лот) и `torgi_notice_url` (извещение).
- Проверены live-экраны `http://localhost:5173/`, `/lots`, `/lots/101`, `/ingest` через браузерный DOM.
- Сняты desktop/mobile скриншоты Chrome в `data/tmp/visual-review/` для Dashboard, списка лотов и карточки лота.
- Подтверждено, что `/api/lots?limit=1&has_cadastral=true` отдаёт:
  - `torgi_url=https://torgi.gov.ru/new/public/lots/lot/21000030190000000072_2`;
  - `torgi_notice_url=https://torgi.gov.ru/new/public/notices/view/21000030190000000072`.

**Проверки:**
- `python -m pytest` в `backend`: 105 passed.
- `npx.cmd tsc --noEmit` в `frontend`: прошло.
- `npm.cmd run test -- --run`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.
- Browser console на `/ingest`: ошибок нет.

**Наблюдения:**
- Desktop `/lots` и `/lots/101`: ссылки `ГИС лот` / `Извещение` визуально разделены и читаются.
- Mobile `/lots/101`: есть горизонтальный overflow в блоке `Проверка источника`; правые ссылки обрезаются на ширине около 390px.
- Mobile `/lots`: фильтры читаемы, но таблица закономерно рассчитана на горизонтальный скролл из-за `min-width: 1180px`.
- Кодовый риск: список `/api/lots` не подгружает `latest_payload` для каждой строки, поэтому для первого лота multi-lot извещения без суффикса `:lot:` ссылка строится как `{regNum}_1`. В текущей dev-БД первые лоты multi-lot действительно имеют `lotNumber=1`, но при нестандартной нумерации безопаснее будет передавать snapshot payload или хранить `notice_lot_number` отдельно.

**TODO:**
- Исправить mobile overflow карточки: на `max-width: 720px` перевести `.card__row` в вертикальный layout, убрать `text-align:right` у значения и дать ссылкам переноситься по строкам.
- Для долгосрочной надёжности ссылок ГИС Торги вынести `notice_lot_number` в поле модели/БД или подмешивать latest snapshot payload в list endpoint без N+1.

---

## 2026-05-10 - ГИС Торги: отдельные ссылки на лот и извещение

**Что сделано:**
- Проверен VPN-bypass/сетевой доступ после добавления IP:
  - `torgi.gov.ru`: DNS `95.167.245.141`, HTTP 302 -> 200;
  - `nspd.gov.ru`: DNS `2.63.246.71-76`, HTTP 200;
  - `tyumen.domclick.ru` и `domclick.ru`: DNS `178.248.234.210`, HTTP 200;
  - `avito.ru`: DNS `176.114.120.24/122.24/124.24`, HTTP 301 -> 429;
  - `cian.ru`: DNS `51.250.123.126`, HTTP 302 -> 404 на корень.
- Проверен публичный формат ГИС Торги: конкретный лот открывается по `https://torgi.gov.ru/new/public/lots/lot/{regNum}_{lotNumber}`, извещение отдельно по `https://torgi.gov.ru/new/public/notices/view/{regNum}`.
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): добавлен `torgi_lot_html_url`; `torgi_public_url` теперь предпочитает конкретную карточку лота и только затем fallback на извещение/JSON.
- API [backend/app/schemas.py](backend/app/schemas.py), [backend/app/api.py](backend/app/api.py): добавлено поле `torgi_notice_url`; `torgi_url` теперь означает ссылку на конкретный лот.
- Telegram [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): в блоке ссылок отдельно добавляются `ГИС Торги (лот)` и `ГИС Торги (извещение)`.
- Frontend [frontend/src/types.ts](frontend/src/types.ts), [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx), [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx): таблица и карточка показывают отдельные ссылки на лот и извещение.
- Обновлена документация по контракту ссылок: [AGENTS.md](AGENTS.md), [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md).

**Проверки:**
- `python -m pytest tests/test_external_lot_links.py tests/test_api.py tests/test_alerts_service.py`: 41 passed.
- `python -m pytest` в `backend`: 105 passed.
- `npx.cmd tsc --noEmit` в `frontend`: прошло.
- `GET http://localhost:8000/api/lots?limit=1&has_cadastral=true`: `torgi_url=https://torgi.gov.ru/new/public/lots/lot/21000030190000000072_2`, `torgi_notice_url=https://torgi.gov.ru/new/public/notices/view/21000030190000000072`.
- `GET http://localhost:8000/health`: `{"status":"ok"}`.
- `GET http://localhost:5173`: HTTP 200.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.

**TODO:**
- Руками открыть несколько ссылок `torgi_url` из UI и убедиться, что SPA ГИС Торги выбирает нужный лот без дополнительного клика.

---

## 2026-05-10 - Clean reset dev-БД на текущем компьютере

**Что сделано:**
- `D:\Property_Auctions` на компьютере не найден; актуальная рабочая копия проекта была в `F:\Property_Auctions`, операции выполнены там.
- Проверены `AGENTS.md`, свежий `WORKLOG.md`, `git status`, ветка `codex/gis_torgi_v2`, remote `https://github.com/Ki1aa/property-auctions.git`.
- Выполнен `git pull origin cursor`: уже актуально на `1e19dd3 feat: harden MVP land lot monitoring`.
- Порты `8000` и `5173` перед reset были свободны.
- Текущая `data/app.db` сохранена в `data/backups/app-before-clean-reset-20260510-165815.db`, затем удалена только `data/app.db`.
- Создана чистая SQLite-схема через `scripts/dev_sync_schema.py`. В этой рабочей копии нет `.venv312`, поэтому использован системный Python 3.12.
- Выполнен live backfill за закрытое окно `2026-05-01` - `2026-05-09` с process-level переменными:
  - `TELEGRAM_ALERTS_ENABLED=false`;
  - `TARGET_REGION_CODES=72`;
  - `INGEST_ONLY_LAND_LOTS=true`;
  - `INGEST_DETAIL_MAX_PER_RUN=1000`.
- Backfill завершился без падений: `fetched_count=8670`, `upserted_count=118`, `processed_files=10`, `failed_files=0`.
- НСПД dry-run с `NSPD_VERIFY_TLS=false`: `5/5 matched`; затем применено обогащение `--region 72 --limit 0 --force --include-fresh --commit-every 10`: `selected=86`, `matched=80`, `failed=6`.
- Backend и frontend подняты заново:
  - backend: `http://localhost:8000`, process-level `TARGET_REGION_CODES=72`, `INGEST_ONLY_LAND_LOTS=true`, `NSPD_VERIFY_TLS=false`;
  - frontend: `http://localhost:5173`.

**Итоговые данные:**
- `lots`: 115.
- `opendata_notices`: 108.
- `ingest_manifest`: 10.
- `alert_events`: 0.
- `lot_snapshots`: 118.
- Все `lots.category=ZK`.
- ИЖС-кандидатов: 68.
- С кадастром: 86.
- С НСПД-центроидом: 70.
- С `nspd_card_id`: 80.
- Явных маркеров non-land assets (`автомоб`, `древес`, `здани`, `помещен`, `транспорт`) в `lots` не найдено.
- `/api/lots?limit=1&has_cadastral=true` вернул лот с `nspd_map_url` c `selectedCard` и `domclick_map_url`.

**Проверки:**
- `GET http://localhost:8000/health`: `{"status":"ok"}`.
- `GET http://localhost:8000/api/ingest-status`: scheduler running, `target_region_codes="72"`.
- `GET http://localhost:8000/api/lots/quality`: `total=115`, `izhs_candidates=68`, `with_cadastral=86`, `with_area=115`, `with_baseline=49`, `with_positive_discount=24`.
- `GET http://localhost:8000/api/lots?limit=1&has_cadastral=true`: есть `nspd_map_url` и `domclick_map_url`.
- `GET http://localhost:5173`: HTTP 200.
- `python -m pytest` в `backend`: 104 passed.
- `npx.cmd tsc --noEmit` в `frontend`: прошло.
- Сетевой доступ:
  - `torgi.gov.ru`: доступен, IP `95.167.245.141`;
  - `nspd.gov.ru`: доступен, IP `2.63.246.71-76`;
  - `domclick.ru` / `tyumen.domclick.ru`: DNS есть, но `curl` уходит в timeout, IP `178.248.234.210`;
  - `avito.ru`: доступен до HTTP, отвечает `429`, IP `176.114.120.24`, `176.114.122.24`, `176.114.124.24`;
  - `cian.ru`: доступен до HTTP, IP `51.250.123.126`.

**TODO:**
- Если Домклик нужен для ручной проверки карт, добавить `178.248.234.210` в VPN-bypass и повторить открытие `tyumen.domclick.ru`.
- При необходимости создать локальную копию именно в `D:\Property_Auctions`; сейчас рабочий проект находится в `F:\Property_Auctions`.

---

## 2026-05-10 - Домклик-карта района по bbox вокруг участка

**Что сделано:**
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): добавлен `domclick_land_map_url(lot)`:
  - берёт координаты из `lot.nspd_centroid_latitude/longitude`, fallback — `lot.latitude/longitude`;
  - строит bbox вокруг точки с радиусом `MARKETPLACE_MAP_RADIUS_KM` (по умолчанию 5 км);
  - формирует ссылку Домклик `search/on-map` с `deal_type=sale`, `category=living`, `offer_type=lot`, `sw`, `ne`, `offset=0`;
  - для региона `72` использует `tyumen.domclick.ru`, для `86` — `xanty-mansijsk.domclick.ru`, для `89` — `salekhard.domclick.ru`, иначе fallback `domclick.ru`.
- [backend/app/config.py](backend/app/config.py), [.env.example](.env.example): добавлены `INCLUDE_MARKETPLACE_MAP_URLS=true` и `MARKETPLACE_MAP_RADIUS_KM=5`. Текстовые поиски агрегаторов по-прежнему управляются отдельным `INCLUDE_MARKETPLACE_SEARCH_URLS=false`.
- [backend/app/schemas.py](backend/app/schemas.py), [backend/app/api.py](backend/app/api.py): в API лота добавлено поле `domclick_map_url`.
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): Telegram-карточка добавляет ссылку `Домклик (карта района)` при наличии центроида.
- [frontend/src/types.ts](frontend/src/types.ts), [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx), [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx): UI показывает `Домклик карта` в карточке лота и краткую ссылку в таблице.
- Проверен НСПД-энричмент:
  - сухой прогон без `NSPD_VERIFY_TLS=false` падал на `CERTIFICATE_VERIFY_FAILED`;
  - с process-level `NSPD_VERIFY_TLS=false` dry-run нашёл 5/5 кадастров;
  - применён ручной enrichment `python scripts/enrich_lots_nspd.py --region 72 --limit 0 --force --include-fresh --commit-every 10` с `NSPD_VERIFY_TLS=false`.

**Итоговые данные:**
- В текущей dev-БД `lots`: 115.
- НСПД проверил 86 кадастров: 80 matched, 6 failed.
- `nspd_card_id/type` заполнены у 80 лотов.
- НСПД-центроид заполнен у 70 лотов.
- `domclick_map_url` появляется у 70 лотов.
- Пример API отдаёт ссылку вида `https://tyumen.domclick.ru/search/on-map?deal_type=sale&category=living&offer_type=lot&sw=...&ne=...&offset=0`.

**Проверки:**
- `.\\.venv312\\Scripts\\python.exe -m pytest tests/test_external_lot_links.py tests/test_api.py tests/test_alerts_service.py`: 40 passed.
- `.\\.venv312\\Scripts\\python.exe -m pytest`: 104 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test -- --run`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `GET http://localhost:8000/api/lots?limit=1&has_cadastral=true`: поле `domclick_map_url` присутствует у лота с НСПД-центроидом.
- `GET http://localhost:5173`: HTTP 200.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.

**TODO:**
- Для автоматического появления `domclick_map_url` у новых лотов включить НСПД-энричмент в dev/prod окружении (`NSPD_ENABLED=true`; локально при текущей TLS-проблеме ещё `NSPD_VERIFY_TLS=false`).
- Проверить руками несколько Домклик-карт: насколько bbox 5 км удобен для Тюмени/районов; при необходимости уменьшить радиус для города и увеличить для сельских участков.
- Следующий слой — аналогичные map-link стратегии для Авито/Циан, если найдём стабильные URL-параметры карты.

---

## 2026-05-10 - Land-filter: автомобили и прочее имущество исключены из lots

**Что сделано:**
- [backend/app/config.py](backend/app/config.py), [.env.example](.env.example): добавлен флаг `INGEST_ONLY_LAND_LOTS=true` по умолчанию. Это продуктовый MVP-фильтр: в рабочую таблицу `lots` попадают только земельные участки / права на земельные участки.
- [backend/app/services/ingest/service.py](backend/app/services/ingest/service.py): после detail-fetch добавлен land-filter:
  - пропускает земельные лоты по `ZK`, ИЖС-признаку и явным маркерам земельного участка;
  - отсекает автомобили, автобусы, мототехнику, спецтехнику, транспорт, древесину, лесные насаждения, здания, помещения, гаражи, машиноместа и объекты незавершенного строительства;
  - не использует слишком широкий маркер `землях`, чтобы древесина на землях лесного фонда не проходила как земельный участок.
- [backend/tests/test_ingest_service.py](backend/tests/test_ingest_service.py): добавлены тесты, что non-land assets не создают `Lot`, а timber/building cases отклоняются.
- [README.md](README.md), [AGENTS.md](AGENTS.md), [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md): задокументирован продуктовый фильтр земельных лотов.
- Dev-БД пересобрана live-загрузкой за `2026-05-01` - `2026-05-09` с `TARGET_REGION_CODES=72`, `INGEST_ONLY_LAND_LOTS=true`, `TELEGRAM_ALERTS_ENABLED=false`, `INGEST_DETAIL_MAX_PER_RUN=1000`.
- Перед пересборками сохранены backup-файлы:
  - `data/backups/app-before-land-filter-reset-20260510-051832.db`;
  - `data/backups/app-before-strict-land-filter-reset-20260510-052200.db`.
- Backend перезапущен с process-level `TARGET_REGION_CODES=72` и `INGEST_ONLY_LAND_LOTS=true`; frontend оставлен запущенным.

**Итоговые данные:**
- `lots`: 115, все `category=ZK`.
- `opendata_notices`: 108.
- `lot_snapshots`: 118.
- `alert_events`: 0, Telegram во время bulk-загрузки не отправлялся.
- Явных asset-маркеров в `lots` (`автомоб`, `древес`, `здани`, `помещен`, `транспорт`) не осталось.
- Качество `/api/lots/quality`: 115 всего, 68 ИЖС-кандидатов, 86 с кадастром, 115 с площадью, 49 с baseline, 24 с положительным дисконтом.

**Проверки:**
- `.\\.venv312\\Scripts\\python.exe -m pytest tests/test_ingest_service.py`: 11 passed.
- `.\\.venv312\\Scripts\\python.exe -m pytest`: 101 passed.
- `GET http://localhost:8000/health`: `{"status":"ok"}`.
- `GET http://localhost:8000/api/ingest-status`: scheduler running, `target_region_codes="72"`, следующий запуск `2026-05-11T05:23:56+05:00`.
- `GET http://localhost:8000/api/lots/quality`: корректная сводка по strict land-БД.
- `GET http://localhost:8000/api/lots?limit=5&sort=discount_to_baseline_desc`: API отдаёт только земельные лоты.
- `GET http://localhost:5173`: HTTP 200.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.

**TODO:**
- Если strict land-filter подтвердится на ещё одном live-окне, можно сделать следующий слой: `INGEST_ONLY_IZHS_CANDIDATES` или Telegram-фильтр `TELEGRAM_ALERT_ONLY_IZHS=true` для совсем тихого рабочего потока.
- `opendata_notices` пока хранит все извещения региона как сырой технический слой; если техническая страница Notices начнёт мешать пользователю, добавить аналогичный фильтр или скрыть её окончательно из MVP UI.

---

## 2026-05-10 - Чистый live-reset dev-БД по региону 72

**Что сделано:**
- Остановлены dev-процессы backend/frontend перед операциями с SQLite.
- Текущая `data/app.db` не удалена безвозвратно, а перенесена в backup: `data/backups/app-before-live-reset-20260510-050457.db`.
- Создана новая чистая SQLite-БД через `python scripts/dev_sync_schema.py`, уже с актуальными колонками текущих моделей.
- Выполнен live backfill ГИС Торги за окно `2026-05-01` - `2026-05-09` с временными переменными процесса:
  - `TARGET_REGION_CODES=72`;
  - `TELEGRAM_ALERTS_ENABLED=false`;
  - `INGEST_DETAIL_MAX_PER_RUN=1000`.
- Первый пробный live backfill до `2026-05-10` показал ожидаемую ошибку источника: файл `20260510T0000-20260511T0000` ещё не опубликован ГИС Торги. Чтобы clean-БД не стартовала с `partial_failed`, база была пересобрана заново и загружена до последнего доступного дневного среза.
- Backend и frontend подняты заново; backend запущен с process-level `TARGET_REGION_CODES=72`, чтобы scheduled/manual ingest в этой dev-сессии оставался в MVP-рамке Тюменской области без правки реального `.env`.
- [.gitignore](.gitignore): добавлены `data/backups/` и `data/tmp/`, чтобы локальные backup/temp-артефакты reset-процедуры не попадали в `git status`.

**Итоговые данные:**
- `lots`: 225.
- `opendata_notices`: 108.
- `lot_snapshots`: 228.
- `alert_events`: 0, Telegram во время bulk-загрузки не отправлялся.
- `ingest_manifest`: 10, все в статусе `processed`.
- Качество `/api/lots/quality` по региону `72`: 225 всего, 68 ИЖС-кандидатов, 117 с кадастром, 149 с площадью, 83 с baseline, 38 с положительным дисконтом.

**Проверки:**
- `GET http://localhost:8000/health`: `{"status":"ok"}`.
- `GET http://localhost:8000/api/ingest-status`: scheduler running, `target_region_codes="72"`, следующий запуск `2026-05-11T05:10:38+05:00`.
- `GET http://localhost:8000/api/lots/quality`: корректная сводка по чистой базе региона `72`.
- `GET http://localhost:8000/api/lots?limit=3&sort=discount_to_baseline_desc`: API возвращает лоты с корректными `torgi_url`, `torgi_json_url`, `nspd_map_url`.
- `GET http://localhost:5173`: HTTP 200.

**TODO:**
- Если этот региональный фильтр нужно закрепить постоянно, вне текущего запущенного процесса, явно обновить `.env`: `TARGET_REGION_CODES=72`.
- Следующим шагом стоит включить продуктовый фильтр уведомлений только на релевантные земельные/ИЖС-кандидаты, чтобы бот не шумел объектами недвижимости и нерелевантными торгами при будущих live-изменениях.

---

## 2026-05-10 - НСПД deep link: selectedCard, координаты и fallback по кадастру

**Что сделано:**
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): `nspd_map_url` теперь строит best-effort deep link:
  - если есть `nspd_card_id`, `nspd_card_type`, центроид и кадастровый номер — добавляет `selectedCard`, `zoom=20`, `coordinate_x`, `coordinate_y`;
  - если card id/type ещё нет, но есть центроид — открывает НСПД-карту в точке участка, с `zoom=20` и кадастровым номером в `query`;
  - если есть только кадастровый номер — открывает НСПД-карту с кадастром в `query`.
- [backend/app/services/nspd/geometry.py](backend/app/services/nspd/geometry.py): добавлен перевод WGS84 `lat/lon` в EPSG:3857 для параметров `coordinate_x/coordinate_y` публичной карты НСПД.
- [backend/app/models.py](backend/app/models.py), [backend/app/schemas.py](backend/app/schemas.py), [frontend/src/types.ts](frontend/src/types.ts): добавлены поля `nspd_card_id`, `nspd_card_type` для сохранения идентификаторов публичной карточки НСПД.
- [backend/app/services/nspd/enrich.py](backend/app/services/nspd/enrich.py): НСПД-обогащение теперь пытается извлечь card id/type из разных возможных мест ответа (`feature.id`, `properties.*`, `properties.options.*`) и очищает их при no-match.
- [backend/alembic/versions/20260510_11_add_lot_nspd_card_fields.py](backend/alembic/versions/20260510_11_add_lot_nspd_card_fields.py): добавлена Alembic-миграция для новых NSPD card columns.
- Выполнен `python scripts/dev_sync_schema.py`: в текущую SQLite добавлены `lots.nspd_card_id`, `lots.nspd_card_type`; предупреждение по старому FK `lots.opendata_notice_id` осталось ожидаемым для SQLite.
- Для локального dev-примера `72:24:0609016:181` заполнены `nspd_card_id=291667829`, `nspd_card_type=36384` из пользовательской ссылки, чтобы карточка `lot_id=4191` сразу отдавала `selectedCard`-URL.
- Обновлены [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md), [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md): описан новый контракт НСПД-ссылки.

**Проверки:**
- `curl.exe -k` к live endpoint НСПД `/api/geoportal/...` из текущей сети вернул `403 Forbidden`, поэтому новые card id/type проверены unit-тестами и локальным backfill по пользовательскому примеру.
- `.\\.venv312\\Scripts\\python.exe -m pytest tests/test_external_lot_links.py tests/test_nspd_enrich.py tests/test_api.py tests/test_alerts_service.py`: 46 passed.
- `.\\.venv312\\Scripts\\python.exe -m pytest`: 99 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `GET http://localhost:8000/api/lots/4191`: `nspd_map_url` содержит `zoom=20`, `coordinate_x/coordinate_y` и `selectedCard=291667829,36384,72:24:0609016:181`.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.

**TODO:**
- После доступного live NSPD enrichment проверить, какие реальные поля ответа стабильно соответствуют `card_id/card_type`, и при необходимости сузить extraction candidates.
- Для уже обогащённых старых лотов прогнать `python scripts/enrich_lots_nspd.py --force --include-fresh`, когда endpoint НСПД снова доступен без 403, чтобы заполнить `nspd_card_id/type` массово.

---

## 2026-05-10 - Полный dev-рестарт backend/frontend

**Что сделано:**
- Остановлены старые процессы проекта на портах `8000` и `5173`.
- Backend поднят заново через `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`; логи пишутся в `data/logs/backend-uvicorn.out.log` и `data/logs/backend-uvicorn.err.log`.
- Frontend поднят заново через `npm run dev -- --host 0.0.0.0 --port 5173`; логи пишутся в `data/logs/frontend-vite.out.log` и `data/logs/frontend-vite.err.log`.

**Проверки:**
- `GET http://localhost:8000/health`: `{"status":"ok"}`.
- `GET http://localhost:8000/api/ingest-status`: scheduler running, `is_running=false`, следующий запуск `2026-05-11T04:24:48+05:00`, `RUN_INGEST_ON_STARTUP=false`.
- `GET http://localhost:8000/api/lots?limit=1`: API отвечает, поле `nspd_map_url` присутствует.
- `GET http://localhost:5173`: HTTP 200.

**TODO:**
- Для проверки нового Telegram-фильтра без шума сделать preview/smoke по реальному `lot_id`, а не отправлять пустые тестовые лоты в рабочий чат.

---

## 2026-05-10 - Telegram: отсечение пустых low-signal алертов

**Что сделано:**
- По пользовательскому примеру Telegram-сообщения с `Тестовый лот` подтверждён UX-дефект: алерт без кадастра, ИЖС-признака, площади, цены за сотку и baseline выглядел как реальная карточка, хотя не помогал принять решение.
- [backend/app/config.py](backend/app/config.py), [.env.example](.env.example): добавлен `TELEGRAM_ALERT_SKIP_LOW_SIGNAL=true` по умолчанию. Такие сообщения теперь не отправляются, если одновременно нет ИЖС-признака, нет кадастрового номера, нет цены за сотку и нет baseline-дисконта.
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): добавлена проверка low-signal перед отправкой Telegram; если фильтр выключить для debug, вердикт будет `недостаточно данных для оценки`, а строка `Почему попало` заменена на нейтральные `Сигналы`.
- [backend/app/services/lot_baseline.py](backend/app/services/lot_baseline.py): уточнены причины невозможности расчёта baseline. Если стартовая цена есть, но нет площади, теперь пишется `Нет площади для расчёта цены за сотку`, а не общее `Нет стартовой цены или площади`.
- [backend/tests/test_alerts_service.py](backend/tests/test_alerts_service.py): добавлены тесты на default-skip low-signal алерта и на принудительный debug-режим без старой неоднозначной формулировки.
- [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md): обновлены описание Telegram-фильтра и текущее число backend-тестов.

**Затронутые файлы:**
- backend/app/config.py
- backend/app/services/alerts/service.py
- backend/app/services/lot_baseline.py
- backend/tests/test_alerts_service.py
- .env.example
- README.md
- DEVELOPMENT_PLAN.md
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `.\\.venv312\\Scripts\\python.exe -m pytest tests/test_alerts_service.py`: 9 passed.
- `.\\.venv312\\Scripts\\python.exe -m pytest`: 95 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.

**TODO:**
- Сделать preview-команду для форматированного Telegram-алерта по реальному `lot_id`, чтобы визуально проверять сообщение без нового ingest и без тестовых пустых лотов.
- На живом потоке подобрать, оставлять ли `TELEGRAM_ALERT_SKIP_LOW_SIGNAL=true` как единственный мягкий фильтр или дополнительно включать `TELEGRAM_ALERT_ONLY_IZHS` / `TELEGRAM_ALERT_REQUIRE_CADASTRAL`.

---

## 2026-05-10 - Telegram MVP: компактная карточка и строгий baseline-фильтр

**Что сделано:**
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): Telegram-уведомление пересобрано из технической простыни в компактную MVP-карточку:
  - верхняя строка теперь сразу даёт событие и вердикт (`Новый лот: интересно, смотреть глубже`);
  - добавлена строка `ГИС: извещение ..., лот N из M` через `LotSnapshot` и multi-lot payload;
  - ключевые поля сгруппированы в рабочие строки: локация, кадастр, земля/ВРИ, ИЖС+НСПД, цена, цена за сотку/м², baseline, срок заявок, причина попадания;
  - raw JSON ГИС Торги перенесён в конец ссылок, чтобы пользователь сначала видел монитор, ГИС-страницу и НСПД-карту;
  - сохранены пояснения, что baseline пока считается по загруженным торгам, а marketplace-поиск не гарантирует карточку участка.
- [backend/app/config.py](backend/app/config.py), [.env.example](.env.example): добавлен `TELEGRAM_ALERT_REQUIRE_BASELINE_FOR_DISCOUNT`. Если включён `TELEGRAM_ALERT_MIN_DISCOUNT_TO_BASELINE` и этот флаг `true`, лоты без рассчитанного baseline-дисконта не будут попадать в Telegram.
- [backend/tests/test_alerts_service.py](backend/tests/test_alerts_service.py): обновлены ожидания нового формата и добавлен тест строгого baseline-фильтра.
- [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md), [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md): обновлены описание компактной Telegram-карточки, production-фильтров и текущее число backend-тестов.

**Затронутые файлы:**
- backend/app/services/alerts/service.py
- backend/app/config.py
- backend/tests/test_alerts_service.py
- .env.example
- README.md
- DEVELOPMENT_PLAN.md
- AGENTS.md
- docs/MVP_PRODUCT_CONTRACT.md
- WORKLOG.md

**Проверки:**
- `.\\.venv312\\Scripts\\python.exe -m pytest tests/test_alerts_service.py`: 7 passed.
- `.\\.venv312\\Scripts\\python.exe -m pytest`: 93 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.

**TODO:**
- После live-прогона на целевом потоке подобрать реальные production-фильтры: `TELEGRAM_ALERT_ONLY_IZHS`, `TELEGRAM_ALERT_REQUIRE_CADASTRAL`, `TELEGRAM_ALERT_MIN_DISCOUNT_TO_BASELINE`, `TELEGRAM_ALERT_REQUIRE_BASELINE_FOR_DISCOUNT`.
- Сделать отдельный preview/smoke для Telegram-карточки по реальному лоту из БД, чтобы перед включением бота визуально проверять формат сообщения без нового ingest.

---

## 2026-05-10 - Контракт MVP: Telegram-first, НСПД-ссылка и matching-логика агрегаторов

**Что сделано:**
- Пересобран продуктовый контракт MVP в отдельном документе [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md): зафиксированы цель Telegram-first MVP, состав Telegram-уведомления, контракт ссылок, различие между публичным извещением ГИС Торги и конкретным внутренним `notice.lots[]`, а также будущая логика поиска того же участка и рыночных аналогов на Циан/Авито/Домклик.
- Уточнён главный продуктовый тезис: MVP должен помогать за 1-3 минуты понять, стоит ли лот смотреть глубже; внешние marketplace-ссылки в текущем MVP остаются поисковыми подсказками, а не доказанным совпадением и не рыночной оценкой.
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): добавлен `nspd_map_url()` с URL `https://nspd.gov.ru/map?thematic=PKK` при наличии кадастрового номера; legacy `pkk_map_url()` оставлен `None`, чтобы не возвращать нерабочий старый PKK deep link.
- [backend/app/api.py](backend/app/api.py), [backend/app/schemas.py](backend/app/schemas.py), [frontend/src/types.ts](frontend/src/types.ts): в контракт `/api/lots` и `/api/lots/{id}` добавлено поле `nspd_map_url`.
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): Telegram-уведомление теперь добавляет ссылку `НСПД карта` при наличии кадастрового номера и поясняет, что если участок не открылся автоматически, кадастровый номер нужно вставить в поиск НСПД.
- [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx): карточка лота показывает ссылку на НСПД-карту в блоке проверки источника и пояснение про поиск по кадастровому номеру.
- Обновлены [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md): MVP-контракт, `nspd_map_url`, статус 92 backend-тестов, ссылка на новый документ и уточнение, что marketplace-интеграция пока не является автоматической оценкой.
- Быстро проверен доступ к НСПД-карте из текущей среды: `curl.exe -k -I -L https://nspd.gov.ru/map?thematic=PKK` вернул `200 OK`; без `-k` локальная TLS-цепочка по-прежнему не доверена, что совпадает с dev-флагом `NSPD_VERIFY_TLS=false`.

**Затронутые файлы:**
- docs/MVP_PRODUCT_CONTRACT.md
- backend/app/services/external_lot_links.py
- backend/app/services/alerts/service.py
- backend/app/api.py
- backend/app/schemas.py
- backend/tests/test_external_lot_links.py
- backend/tests/test_alerts_service.py
- backend/tests/test_api.py
- frontend/src/types.ts
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/utils/links.ts
- README.md
- DEVELOPMENT_PLAN.md
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `.\\.venv312\\Scripts\\python.exe -m pytest tests/test_external_lot_links.py tests/test_alerts_service.py tests/test_api.py`: 31 passed.
- `.\\.venv312\\Scripts\\python.exe -m pytest`: 92 passed.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.

**TODO:**
- На машине с российским маршрутом провести live-проверку marketplace-поисков: какие параметры реально дают полезную выдачу на Циан/Авито/Домклик и где возникает captcha/пустая выдача.
- После НСПД coverage выбрать первый источник аналогов, вероятнее Циан, и начать заполнять `MarketComparable`.
- Отдельно спроектировать `same_parcel_match` vs `market_analog`: точное совпадение по кадастру не смешивать с оценкой рынка по соседним участкам.

---

## 2026-05-09 - Дефектовка MVP: источник, multi-lot UX и честный baseline

**Что сделано:**
- Проведена дефектовка концепта “извещение vs лот”: подтверждено, что OpenData `7710568760-notice` отдаёт индекс документов (`regNum`, `documentType`, `subjectEstateCode`, `biddTypeCode`, `href`), а реальные участки для анализа лежат глубже в detail JSON по `href`, в `exportObject.structuredObject.notice.lots[]`.
- Проверены официальные OpenData-точки ГИС Торги:
  - `https://torgi.gov.ru/new/opendata/list.json` — машиночитаемый реестр наборов;
  - `https://torgi.gov.ru/new/opendata/7710568760-notice/meta.json` — список выгрузок извещений;
  - `https://torgi.gov.ru/new/opendata/7710568760-notice/structure-20240401.json` — схема индексного `listObjects`;
  - дополнительно просмотрены `masterData`, `protocol`, `contract` как следующий источник для справочников/результатов/договоров, но в этот проход они не подключались.
- Найден и исправлен дефект discovery: `INGEST_SOURCE_URL` мог указывать на HTML-карточку OpenData, но код воспринимал его как прямой `data-*.json`. Теперь прямым override считается только URL `data-*.json`; карточка обрабатывается как `card_override` и из неё извлекаются актуальные data-ссылки.
- [backend/app/api.py](backend/app/api.py), [backend/app/schemas.py](backend/app/schemas.py), [frontend/src/types.ts](frontend/src/types.ts): в API добавлены объясняющие поля `notice_reg_num`, `notice_lot_number`, `notice_lot_count`, чтобы карточка могла явно показывать “это лот N из M внутри извещения”.
- [backend/app/services/lot_baseline.py](backend/app/services/lot_baseline.py), [backend/app/api.py](backend/app/api.py): лоты со `start_price <= 0` больше не участвуют в расчёте ₽/сотка и дисконта к baseline. Это убирает ложный сигнал `100%` дисконта для нулевой стартовой цены.
- [frontend/src/components/Layout.tsx](frontend/src/components/Layout.tsx): главное меню упрощено до MVP-сценариев `Сводка / Лоты / Загрузки`; технические страницы `/notices` и `/map` остались доступными по маршрутам, но убраны из верхнего меню.
- [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx): таблица лотов теперь показывает главное действие `Открыть` карточку лота и короткую ссылку `ГИС`; JSON/marketplace-ссылки убраны из списка, чтобы не шуметь.
- [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx), [frontend/src/styles.css](frontend/src/styles.css): карточка лота получила верхнюю сводку (кадастр, площадь, цена, ₽/сотка, дисконт, срок заявок) и пояснение, что публичная ссылка ГИС Торги ведёт на извещение целиком, а монитор показывает конкретный внутренний лот.
- Обновлены [README.md](README.md) и [AGENTS.md](AGENTS.md): discovery-chain, новые API-поля, меню MVP и 91 backend test.

**Дефекты/риски по итогам проверки:**
- Публичный сайт ГИС Торги по-прежнему не даёт стабильного deep link на конкретный элемент `notice.lots[]`; правильная UX-модель — открывать внешний URL извещения и внутри нашего монитора держать точную привязку `regNum + lotNumber`.
- Для полноценного “мощного сервиса” следующим слоем нужно подключить `masterData` для расшифровки кодов, `protocol`/`contract` для итогов торгов и договоров, а также внешние аналоги рынка. Текущий baseline остаётся внутренней эвристикой по загруженным торгам.
- В текущей SQLite: `lots_total=4232`, `region72=114`, `multi_lot_rows=40`, `with_cadastral=190`, `with_area=170`, `with_price_area=123`, FK-сирот по `lots/opendata_notices/snapshots/alerts` не найдено. Исторически не все регионы догнаны multi-lot split, но будущий ingest разворачивает новые извещения автоматически.

**Затронутые файлы:**
- backend/app/services/ingest/discovery.py
- backend/app/api.py
- backend/app/schemas.py
- backend/app/services/lot_baseline.py
- backend/tests/test_ingest_discovery.py
- backend/tests/test_api.py
- frontend/src/components/Layout.tsx
- frontend/src/components/LotsTable.tsx
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/styles.css
- frontend/src/types.ts
- README.md
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `python -m pytest`: 91 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `git diff --check`: без whitespace-ошибок, только стандартные CRLF-предупреждения Git на Windows.
- Backend полностью перезапущен; `GET http://localhost:8000/health`: `{"status":"ok"}`.
- `GET /api/lots/4231`: `notice_reg_num=22000162030000000177`, `notice_lot_number=4`, `notice_lot_count=5`, `start_price_per_sotka=null`, `discount_to_baseline=null`.
- Headless Edge screenshots: `data/logs/screenshots/lot-detail-4231-final.png`, `data/logs/screenshots/lots-mobile-ready.png` — явных перекрытий и пустых экранов не обнаружено.

**TODO:**
- Сформировать отдельную модель/таблицу для `notice_lots` или нормализованных `source_notice_reg_num/source_lot_number`, чтобы не кодировать multi-lot через `source_id`.
- Подключить `masterData` для человекочитаемых названий кодов `biddTypeCode`, регионов, форм собственности и статусов.
- Добавить ingestion `protocol`/`contract`, чтобы понимать итоговую цену, победителя и факт заключения договора.
- После этого пересобрать скоринг: рынок по Циан/Авито/Домклик + протоколы/договоры + НСПД, а не только внутренний baseline.

---

## 2026-05-09 - Multi-lot извещения: разворот в отдельные Lot

**Что сделано:**
- Проверена гипотеза пользователя: в ГИС Торги OpenData `regNum` — это извещение, а настоящий список участков часто лежит глубже в detail JSON в `exportObject.structuredObject.notice.lots[]`.
- На живом примере `lot_id=4187` / `regNum=22000162030000000177` подтверждено: одно извещение содержит 5 участков; прежняя логика сохраняла одну строку `lots` и брала поля первым найденным проходом по JSON.
- [backend/app/services/ingest/service.py](backend/app/services/ingest/service.py): detail-fetch теперь разворачивает `notice.lots[]` в отдельные normalized lot records. Для совместимости первый лот многолотового извещения сохраняет `source_id=regNum`, следующие получают `source_id=regNum:lot:<lotNumber>`.
- `noticeCancel` / `noticeStop` / `noticeResumption` / `noticeAnnulment` теперь обновляют все строки одного извещения: `regNum` и `regNum:lot:%`.
- [backend/app/services/ingest/detail_parser.py](backend/app/services/ingest/detail_parser.py): категория земли теперь предпочитает `characteristics[code=PurposeZU]` над общей имущественной категорией `category`.
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): публичная ссылка ГИС Торги теперь корректно извлекает номер извещения из multi-lot `source_id` вида `regNum:lot:<lotNumber>`, поэтому список `/api/lots` больше не падает на JSON-ссылку для таких строк.
- [backend/tests/test_ingest_service.py](backend/tests/test_ingest_service.py): добавлен тест, что одно OpenData-извещение с двумя `lots[]` создаёт две строки в `lots`.
- [backend/tests/test_detail_parser.py](backend/tests/test_detail_parser.py): добавлен тест на приоритет `PurposeZU` для категории земель.
- [backend/tests/test_external_lot_links.py](backend/tests/test_external_lot_links.py): добавлен регрессионный тест для `regNum:lot:<lotNumber>`.
- Локально выполнен безопасный догон существующей SQLite по Тюменской области с отключёнными Telegram-алертами и `NSPD_ENABLED=false`: 31 извещение проверено, 71 фактический лот развернут/обновлён, строк региона 72 стало `114` вместо `74`.
- Для проблемного извещения `22000162030000000177` теперь есть 5 строк:
  - `22000162030000000177` — участок 1;
  - `22000162030000000177:lot:2` — участок 2;
  - `22000162030000000177:lot:3` — участок 3;
  - `22000162030000000177:lot:4` — участок с кадастром `72:22:0611001:180`;
  - `22000162030000000177:lot:5` — участок с кадастром `72:22:0611001:190`.
- Обновлён [AGENTS.md](AGENTS.md): текущий статус ingest теперь описывает multi-lot split и 89 backend tests.

**Затронутые файлы:**
- backend/app/services/ingest/service.py
- backend/app/services/ingest/detail_parser.py
- backend/app/services/external_lot_links.py
- backend/tests/test_ingest_service.py
- backend/tests/test_detail_parser.py
- backend/tests/test_external_lot_links.py
- AGENTS.md
- WORKLOG.md
- data/app.db (локальная dev-БД, gitignored)

**Проверки:**
- `python -m pytest tests/test_ingest_service.py::test_run_ingest_splits_multilot_notice_detail ...`: прошло.
- `python -m pytest tests/test_external_lot_links.py`: 12 passed.
- `python -m pytest`: 89 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- Backend полностью перезапущен; `GET http://localhost:8000/health`: `{"status":"ok"}`.
- API после догона показывает новые строки по `source_id like '22000162030000000177%'`; список `/api/lots` и карточка `/api/lots/4231` отдают `torgi_url=https://torgi.gov.ru/new/public/notices/view/22000162030000000177` и отдельный `torgi_json_url` на raw JSON.

**Известные проблемы / TODO:**
- Ссылка ГИС Торги остаётся ссылкой на извещение, потому что публичный сайт ГИС не даёт стабильный deep link на конкретный элемент `notice.lots[]`. Внутри нашего монитора теперь строка соответствует конкретному участку, а внешний URL ведёт на родительское извещение.
- Для исторических регионов вне Тюменской области multi-lot догон не выполнялся; будущий ingest будет разворачивать такие извещения автоматически.

---

## 2026-05-09 - Hotfix: рабочий URL карточки ГИС Торги

**Что сделано:**
- По сообщению пользователя перепроверена ссылка ГИС Торги в браузерном режиме через headless Edge: `/new/public/op/view/{uuid}` открывает SPA, но не рендерит карточку извещения.
- Подтверждён рабочий официальный маршрут из detail JSON: `/new/public/notices/view/{regNum}`; для `lot_id=4187` страница `https://torgi.gov.ru/new/public/notices/view/22000162030000000177` рендерит карточку `Извещение № 22000162030000000177`.
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): `torgi_url` снова строится по реестровому номеру; если в detail payload есть официальный `commonInfo.href`, он используется приоритетно. UUID из имени JSON больше не используется как id публичной страницы.
- [backend/tests/test_external_lot_links.py](backend/tests/test_external_lot_links.py), [backend/tests/test_api.py](backend/tests/test_api.py): ожидания обновлены на `/new/public/notices/view/{regNum}`.
- Обновлены [README.md](README.md) и [AGENTS.md](AGENTS.md), чтобы текущий контракт ссылок был описан правильно.
- Backend принудительно перезапущен; текущий API для `lot_id=4187` отдаёт `torgi_url=https://torgi.gov.ru/new/public/notices/view/22000162030000000177`.

**Затронутые файлы:**
- backend/app/services/external_lot_links.py
- backend/tests/test_external_lot_links.py
- backend/tests/test_api.py
- README.md
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `python -m pytest tests/test_external_lot_links.py tests/test_api.py::test_lot_detail_returns_notice_payload_when_linked tests/test_alerts_service.py::test_notify_lot_event_sends_html_with_links`: 13 passed.
- `python -m pytest`: 86 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `GET http://localhost:8000/health`: `{"status":"ok"}`.
- `GET http://localhost:8000/api/lots/4187`: `torgi_url` указывает на `/new/public/notices/view/22000162030000000177`, `pkk_map_url=null`, маркетплейс-ссылки пустые.

**Известные проблемы / TODO:**
- Для ГИС Торги обычная HTTP-проверка недостаточна: SPA отдаёт `200` почти на любой маршрут. Для deep links надо проверять DOM/рендер или доверять официальному `commonInfo.href` из detail JSON.

---

## 2026-05-09 - Исправление внешних ссылок лота

**Что сделано:**
- Подтверждена проблема пользователя: старый URL ГИС Торги строился как `/new/public/notices/view/{regNum}` и открывал SPA-shell без полезной карточки; ПКК `pkk.rosreestr.ru` больше не даёт надёжный результат; поисковые ссылки Домклик/Авито/Циан часто ведут в капчу/429/401 или пустую выдачу.
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): публичная ссылка ГИС Торги теперь строится как `/new/public/op/view/{uuid}`, где UUID берётся из `notice_payload.href`, `notice_detail_url` или `source_url` вида `notice_<regNum>_<uuid>.json`; если UUID не найден, `torgi_url` честно падает обратно на JSON извещения.
- Legacy `pkk_map_url` оставлен в API для совместимости, но теперь возвращает `null`; фронт больше не достраивает ПКК fallback.
- [backend/app/config.py](backend/app/config.py), [.env.example](.env.example): `INCLUDE_MARKETPLACE_SEARCH_URLS` выключен по умолчанию; маркетплейс-ссылки остаются только как явный best-effort режим.
- [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx), [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx): убраны ПКК-ссылки из списка и карточки лота.
- Проверено на живом `lot_id=4187`: `torgi_url=https://torgi.gov.ru/new/public/op/view/702bf5e5-c1fe-43d9-b713-b52e485c6eea`, `torgi_json_url` остаётся прямым JSON, `pkk_map_url=null`.

**Затронутые файлы:**
- backend/app/services/external_lot_links.py
- backend/app/config.py
- backend/app/schemas.py
- backend/app/services/alerts/service.py
- backend/tests/test_external_lot_links.py
- backend/tests/test_api.py
- backend/tests/test_alerts_service.py
- frontend/src/components/LotsTable.tsx
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/types.ts
- frontend/src/utils/links.ts
- .env.example, README.md, AGENTS.md, WORKLOG.md

**Проверки:**
- `python -m pytest tests/test_external_lot_links.py tests/test_api.py::test_lot_detail_returns_notice_payload_when_linked tests/test_alerts_service.py::test_notify_lot_event_sends_html_with_links`: 12 passed.
- `python -m pytest`: 85 passed.
- `npx.cmd tsc --noEmit`: прошло.
- `npm.cmd run test`: 3 passed.
- `npm.cmd run build`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `git diff --check`: без whitespace-ошибок, только предупреждения Git о будущей замене LF на CRLF.

**Известные проблемы / TODO:**
- Запущенный backend нужно перезапустить, чтобы он подхватил новый default `INCLUDE_MARKETPLACE_SEARCH_URLS=false` и исправленный генератор ссылок.
- Надёжный deep link в НСПД-карту пока не добавлен: лучше показывать кадастровый номер и наши координаты/НСПД-данные, чем снова давать ссылку, которая выглядит точной, но не приводит к участку.

---

## 2026-05-09 - Split tunnel: live ГИС Торги, Telegram alerts, НСПД enrichment

**Что сделано:**
- После настройки split tunneling проверены маршруты:
  - `https://torgi.gov.ru` стал доступен;
  - `https://api.telegram.org` доступен из Python-клиента, Telegram smoke вернул `Sent.`;
  - `https://nspd.gov.ru` доступен, но в текущем split-tunnel режиме отдаёт TLS chain с self-signed certificate.
- Запущен live fetch свежего OpenData:
  - `python scripts/fetch_latest_opendata.py`;
  - скачаны `data-20260508T0000-20260509T0000-structure-20240401.json`, `structure-20240401.json`, `latest_opendata_meta.json`.
- Запущен точечный live-ingest по Тюменской области за свежий файл:
  - `INGEST_SOURCE_URL=https://torgi.gov.ru/new/opendata/7710568760-notice/data-20260508T0000-20260509T0000-structure-20240401.json`;
  - `INGEST_STRUCTURE_URL=https://torgi.gov.ru/new/opendata/7710568760-notice/structure-20240401.json`;
  - `TARGET_REGION_CODES=72`;
  - `INGEST_DETAIL_MAX_PER_RUN=80`;
  - `TELEGRAM_ALERT_ONLY_IZHS=true`;
  - `python scripts/run_backfill_ingest.py --from-date 2026-05-08 --to-date 2026-05-08`.
- Результат ingest: `fetched_count=1408`, `upserted_count=19`, `changed_count=19`, `processed_files=1`, `failed_files=0`; новый `IngestRun id=19`, `status=success`.
- Telegram alert pipeline сработал: появились свежие `AlertEvent` по ИЖС-кандидатам (`lot_id` 4174, 4175, 4177, 4183, 4187).
- Качество данных по региону 72 после ingest:
  - `total=74`;
  - `izhs_candidates=6`;
  - `with_cadastral=17`;
  - `with_area=19`;
  - `with_start_price=21`;
  - `with_baseline=19`;
  - `with_positive_discount=8`.
- [backend/app/config.py](backend/app/config.py), [backend/app/services/nspd/client.py](backend/app/services/nspd/client.py): добавлен `NSPD_VERIFY_TLS` (`true` по умолчанию; локально можно `false` при self-signed chain).
- [backend/scripts/enrich_lots_nspd.py](backend/scripts/enrich_lots_nspd.py): добавлен фильтр `--region`.
- Проверен и применён ручной НСПД-догон по Тюменской области:
  - dry-run: `--limit 5 --force --dry-run --include-fresh` дал `matched=5/5`;
  - apply: `NSPD_VERIFY_TLS=false python scripts/enrich_lots_nspd.py --region 72 --limit 20 --force`;
  - результат: `selected=17`, `checked=17`, `matched=16`, `failed=1`;
  - в БД: 16 лотов региона 72 получили `nspd_enriched_at`, 7 получили `nspd_specified_area_sqm`.
- Обновлена документация: [.env.example](.env.example), [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md).

**Затронутые файлы:**
- backend/app/config.py
- backend/app/services/nspd/client.py
- backend/scripts/enrich_lots_nspd.py
- backend/tests/test_nspd_client.py
- .env.example, README.md, DEVELOPMENT_PLAN.md, AGENTS.md, WORKLOG.md
- data/raw/latest_opendata_meta.json, data/raw/data-20260508T0000-20260509T0000-structure-20240401.json, data/raw/structure-20240401.json, data/raw/nspd_enrich_report.json (gitignored)

**Проверки:**
- `python scripts/fetch_latest_opendata.py`: успешно.
- `python scripts/send_telegram_test.py --text "GIS Torgi Monitor split tunnel smoke"`: `Sent.`
- `python scripts/run_backfill_ingest.py --from-date 2026-05-08 --to-date 2026-05-08`: `processed_files=1`, `failed_files=0`.
- `python scripts/enrich_lots_nspd.py --region 72 --limit 20 --force` с `NSPD_VERIFY_TLS=false`: `matched=16`, `failed=1`.
- `backend/.venv312/Scripts/python.exe -m pytest`: 85 passed.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 3 passed.
- `npm.cmd run build` в `frontend/`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `git diff --check`: без whitespace-ошибок, только предупреждения Git о будущей замене LF на CRLF.

**Известные проблемы / TODO:**
- НСПД в текущем split-tunnel режиме требует `NSPD_VERIFY_TLS=false`; в production надо держать `true`.
- Один кадастр НСПД вернул `404 Not Found`: `72:15:0314001:00001`.
- У отдельных лотов площадь из извещения и НСПД сильно расходится (пример: `72:22:0611001:180`: извещение 855 м², НСПД 586210 м²); по умолчанию `NSPD_MERGE_AREA_POLICY=notice_only`, поэтому основная площадь не перетирается.
- В `.env` не задан `APP_PUBLIC_BASE_URL`, поэтому ссылка «Монитор» в Telegram не формируется для внешнего открытия.

**Следующее:**
- Обновить `.env` под рабочий MVP-режим: `TARGET_REGION_CODES=72`, `TELEGRAM_ALERT_ONLY_IZHS=true`, при необходимости `NSPD_ENABLED=true`, `NSPD_VERIFY_TLS=false`, `APP_PUBLIC_BASE_URL=...`.
- Добавить в Telegram-вердикт явное предупреждение о расхождении площади notice vs НСПД.
- Начать интеграцию Циан как источника реальных аналогов или хотя бы сохранить первые результаты разведки в `market_comparables`.

---

## 2026-05-09 - MVP bot: вердикт в Telegram и ручной НСПД-догон

**Что сделано:**
- Проведена диагностика текущего dev-стенда: backend `8000` и frontend `5173` отвечают, в БД есть лоты, Telegram Bot API доступен, `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` заданы.
- Проверка Telegram smoke прошла: `python scripts/send_telegram_test.py --text "GIS Torgi Monitor MVP smoke: Telegram delivery works."` вернул `Sent.`.
- Подтвержден сетевой блокер: при текущем VPN `https://torgi.gov.ru` и `https://nspd.gov.ru` уходят в timeout, при этом `https://api.telegram.org` и `https://www.cian.ru` доступны.
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): Telegram-сообщение превращено из простого лога в первичный разбор лота:
  - человекочитаемый заголовок события;
  - строка `Вердикт`;
  - причины попадания в алерт;
  - кадастр, НСПД-статус, ВРИ, категория земли, муниципалитет/населённый пункт;
  - стартовая цена, цена за сотку/м², baseline, дисконт, confidence и пояснение;
  - явная сноска, что baseline по торгам ещё не является рыночной оценкой Циан.
- Marketplace-ссылки в Telegram сокращены: если есть кадастровый номер, отправляются поиски Домклик/Авито/Циан только по кадастру; расширенный поиск по адресу используется только когда кадастра нет.
- Добавлен [backend/scripts/enrich_lots_nspd.py](backend/scripts/enrich_lots_nspd.py): ручное обогащение уже существующих лотов через НСПД по кадастровому номеру (`--limit`, `--dry-run`, `--force`, отчёт в `data/raw/nspd_enrich_report.json`).
- Документация обновлена: [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md).

**Затронутые файлы:**
- backend/app/services/alerts/service.py
- backend/scripts/enrich_lots_nspd.py
- backend/tests/test_alerts_service.py
- README.md, DEVELOPMENT_PLAN.md, AGENTS.md, WORKLOG.md

**Проверки:**
- `python scripts/send_telegram_test.py --text ...`: `Sent.`
- `python scripts/enrich_lots_nspd.py --help`: CLI корректно показывает параметры.
- `backend/.venv312/Scripts/python.exe -m pytest`: 84 passed.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 3 passed.
- `npm.cmd run build` в `frontend/`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `git diff --check`: без whitespace-ошибок, только предупреждения Git о будущей замене LF на CRLF.

**Известные проблемы / TODO:**
- Live-ingest ГИС Торги и НСПД-обогащение не проверить при текущем VPN: `torgi.gov.ru` и `nspd.gov.ru` недоступны с этой машины.
- Циан как источник реальных аналогов ещё не интегрирован; сейчас в Telegram/API есть поисковые ссылки и внутренняя baseline-оценка.

**Следующее:**
- Переключить сеть: split tunneling для `torgi.gov.ru`/`nspd.gov.ru` или временно VPN-off.
- После доступа к российским сайтам выполнить: connectivity check → малый ingest → `enrich_lots_nspd.py --limit 20 --force` → проверить реальный smart alert.

---

## 2026-05-09 - План доведения MVP к Telegram-боту мониторинга

**Что сделано:**
- Зафиксирована целевая формулировка MVP: Telegram-бот, который на новых/изменённых лотах ГИС Торги присылает пользователю полезный первичный разбор земельного участка.
- Уточнена бизнес-задача: сократить ручной поиск и первичный анализ, быстро находить участки с потенциальным дисконтом и принимать решение, стоит ли смотреть глубже и участвовать в аукционе.
- Зафиксированы источники данных MVP: ГИС Торги как основной реестр, НСПД как кадастрово-пространственная проверка, Циан как первый источник рыночных аналогов; Авито/Домклик — последующие расширения.
- Уточнено сетевое ограничение рабочей машины: при включённом VPN доступны Telegram/нейросети, но недоступны российские сайты; для live-ingest Торгов/НСПД/Циан нужен VPN-off, split tunneling, прокси или отдельный хост.

**Затронутые файлы:**
- WORKLOG.md

**Проверки:**
- Не запускались: запись плановая, код не менялся.

**Известные проблемы / TODO:**
- Нужно выбрать рабочую сетевую схему для одновременного доступа к российским источникам и Telegram Bot API.
- Реальная рыночная оценка по Циан ещё не реализована; сейчас есть внутренний baseline по торгам и поисковые ссылки.

**Следующее:**
- Реализовать/проверить минимальный рабочий поток: ingest ГИС Торги → извлечение кадастра → НСПД enrichment → baseline/аналог → smart Telegram alert.

---

## 2026-05-09 - MVP polish: проверки, Telegram proxy, чистое рабочее дерево

**Что сделано:**
- Прочитан свежий `WORKLOG.md`, выделены ближайшие MVP-блокеры: окружение frontend-проверок и live-доставка Telegram при недоступном маршруте к `api.telegram.org`.
- Восстановлены frontend dev-зависимости через `npm install`, после чего `npx tsc --noEmit` и vitest снова проходят локально.
- [backend/app/services/alerts/telegram.py](backend/app/services/alerts/telegram.py), [backend/app/config.py](backend/app/config.py): добавлены `TELEGRAM_PROXY_URL` и `TELEGRAM_TIMEOUT_SECONDS`; отправка в Telegram теперь может идти через HTTP(S)-прокси без правки кода.
- [backend/scripts/send_telegram_test.py](backend/scripts/send_telegram_test.py): добавлен разовый флаг `--proxy-url` для smoke-проверки через локальный прокси.
- [.env.example](.env.example), [README.md](README.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md): описаны новые Telegram-настройки и MVP-чеклист для push-алертов.
- [.gitignore](.gitignore): добавлен ignore для версионированных локальных venv-папок (`.venv*/`, `backend/.venv*/`), чтобы `backend/.venv312/` не шумел в статусе.
- Запущен [backend/scripts/dev_sync_schema.py](backend/scripts/dev_sync_schema.py); локальная SQLite содержит таблицу `market_comparables`.

**Затронутые файлы:**
- backend/app/{config.py}
- backend/app/services/alerts/telegram.py
- backend/scripts/send_telegram_test.py
- backend/tests/test_telegram.py
- .env.example, .gitignore, README.md, DEVELOPMENT_PLAN.md, AGENTS.md, WORKLOG.md

**Проверки:**
- `backend/.venv312/Scripts/python.exe -m pytest`: 83 passed.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 3 passed.
- `npm.cmd run build` в `frontend/`: прошло, осталось известное предупреждение Vite о крупном lazy chunk `TradesMap`.
- `python scripts/dev_sync_schema.py`: `dev schema sync complete`; осталось существующее предупреждение о FK `lots(opendata_notice_id)` в SQLite.
- `git diff --check`: без whitespace-ошибок, только предупреждения Git о будущей замене LF на CRLF.
- `python scripts/send_telegram_test.py --help`: показывает новый `--proxy-url`.

**Известные проблемы / TODO:**
- Live Telegram smoke не повторялся без прокси: в `.env` сейчас не задан `TELEGRAM_PROXY_URL`, а предыдущий прогон упирался в `ConnectTimeout` к `api.telegram.org`.
- Реальные рыночные аналоги пока не собираются: есть таблица `market_comparables` и заглушка Циан до live-разведки источников.

**Следующее:**
- На машине с доступом к Bot API задать `TELEGRAM_PROXY_URL` или выполнить `python scripts/send_telegram_test.py --proxy-url http://127.0.0.1:7890`.
- Для demo-MVP запустить backend/frontend, затем либо `load_demo_tyumen_data.py --reset`, либо ручной ingest на хосте с доступом к `torgi.gov.ru`.

---

## 2026-05-09 - Локальный запуск SPA + проверка Telegram (smoke)

**Что сделано:**
- Пользователь настроил бота и `TELEGRAM_*` в корневом `.env`.
- Backend (uvicorn) уже слушал порт 8000; поднят dev-сервер фронта: `npm run dev` в `frontend/` — Vite на http://localhost:5173/ (и сетевые адреса хоста).
- Запуск smoke: `python scripts/send_telegram_test.py` из `backend/` с текстом проверки доставки.

**Проверки:**
- `GET http://127.0.0.1:8000/health` — ок (ранее в сессии).
- `send_telegram_test.py` — **неуспех**: `httpx.ConnectTimeout` при подключении к `https://api.telegram.org` (сеть/маршрут до Bot API с машины разработчика; токен и chat_id скрипт принял).

**Затронутые файлы:**
- код не менялся; только операционный прогон.

**Следующее:** с рабочего хоста с доступом к `api.telegram.org` (VPN/другой канал) повторить `send_telegram_test.py`; при необходимости — прокси для httpx в [backend/app/services/alerts/telegram.py](backend/app/services/alerts/telegram.py).

---

## 2026-05-09 - MVP Telegram: smart-фильтры, НСПД merge, каркас рыночных аналогов

**Что сделано:**
- [backend/app/config.py](backend/app/config.py), [.env.example](.env.example): `TELEGRAM_ALERTS_ENABLED`, `TELEGRAM_ALERT_REQUIRE_CADASTRAL`, `TELEGRAM_ALERT_MIN_DISCOUNT_TO_BASELINE`; `NSPD_MERGE_AREA_POLICY`, `NSPD_MERGE_ADDRESS_POLICY` (`notice_only` | `nspd_when_notice_missing` | `prefer_nspd`).
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): порог по `discount_to_baseline` (лоты без baseline не отсекаются), мастер-выключатель и требование кадастра до дедупликации `AlertEvent`.
- [backend/app/services/nspd/enrich.py](backend/app/services/nspd/enrich.py): `merge_nspd_into_notice_fields` после успешного match по geoportal.
- [backend/app/models.py](backend/app/models.py), Alembic [backend/alembic/versions/20260509_10_add_market_comparables.py](backend/alembic/versions/20260509_10_add_market_comparables.py): таблица `market_comparables`; заглушка [backend/app/services/market/cian.py](backend/app/services/market/cian.py).
- Документация: [README.md](README.md) (production checklist, парсер), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md).
- Тесты: [backend/tests/test_alerts_service.py](backend/tests/test_alerts_service.py), [backend/tests/test_nspd_enrich.py](backend/tests/test_nspd_enrich.py).

**Проверки:**
- `python -m pytest` в `backend/`: 82 passed.
- `npx tsc --noEmit` в `frontend/`: ошибки отсутствующих типов vitest/testing-library в тестах (предсуществующие, фронт не менялся).

**Следующее:** заполнение `market_comparables` после разведки Циан (DEVELOPMENT_PLAN §0.E); при желании UI источника полей notice vs НСПД на карточке лота.

---

## 2026-05-09 - Telegram-алерты: ссылки Торги/маркетплейсы, устойчивость отправки

**Что сделано:**
- [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): вторая ссылка `torgi_notice_json_link_when_distinct`; пары URL Домклик/Авито/Циан — расширенный запрос и только кадастр; настраиваемые шаблоны `DOMCLICK_SEARCH_TEMPLATE`, `AVITO_LAND_SEARCH_TEMPLATE`, `CIAN_LAND_SEARCH_TEMPLATE`.
- [backend/app/config.py](backend/app/config.py), [.env.example](.env.example): `TELEGRAM_DISABLE_WEB_PAGE_PREVIEW`, `TELEGRAM_MAX_MESSAGE_LENGTH`, `TELEGRAM_SEND_MAX_RETRIES`.
- [backend/app/services/alerts/telegram.py](backend/app/services/alerts/telegram.py): обрезка текста, retry при HTTP 429.
- [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py): HTML-алерт с двумя ссылками ГИС Торги при необходимости, маркетплейки с подписями и дедупликацией одинаковых URL.
- API [backend/app/schemas.py](backend/app/schemas.py), [backend/app/api.py](backend/app/api.py): поля `torgi_json_url`, `*_cadastral`, `cian_*`.
- Скрипт проверки доставки [backend/scripts/send_telegram_test.py](backend/scripts/send_telegram_test.py).
- Документация: [README.md](README.md) (раздел Telegram), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) (шаблоны агрегаторов), [AGENTS.md](AGENTS.md).
- Фронт: [frontend/src/types.ts](frontend/src/types.ts), [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx), [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx).

**Проверки:**
- `python -m pytest`: 74 passed.
- `npx tsc --noEmit`: ок.

**Следующее:** при смене URL площадок — правка шаблонов в `.env`; smart-алерты по порогу discount/score (roadmap).

---

## 2026-05-09 - НСПД: поля в БД, обогащение при ingest, UI карточки

**Что сделано:**
- Модель [backend/app/models.py](backend/app/models.py): `nspd_specified_area_sqm`, `nspd_readable_address`, `nspd_cost_value`, `nspd_centroid_latitude/longitude`, `nspd_enriched_at`.
- Alembic [backend/alembic/versions/20260509_09_add_lot_nspd_fields.py](backend/alembic/versions/20260509_09_add_lot_nspd_fields.py); утилита геометрии [backend/app/services/nspd/geometry.py](backend/app/services/nspd/geometry.py).
- [backend/app/services/nspd/enrich.py](backend/app/services/nspd/enrich.py): разбор Feature, `maybe_enrich_lot_nspd_async` (HTTP в `asyncio.to_thread`, без мутации ORM в воркере).
- [backend/app/services/ingest/service.py](backend/app/services/ingest/service.py): после commit upsert лота — NSPD при `NSPD_ENABLED`, бюджет `nspd_max_per_run`, пропуск при свежем `nspd_enriched_at` (`nspd_refresh_after_days`).
- API [backend/app/schemas.py](backend/app/schemas.py), [backend/app/api.py](backend/app/api.py): поля в `LotDetail`; фронт [frontend/src/types.ts](frontend/src/types.ts), [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx).
- Тесты [backend/tests/test_nspd_enrich.py](backend/tests/test_nspd_enrich.py); конфиг [.env.example](.env.example) (`NSPD_MAX_PER_RUN`, `NSPD_REFRESH_AFTER_DAYS`); [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md).

**Проверки:**
- `python scripts/dev_sync_schema.py`: добавлены 6 колонок `lots.nspd_*` и индекс `ix_lots_nspd_enriched_at`.
- `python -m pytest`: 70 passed.
- `npx tsc --noEmit`: ок.

**Следующее:**
- Политика слияния НСПД vs извещение (приоритет полей); при необходимости карта по `nspd_centroid_*`.

---

## 2026-05-09 - Baseline в отдельном модуле, каркас клиента НСПД

**Что сделано:**
- Вынесен расчёт baseline и derived prices в [backend/app/services/lot_baseline.py](backend/app/services/lot_baseline.py); [backend/app/api.py](backend/app/api.py) и [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py) используют его без циклического импорта `alerts` → `api`.
- Добавлен опциональный клиент НСПД: [backend/app/services/nspd/client.py](backend/app/services/nspd/client.py), настройки `NSPD_*` в [backend/app/config.py](backend/app/config.py) и [.env.example](.env.example); по умолчанию `nspd_enabled=false`, сетевых вызовов из ingest нет.
- Тесты [backend/tests/test_nspd_client.py](backend/tests/test_nspd_client.py).
- Обновлены [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) (приоритеты, блок раздела 3), [AGENTS.md](AGENTS.md).

**Затронутые файлы:**
- backend/app/{api.py,config.py}
- backend/app/services/{lot_baseline.py,alerts/service.py,nspd/__init__.py,nspd/client.py}
- backend/tests/test_nspd_client.py
- .env.example, DEVELOPMENT_PLAN.md, AGENTS.md, WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: ожидается полный зелёный прогон.

**Следующее:**
- Подключить НСПД к enrich после появления модели кеша/полей в `Lot`; включить `NSPD_ENABLED` только на машине с доступом к `nspd.gov.ru`.

---

## 2026-05-09 - MVP: время и ссылки у лотов, Telegram, внешние карты

**Что сделано:**
- Добавлен [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py): URL страницы извещения на `torgi.gov.ru` (`/new/public/notices/view/{regNum}`) при наличии номера в `notice_payload` или в `source_id`, иначе JSON `href`; ПКК Росреестра; опционально поиск Домклик/Авито по строке из кадастра, адреса, муниципалитета, региона.
- В [backend/app/config.py](backend/app/config.py) и [.env.example](.env.example): `APP_PUBLIC_BASE_URL`, `INCLUDE_MARKETPLACE_SEARCH_URLS`.
- Расширены [backend/app/schemas.py](backend/app/schemas.py) и [backend/app/api.py](backend/app/api.py): поля ссылок в списке и детале лота; для деталя `torgi_url` учитывает `notice_payload`.
- Telegram: [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py) формирует HTML с baseline, полями лота и ссылками; [backend/app/services/alerts/telegram.py](backend/app/services/alerts/telegram.py) поддерживает `parse_mode` и `disable_web_page_preview`.
- Фронт: [frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx) — даты начала/окончания со временем, колонка ссылок; [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx) — секция «Ссылки» и сноска про маркетплейсы; [frontend/src/utils/links.ts](frontend/src/utils/links.ts); типы в [frontend/src/types.ts](frontend/src/types.ts).
- Документы: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md); тесты [backend/tests/test_external_lot_links.py](backend/tests/test_external_lot_links.py), [backend/tests/test_alerts_service.py](backend/tests/test_alerts_service.py), расширен [backend/tests/test_api.py](backend/tests/test_api.py).

**Затронутые файлы:**
- backend/app/{config.py,api.py,schemas.py}
- backend/app/services/{external_lot_links.py,alerts/service.py,alerts/telegram.py}
- backend/tests/{test_external_lot_links.py,test_alerts_service.py,test_api.py}
- frontend/src/{types.ts,components/LotsTable.tsx,pages/LotDetailPage.tsx,utils/links.ts,styles.css}
- .env.example, DEVELOPMENT_PLAN.md, AGENTS.md, WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 62 passed.
- `npx tsc --noEmit` в `frontend/`: ок.
- `npm run test` в `frontend/`: 3 passed.

**Известные проблемы / TODO:**
- Ссылки на Домклик/Авито остаются эвристическим поиском; привязка «цены по району» к кадастру без API источника не делалась.

**Следующее:**
- НСПД и разведка маркетплейсов по [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md); настройка реального Telegram и `APP_PUBLIC_BASE_URL` в окружении.

---

## 2026-05-08 - Сортировка извещений и выравнивание фильтров

**Что сделано:**
- На странице `/notices` выровнены фильтры: поле `Реестровый номер` теперь имеет такую же подпись и вертикальное выравнивание, как `Тип документа` и `Вид торгов`.
- Добавлена серверная сортировка извещений через параметр `sort`:
  - `publish_date_desc` / `publish_date_asc`;
  - `reg_num_asc` / `reg_num_desc`;
  - `document_type_asc` / `document_type_desc`;
  - `bidd_type_code_asc` / `bidd_type_code_desc`.
- Заголовки таблицы `/notices` стали кликабельными для сортировки по реестровому номеру, типу документа, виду торгов и дате публикации; повторный клик меняет направление.
- Сортировка сделана на backend, чтобы сортировать весь набор данных, а не только текущие 50 строк страницы.
- Для стабильной пагинации backend всегда добавляет вторичную сортировку по `id`.
- Добавлены составные индексы `opendata_notices(..., id)` для сортируемых колонок:
  - `ix_opendata_notices_publish_date_id`;
  - `ix_opendata_notices_reg_num_id`;
  - `ix_opendata_notices_document_type_id`;
  - `ix_opendata_notices_bidd_type_code_id`.
- Добавлена Alembic-ревизия `20260508_08_add_opendata_notice_sort_indexes.py`.
- Запущен `python scripts/dev_sync_schema.py`, существующая dev SQLite получила новые индексы.
- Обновлены README/AGENTS с новым контрактом сортировки `/api/opendata-notices`.

**Затронутые файлы:**
- backend/app/api.py
- backend/app/models.py
- backend/alembic/versions/20260508_08_add_opendata_notice_sort_indexes.py
- backend/tests/test_api.py
- frontend/src/api.ts
- frontend/src/types.ts
- frontend/src/pages/TradesPage.tsx
- frontend/src/pages/TradesPage.test.tsx
- frontend/src/components/TradesTable.tsx
- frontend/src/styles.css
- README.md
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `python scripts/dev_sync_schema.py` в `backend/`: созданы 4 новых индекса.
- `$env:PYTHONPATH='.'; python -m pytest` в `backend/`: 55 passed.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 3 passed.
- `npm.cmd run build` в `frontend/`: прошло; остаётся известное предупреждение Vite о крупном lazy chunk карты MapLibre.
- `GET http://localhost:8000/api/opendata-notices?sort=reg_num_asc&limit=3`: 200 OK.
- `EXPLAIN QUERY PLAN` в SQLite показал использование новых индексов для сортировок `publish_date`, `reg_num`, `document_type`, `bidd_type_code`.
- В in-app browser открыта `/notices`: фильтры на узком экране складываются корректно, клик по `Реестровый номер` переключил серверную сортировку и показал ожидаемую первую строку.

**Известные проблемы / TODO:**
- Колонка `Ссылка` не сортируется намеренно: сортировка по URL не несёт практической пользы для пользователя.

---

## 2026-05-08 - Повторная очистка данных перед проверкой ingest всех регионов

**Что сделано:**
- Остановлены локальные процессы backend/frontend, запущенные из этой копии проекта.
- Удалены восстановимые локальные данные:
  - `data/app.db`;
  - `data/migration_check.db` при наличии;
  - всё содержимое `data/raw/`.
- Директория `data/raw/` создана заново пустой.
- Backend и frontend запущены заново; backend создал новую пустую SQLite-базу через `create_all()`.

**Затронутые файлы:**
- WORKLOG.md
- data/app.db (удалён и затем создан заново пустым при старте backend; gitignored)
- data/raw/* (удалено; gitignored)

**Проверки:**
- `GET http://localhost:8000/health`: 200 OK.
- `GET http://localhost:8000/api/lots?limit=1`: 200 OK, ответ `{"items":[],"total":0,"limit":1,"offset":0}`.
- `GET http://localhost:8000/api/ingest-runs?limit=5`: 200 OK, ответ `[]`.
- `GET http://localhost:8000/api/ingest-status`: 200 OK, `target_region_codes` пустой, значит ingest не ограничен 72 регионом.
- `GET http://localhost:5173`: 200 OK.
- `data/raw/`: пустая директория.

**Известные проблемы / TODO:**
- Данные отсутствуют намеренно; следующий ручной ingest из `/ingest` должен проверить загрузку с чистого листа по всем регионам РФ.

**Следующее:**
- Запустить загрузку вручную на `/ingest` и посмотреть число полученных/сохранённых лотов и возможные ошибки источника.

---

## 2026-05-08 - Ingest всех регионов РФ по умолчанию

**Что сделано:**
- Изменён дефолт `target_region_codes` в backend-конфиге: пустая строка теперь означает отсутствие регионального фильтра, ingest сохраняет все регионы РФ.
- Обновлён `.env.example`: `TARGET_REGION_CODES=` оставлен пустым, комментарии поясняют, что коды через запятую можно задать при необходимости сузить ingest.
- Со страницы `/ingest` убрана карточка `Фокус`, потому что региональный фокус больше не используется в обычном режиме.
- Обновлены `README.md` и `AGENTS.md`: описано текущее поведение `TARGET_REGION_CODES` и то, что пустое значение означает все регионы.

**Затронутые файлы:**
- backend/app/config.py
- frontend/src/pages/IngestRunsPage.tsx
- .env.example
- README.md
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло; остаётся известное предупреждение Vite о крупном lazy chunk карты MapLibre.
- `$env:PYTHONPATH='.'; python -m pytest` в `backend/`: 55 passed.
- `GET http://localhost:8000/api/ingest-status`: 200 OK, `target_region_codes` вернулся как пустая строка.

**Известные проблемы / TODO:**
- При загрузке всей России объём данных и число detail-fetch запросов вырастут; текущий лимит `INGEST_DETAIL_MAX_PER_RUN=200` остаётся защитой от слишком тяжёлого одного прохода.

**Следующее:**
- Запустить ручной ingest из `/ingest` на пустой базе и посмотреть время первого прохода/объём сохранённых лотов.

---

## 2026-05-08 - Очистка локальных данных для проверки чистого старта

**Что сделано:**
- Остановлены локальные процессы backend/frontend, запущенные из этой копии проекта.
- Удалены восстановимые локальные данные:
  - `data/app.db`;
  - `data/migration_check.db`;
  - всё содержимое `data/raw/`.
- Директория `data/raw/` создана заново пустой, чтобы скрипты могли продолжать использовать ожидаемый путь.
- Backend и frontend запущены заново; backend создал новую пустую SQLite-базу через `create_all()`.

**Затронутые файлы:**
- WORKLOG.md
- data/app.db (удалён и затем создан заново пустым при старте backend; gitignored)
- data/raw/* (удалено; gitignored)

**Проверки:**
- `GET http://localhost:8000/health`: 200 OK.
- `GET http://localhost:8000/api/lots?limit=1`: 200 OK, ответ `{"items":[],"total":0,"limit":1,"offset":0}`.
- `GET http://localhost:8000/api/ingest-runs?limit=5`: 200 OK, ответ `[]`.
- `GET http://localhost:5173`: 200 OK.
- `data/raw/`: пустая директория.

**Известные проблемы / TODO:**
- Данные отсутствуют намеренно; для проверки загрузки с нуля нужно запустить ingest вручную из `/ingest` или дождаться планировщика.

**Следующее:**
- Пройти UI-smoke-test на пустой базе: Dashboard, `/lots`, `/notices`, `/ingest`, ручной запуск загрузки.

---

## 2026-05-08 - Приведение страницы лотов и мульти-региональный фильтр

**Что сделано:**
- Переработана страница `/lots`: фильтры выровнены в плотную сетку с подписями, действия приведены к единому виду кнопок.
- Фильтр региона больше не превращается в выпадающий список; это всегда текстовое поле.
- Поле региона поддерживает несколько кодов через запятую, например `72,86`; при применении пробелы нормализуются.
- Backend `/api/lots` и `/api/export/lots.csv` теперь принимают `region` как один код, повторяющиеся query-параметры или строку с кодами через запятую.
- Таблица лотов укрупнена и выровнена: длинное название больше не зажимается в узкую колонку, кадастр показан под названием, статус/регион/муниципалитет сгруппированы, цена и baseline показываются компактными блоками.
- Обновлён `AGENTS.md`, так как изменился контракт фильтра `region` в API.

**Затронутые файлы:**
- backend/app/api.py
- backend/tests/test_api.py
- frontend/src/pages/LotsPage.tsx
- frontend/src/components/LotsTable.tsx
- frontend/src/styles.css
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло; остаётся известное предупреждение Vite о крупном lazy chunk карты MapLibre.
- `$env:PYTHONPATH='.'; python -m pytest` в `backend/`: 55 passed.
- `GET http://localhost:8000/api/lots?region=72,86&limit=1`: 200 OK.
- `GET http://localhost:5173/lots`: 200 OK.

**Известные проблемы / TODO:**
- Нужен ручной визуальный smoke-test `/lots` в браузере: проверить форму, таблицу и фильтр `72,86` на реальных данных.

**Следующее:**
- Если новая таблица устроит, можно отдельно русифицировать сырые статусы `notice`/`protocol` и добавить сохранённые пресеты фильтров.

---

## 2026-05-08 - Компактная история загрузок ingest

**Что сделано:**
- Переработана страница `/ingest`: основная история запусков теперь показывает только ключевые поля `#`, статус, старт, длительность, получено, сохранено, изменено, файлы и тип сбоя.
- Убраны широкие колонки с URL и полным текстом ошибки из основной таблицы.
- Добавлено раскрытие строки через кнопку `Детали`: внутри показываются финиш, тип сбоя, обработанные/упавшие файлы, последний URL ошибки и человекочитаемый текст ошибки.
- Сокращён поясняющий текст над историей, чтобы страница не выглядела как справка.
- Добавлены CSS-стили для компактной таблицы, фиксированных ширин колонок и раскрытого диагностического блока.
- Запущены локальные dev-серверы для проверки страницы: backend `http://localhost:8000`, frontend `http://localhost:5173`.

**Затронутые файлы:**
- frontend/src/pages/IngestRunsPage.tsx
- frontend/src/styles.css
- WORKLOG.md

**Проверки:**
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло; остаётся известное предупреждение Vite о крупном lazy chunk карты MapLibre.
- `GET http://localhost:8000/health`: 200 OK.
- `GET http://localhost:5173`: 200 OK.

**Известные проблемы / TODO:**
- Визуальный smoke-test в браузере руками ещё полезен: открыть `/ingest`, раскрыть строку с ошибкой и проверить, что длинный URL не ломает ширину.

**Следующее:**
- Если компактная таблица устроит по ощущениям, можно отдельно улучшить подписи статусов ingest с `partial_failed`/`success` на русские пользовательские названия.

---

## 2026-05-07 - UX загрузок: статус, расписание и ручной запуск ingest

**Цель:** сделать загрузки понятными пользователю: видно, идёт ли скачивание, работает ли планировщик, когда следующий автозапуск, и можно ли запустить загрузку вручную.

**Что сделано:**
- Backend:
  - добавлен guarded ingest-runner с `asyncio.Lock`, чтобы manual/scheduled ingest не запускались параллельно;
  - `scheduled_ingest()` теперь использует общий guarded runner;
  - добавлен `GET /api/ingest-status` с полями `is_running`, `scheduler_running`, `next_run_at`, `interval_minutes`, `run_on_startup`, `fetch_notice_details`, `detail_max_per_run`, `target_region_codes`;
  - добавлен `POST /api/ingest-runs/start`, который запускает operational ingest в фоне и возвращает `started=false`, если загрузка уже идёт.
- Frontend `/ingest`:
  - добавлена кнопка «Запустить загрузку»;
  - показаны карточки статуса: сейчас идёт/не идёт, автоматический интервал, следующий запуск, региональный фокус, detail JSON;
  - добавлено короткое объяснение: загрузка не постоянная, она идёт по расписанию или вручную; ошибки видны в истории;
  - при активной загрузке страница автообновляется раз в 5 секунд.
- Обновлены [README.md](README.md), [AGENTS.md](AGENTS.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

**Затронутые файлы:**
- backend/app/scheduler.py
- backend/app/api.py
- backend/app/schemas.py
- backend/tests/test_api.py
- frontend/src/api.ts
- frontend/src/types.ts
- frontend/src/pages/IngestRunsPage.tsx
- frontend/src/styles.css
- README.md
- AGENTS.md
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 55 passed.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло; MapLibre остаётся крупным lazy chunk.
- `GET http://localhost:8000/api/ingest-status`: 200 OK, показал `is_running=false`, `scheduler_running=true`, следующий запуск 2026-05-08.

**Известные проблемы / TODO:**
- Кнопка запускает настоящий live-ingest; при VPN/недоступности Торгов ожидаемо появится ошибка `source_unavailable` в истории.
- Ручной запуск пока только `operational`, backfill из UI не добавлялся.

**Следующее:**
- Пройти ручной UX smoke-test `/ingest`: нажать кнопку в среде с доступом к Торгам и убедиться, что running/success/failed статусы понятны пользователю.

---

## 2026-05-07 - MVP hardening: demo-data, ФИАС, Dashboard quality, frontend resilience

**Цель:** выполнить пункты 1-5 MVP-плана: привести уже существующую функциональность к рабочему состоянию без `mvp_score` и без Telegram-алертов.

**Что сделано:**
- Разобрано текущее рабочее дерево: содержательные изменения были в backend/doc-части предыдущего шага; несколько frontend/alerts файлов помечены git как modified из-за LF/CRLF без содержательного diff.
- Добавлен offline demo-loader `backend/scripts/load_demo_tyumen_data.py`:
  - читает `data/raw/torgi_opendata_tyumen_union.json`;
  - читает сохранённые detail JSON из `data/raw/torgi_sample_lots_full_20260507`;
  - не ходит в сеть;
  - поддерживает `--reset` для воспроизводимой dev-БД.
- Добавлены поля `Lot.permitted_use_codes`, `Lot.municipality`, `Lot.settlement`.
- Добавлена Alembic-ревизия `20260507_07_add_lot_municipality_fields.py`.
- `detail_parser` теперь извлекает ФИАС-муниципалитет/населённый пункт из `estateAddressFIAS.addressByFIAS.hierarchyObjects[]`.
- Ingest сохраняет `permitted_use_codes`, `municipality`, `settlement`; `reprocess_lots_offline.py` умеет добирать эти поля из сохранённых snapshot payload.
- API расширен:
  - `/api/lots` и CSV поддерживают `municipality`, `has_cadastral`, `has_price_per_sotka`, `has_positive_discount`;
  - `/api/lots/facets` возвращает `municipality`;
  - добавлен `/api/lots/quality?region=72` для Dashboard-метрик качества данных.
- Dashboard получил блок качества данных по Тюменской области: ИЖС-кандидаты, муниципалитет, кадастр, площадь, стартовая цена, ₽/сотка, baseline, положительный дисконт.
- `/lots` получил быстрые фильтры качества и фильтр по муниципалитету.
- Карточка лота показывает муниципалитет, населённый пункт, коды ВРИ и объяснение, почему лот считается/не считается ИЖС-кандидатом.
- Добавлен базовый frontend ErrorBoundary.
- Обновлены [README.md](README.md), [AGENTS.md](AGENTS.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

**Затронутые файлы:**
- .env.example
- backend/app/config.py
- backend/app/models.py
- backend/app/api.py
- backend/app/schemas.py
- backend/app/services/ingest/normalizer.py
- backend/app/services/ingest/detail_parser.py
- backend/app/services/ingest/service.py
- backend/alembic/versions/20260507_07_add_lot_municipality_fields.py
- backend/scripts/load_demo_tyumen_data.py
- backend/scripts/reprocess_lots_offline.py
- backend/tests/test_api.py
- backend/tests/test_detail_parser.py
- backend/tests/test_ingest_service.py
- backend/tests/test_normalizer_notices.py
- frontend/src/api.ts
- frontend/src/types.ts
- frontend/src/main.tsx
- frontend/src/components/ErrorBoundary.tsx
- frontend/src/components/LotsTable.tsx
- frontend/src/pages/DashboardPage.tsx
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/pages/LotsPage.tsx
- frontend/src/styles.css
- README.md
- AGENTS.md
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 53 passed.
- `python scripts/dev_sync_schema.py` в `backend/`: добавлены `permitted_use_codes`, `municipality`, `settlement`, индексы `ix_lots_municipality`, `ix_lots_settlement`; FK-warning ожидаемый для существующей SQLite.
- `DATABASE_URL=sqlite+pysqlite:///../data/demo_loader_check.db python scripts/load_demo_tyumen_data.py --reset`: прошло, 77 `OpenDataNotice`, 15 Lot, 8 ИЖС-кандидатов, 13 лотов с ₽/сотка; временная БД удалена.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло; MapLibre остаётся крупным lazy chunk.
- `git diff --check`: без whitespace-ошибок, только обычные предупреждения LF -> CRLF.

**Известные проблемы / TODO:**
- Реальный manual smoke-test в браузере на demo-БД ещё не пройден.
- НСПД-клиент и модель кадастрового обогащения ещё не подключены.
- `mvp_score` и Telegram smart-алерты отложены по решению пользователя.
- Non-notice event обновляет статус только если Lot уже существует по `regNum`.

**Следующее:**
- Запустить demo-БД командой `python scripts/load_demo_tyumen_data.py --reset`, поднять backend/frontend и пройти страницы `/`, `/lots`, `/lots/:id`, `/notices`, `/ingest`.
- После ручного smoke-test переходить к проектированию `CadastralEnrichment` / НСПД-клиента.

---

## 2026-05-07 - Исправления ingest по итогам source discovery

**Цель:** применить high-priority выводы разведки источников без live-ingest и без массовых сетевых запросов.

**Что сделано:**
- Региональная семантика OpenData исправлена: `normalize_lot()` теперь берёт `region` из `subjectEstateCode`, а не из `subjectRightHolderCode`.
- После detail-fetch ingest перепроверяет регион через `lots[].biddingObjectInfo.subjectRF.code`; если detail уточнил регион не из `TARGET_REGION_CODES`, Lot не создаётся/не обновляется.
- Default локального фокуса изменён на `TARGET_REGION_CODES=72`; `.env.example` теперь описывает `subjectEstateCode`, а не регион правообладателя.
- `detail_parser` извлекает `permitted_use_codes` из `characteristics[code=PermittedUse].characteristicValue[].code` и `subject_region_code` из `subjectRF.code`.
- ИЖС-детектор теперь предпочитает код ВРИ whitelist `2.1/2.2/2.3/13.1/13.2` с prefix-match (`2.1.2001` считается, `2.7.2001` не считается); `IZHS_KEYWORDS` оставлен fallback'ом, если кода ВРИ нет.
- Ingest перестал создавать пустые Lot из non-notice документов:
  - `clarifications` сохраняется как `OpenDataNotice`, но Lot не создаёт;
  - `noticeCancel/noticeStop/noticeResumption/noticeAnnulment` обновляют статус существующего Lot, если он найден.
- Обновлены тесты на регион, ВРИ-коды, false-positive `2.7.2001` + случайный текст `2.1`, `clarifications` и cancel-event.
- Обновлены [AGENTS.md](AGENTS.md) и [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) под новое поведение ingest.

**Затронутые файлы:**
- .env.example
- backend/app/config.py
- backend/app/services/ingest/normalizer.py
- backend/app/services/ingest/detail_parser.py
- backend/app/services/ingest/service.py
- backend/tests/test_detail_parser.py
- backend/tests/test_ingest_service.py
- backend/tests/test_normalizer_notices.py
- AGENTS.md
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 52 passed.

**Известные проблемы / TODO:**
- ФИАС-иерархия всё ещё не извлекается в нормализованный муниципалитет.
- НСПД endpoint найден разведкой, но клиент и модель обогащения ещё не подключены.
- Non-notice event сейчас обновляет статус только если Lot уже существует по `regNum`; исторические/неслинкованные кейсы могут требовать отдельного backfill.

**Следующее:**
- Добавить извлечение муниципалитета из `estateAddressFIAS.addressByFIAS.hierarchyObjects[]`.
- После этого проектировать `CadastralEnrichment` и НСПД-клиент.

---

## 2026-05-07 - Разведка источников ГИС Торги / НСПД для ИЖС-мониторинга в Тюменской области

**Цель:** проверить, действительно ли проект качает нужные данные из ГИС Торги, и зафиксировать минимально достаточный набор источников для мониторинга земельных участков под ИЖС в Тюменской области и Тюмени.

**Что сделано (только разведка, БД не трогали, `.env` не редактировали, `git commit` не делали):**

1. **OpenData ГИС Торги:** скачан свежий day-файл через `scripts/fetch_latest_opendata.py`:
   - `data/raw/data-20260506T0000-20260507T0000-structure-20240401.json` (1568 записей, 15 по Тюмени).
   - Подтверждено: проект качает правильный dataset `7710568760-notice` (карточка `61f2a3bf11d8ab36f6c1b275`), schema `structure-20240401`.
2. **Локальный union 4 day-файлов** (22, 27, 29 апр + 6-7 мая) → 77 записей по Тюмени (`subjectEstateCode=72 OR subjectRightHolderCode=72`), сохранён в `data/raw/torgi_opendata_tyumen_union.json`. Распределение: 41 ZK, 8 229FZ, 8 178FZ, 6 концессий, 6 1041PP и т.д.
3. **Точечный fetch 16 notice detail JSON** (12 ZK + 1 178FZ + 1 APGU + 1 1041PP + 1 229FZ-cancel) через одноразовый скрипт (без `run_ingest`):
   - Raw сохранены в `data/raw/torgi_sample_lots_full_20260507/<regNum>.json`.
   - Прогон через `detail_parser.parse_notice_detail()`: coverage 75-100% по всем нужным полям (`cadastral_number 81%`, `area_sqm 87.5%`, `land_category 93.8%`, `permitted_use_text/code 75%`, `address 93.8%`, `start_price 81%`, `lot_name 100%`, `subjectRF_code 93.8%`, `municipality_fias 93.8%`, `lot_status 93.8%`, `bidd_dates 93.8%`, `organizer 93.8%`, `ui_href 100%`).
   - Сводка: `data/raw/torgi_sample_lots_20260507.json`.
4. **HTML / SPA-XHR probe** торгов (`data/raw/torgi_ui_probe_20260507.json`):
   - HTML карточек `/new/public/notices/view/<id>` — пустой SPA-shell (одинаковые 22.7 KB), парсить нет смысла.
   - **Найден рабочий публичный SPA endpoint** `/new/api/public/notices/search?dynSubjRF=72&biddType=ZK&size=5` (200 OK, Spring pageable, 63 KB). Каждый item содержит `lots[].attributes[]` — те же поля, что в notice detail. Это альтернативный pipeline c серверной фильтрацией.
5. **НСПД discovery** (`data/raw/nspd_samples_20260507.json`):
   - Проверены 5 endpoint-шаблонов на 1 кадастре: только **`https://nspd.gov.ru/api/geoportal/v1/search/geoportal?query=<cadnum>&thematicSearchId=1`** отвечает 200 (остальные 403/404).
   - Прогнаны 8 кадастров из выборки: 8/8 успешно. Ответ — GeoJSON Feature с полигоном (EPSG:3857) и `properties.options`: `cad_num, specified_area, declared_area, land_record_category_type, permitted_use_established_by_document, readable_address, cost_value (кадастровая стоимость, БОНУС не в Торгах), cost_index (УПКС), quarter_cad_number, ownership_type, status`.
6. **Сравнение ИЖС-детектора** (`_recon_compare_izhs.py`): по PermittedUse.code (whitelist + prefix) = 7/16, по текущему `match_izhs()` (substring) = 7/16, **но 2 mismatch'а** (1 false positive — лот за 49 млн руб с ВРИ `2.7.2001` ошибочно ловится на substring `2.1`; 1 false negative — лот с ВРИ `2.2` не ловится keyword'ом). Доля ошибок ≈12.5% даже на маленькой выборке.

**Ключевые находки и узкие места текущего ingest (зафиксированы в отчёте, НЕ применены):**

1. **`TARGET_REGION_CODES=""` по умолчанию** — фильтра региона нет, БД растёт всеми регионами.
2. **Семантика регионального фильтра неправильная**: `normalizer.region` берёт `subjectRFCode` (нет в schema 20240401) → fallback на `subjectRightHolderCode` (регион правообладателя, а не земли). В выборке 1/16 лот с `estate=86 (ХМАО) / right=72 (Тюмень)` — будет ошибочно засчитан как Тюменский. Правильный ключ: `subjectEstateCode` + кросс-валидация через detail `lots[].biddingObjectInfo.subjectRF.code`.
3. **ИЖС-детектор по substring `2.1` шумит** (см. п.6 выше). Рекомендация: переключить на `characteristics[code=PermittedUse].characteristicValue[].code` против белого списка.
4. **`documentType=clarifications` пишется как Lot**, хотя это разъяснение к существующему извещению (без `lots[].biddingObjectInfo`). Аналогично `noticeStop/Resumption/Annulment` — должны менять статус существующего лота, а не создавать новый.
5. **ФИАС-иерархия не извлекается** — нельзя нормально фильтровать по муниципалитету.

**Ответы на главный вопрос:**

- **Скачивает ли текущий проект правильные данные?** Да. Dataset `7710568760-notice`, schema `20240401`, schema discovery работает, watermark и идемпотентность работают.
- **Достаточно ли OpenData ГИС Торги для MVP?** Listings (`listObjects`) — нет, это только индекс. **Достаточно OpenData listObjects + fetched notice detail JSON** (наш текущий двухступенчатый ingest), 75-100% coverage.
- **Что нужно из карточки лота?** Всё, что не влезло в listObjects: `characteristics.CadastralNumber/SquareZU/PermittedUse(code)`, `category`, `estateAddressFIAS`, `lotStatus`, `priceMin`, `bidderOrg`, `biddConditions.bidd*Time`, `commonInfo.href` (UI-ссылка), `subjectRF.code`. Уже извлекается, кроме FIAS-иерархии и `subjectRF.code` и **кода** PermittedUse.
- **Что нужно из НСПД?** Геометрия (для карты), кадастровая стоимость + УПКС (для скоринга/baseline), точная площадь (для кросс-валидации). Не блокирует MVP.
- **Какие изменения нужны в текущем ingest?** См. рекомендации в `data/raw/source_discovery_20260507.md` (6 high-priority + 2 mid-priority пунктов).

**Артефакты в `data/raw/`:**

- `source_discovery_20260507.md` — финальный отчёт с таблицей «поле → источник → надёжность», 16 примерами лотов, mermaid-диаграммой, рекомендациями.
- `source_discovery_20260507.json` — машиночитаемая сводка.
- `torgi_opendata_tyumen_union.json` — union 4 day-файлов по Тюмени (77 записей).
- `torgi_sample_lots_20260507.json` — обогащённая выборка 16 лотов.
- `torgi_sample_lots_full_20260507/<regNum>.json` × 16 — исходные detail JSON.
- `torgi_ui_probe_20260507.json` — HTML/SPA probe.
- `nspd_samples_20260507.json` — 8 ответов НСПД.
- `data-20260506T0000-20260507T0000-structure-20240401.json` — свежий day-файл OpenData.

**Скрипты разведки** (одноразовые, помечены префиксом `_recon_`, в проде не используются):

- `backend/scripts/_recon_pick_sample.py`
- `backend/scripts/_recon_fetch_details.py`
- `backend/scripts/_recon_summarize_sample.py`
- `backend/scripts/_recon_check_html_and_ui.py`
- `backend/scripts/_recon_probe_nspd.py`
- `backend/scripts/_recon_compare_izhs.py`
- `backend/scripts/_recon_build_report.py`

**Что НЕ сделано (по условию задачи):**

- Не запускали `run_ingest()` / `import_opendata_to_db.py`.
- Не редактировали `.env`.
- Не правили `backend/app/...` / `frontend/src/...`.
- Не делали `git commit` / `git push`.

**Следующие шаги** (после утверждения отчёта, отдельной задачей):

- Применить рекомендации по `region`-фильтру (estate-based + subjectRF.code из detail).
- Переключить ИЖС-детектор на PermittedUse.code whitelist.
- Маршрутизировать `documentType` (notice → upsert, остальное → status update).
- Добавить ФИАС-извлечение муниципалитета.
- Подключить НСПД-обогащение по найденному endpoint'у.

---

## 2026-05-06 - Закрытие технических рисков: карта, CI, lifespan, dev SQLite, MapLibre chunk

**Что сделано:**
- Исправлен XSS-риск в `TradesMap`: popup больше не собирается через `setHTML`; используется `setDOMContent` и DOM-узлы с `textContent`.
- GitHub Actions frontend job расширен: после `npx tsc --noEmit` запускаются `npm run test` и `npm run build`.
- Backend переведён с deprecated FastAPI `@app.on_event("startup")` на lifespan:
  - startup-логика вынесена в `_startup()`;
  - при shutdown вызывается остановка APScheduler через `stop_scheduler()`;
  - pytest больше не показывает warnings про deprecated `on_event`.
- Выбрана стратегия для dev SQLite:
  - Alembic остаётся источником истины для production;
  - `dev_sync_schema.py` добавляет новые колонки и недостающие индексы;
  - отсутствующие FK в существующей SQLite-таблице выводятся как warning, потому что SQLite требует rebuild/fresh DB.
- Запущен `python scripts/dev_sync_schema.py`: созданы недостающие индексы `ix_ingest_manifest_error_kind`, `ix_ingest_runs_error_kind`, `ix_lots_is_izhs_candidate`, `ix_lots_opendata_notice_id`, `ix_lots_cadastral_number`; подтвержден warning про FK `lots.opendata_notice_id`.
- MapLibre разгружен из основного bundle:
  - `MapPage` лениво загружается через `React.lazy`;
  - `TradesMap` лениво загружается на странице карты и в карточке лота;
  - Vite build теперь даёт основной `index` около 220 KB, а MapLibre остаётся отдельным async chunk.
- Обновлены [README.md](README.md), [AGENTS.md](AGENTS.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

**Затронутые файлы:**
- .github/workflows/ci.yml
- backend/app/main.py
- backend/app/scheduler.py
- backend/scripts/dev_sync_schema.py
- frontend/src/App.tsx
- frontend/src/components/TradesMap.tsx
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/pages/MapPage.tsx
- README.md
- AGENTS.md
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python scripts/dev_sync_schema.py` в `backend/`: прошло, индексы созданы, FK-warning ожидаемый.
- `python -m pytest` в `backend/`: 48 passed, без FastAPI deprecation warnings.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло; предупреждение о крупном chunk осталось только для лениво загружаемого `TradesMap`/MapLibre.

**Известные проблемы / TODO:**
- `dev_sync_schema.py` не rebuild'ит SQLite-таблицы для добавления FK; при необходимости строгой локальной схемы проще создать fresh DB или использовать Alembic/fresh migration path.
- MapLibre всё равно остаётся тяжёлой зависимостью, но теперь не блокирует основной bundle.
- В CI всё ещё нет ruff/eslint и backend migration smoke-test.

**Следующее:**
- Продолжить demo-MVP: добавить на Dashboard метрики качества данных по целевым регионам и объяснение ограничений shortlist.

---

## 2026-05-06 - Demo-MVP: baseline-оценка и shortlist интересных лотов

**Что сделано:**
- Добавлена внутренняя baseline-оценка без внешних маркетплейсов:
  - медиана `start_price_per_sotka` считается на лету по каскаду `region+category -> region -> category -> global`;
  - для каждого лота API возвращает `baseline_price_per_sotka`, `discount_to_baseline`, `valuation_confidence`, `valuation_baseline_scope`, `valuation_baseline_sample_size`, `valuation_reason`;
  - положительный `discount_to_baseline` означает, что стартовая цена за сотку ниже внутреннего baseline.
- Добавлена сортировка `/api/lots?sort=discount_to_baseline_desc`.
- CSV export `/api/export/lots.csv` дополнен baseline-колонками.
- Страница `/lots` показывает baseline, дисконт и уверенность оценки; сортировка получила пункт «По дисконту к baseline».
- Карточка `/lots/:id` показывает baseline-блок и основание расчёта.
- Dashboard получил shortlist «Потенциально интересные ИЖС-кандидаты» по дисконту к baseline.
- Обновлены [README.md](README.md), [AGENTS.md](AGENTS.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

**Затронутые файлы:**
- backend/app/api.py
- backend/app/schemas.py
- backend/tests/test_api.py
- frontend/src/types.ts
- frontend/src/components/LotsTable.tsx
- frontend/src/pages/LotsPage.tsx
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/pages/DashboardPage.tsx
- frontend/src/styles.css
- README.md
- AGENTS.md
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 48 passed, 2 warnings про deprecated FastAPI `on_event`.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло, есть ожидаемое предупреждение о крупном chunk из-за maplibre.

**Известные проблемы / TODO:**
- Это baseline по собственной базе торгов, а не рыночная оценка по Циан/Авито.
- В целевых регионах `72/86/89` пока мало ИЖС-кандидатов с одновременно заполненными стартовой ценой и площадью; для Тюменской области (`72`) сейчас нет ИЖС-кандидатов, по которым можно посчитать дисконт.
- Для рабочего бизнес-скоринга всё ещё нужны НСПД/геометрия и внешние рыночные аналоги.

**Следующее:**
- Для demo-MVP добавить более понятные метрики качества данных на Dashboard: целевые регионы, ИЖС-кандидаты, доля с кадастром/площадью/ценой, чтобы руководству было видно не только shortlist, но и ограничения текущих данных.

---

## 2026-05-06 - Безопасный старт и наблюдаемость ingest

**Что сделано:**
- Выполнен безопасный старт: `git status` показывал изменённые файлы, но `git diff --numstat` / `git diff --raw` не показали содержательных изменений; причина — предупреждения LF -> CRLF при `core.autocrlf=true`.
- Добавлена наблюдаемость ingest на уровне БД/API/UI:
  - `IngestRun`: `processed_files`, `failed_files`, `last_error_source_url`, `error_kind`;
  - `IngestManifest`: `error_kind`;
  - `run_ingest()` сохраняет количество обработанных/упавших файлов, последний URL ошибки и классифицирует `source_unavailable`, `schema_migration_required`, `file_processing_error`;
  - stale `running` ingest при старте помечается `error_kind=interrupted`.
- Добавлена Alembic-ревизия `20260506_06_add_ingest_observability.py`.
- Локальная SQLite-схема синхронизирована через `python scripts/dev_sync_schema.py`.
- `/api/ingest-runs` возвращает новые диагностические поля.
- Страница `/ingest` показывает счётчик файлов, тип сбоя и последний URL ошибки.
- Обновлены [README.md](README.md), [AGENTS.md](AGENTS.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

**Затронутые файлы:**
- backend/app/models.py
- backend/app/services/ingest/service.py
- backend/app/schemas.py
- backend/app/main.py
- backend/alembic/versions/20260506_06_add_ingest_observability.py
- backend/tests/test_api.py
- backend/tests/test_ingest_service.py
- frontend/src/types.ts
- frontend/src/pages/IngestRunsPage.tsx
- frontend/src/styles.css
- README.md
- AGENTS.md
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python scripts/dev_sync_schema.py` в `backend/`: добавлены новые колонки в локальную SQLite.
- `python -m pytest` в `backend/`: 47 passed, 2 warnings про deprecated FastAPI `on_event`.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло.
- `npm.cmd run test` в `frontend/`: 2 passed.
- `npm.cmd run build` в `frontend/`: прошло, есть ожидаемое предупреждение о крупном chunk из-за maplibre.

**Известные проблемы / TODO:**
- Live-доступ к `torgi.gov.ru` из текущей сети ранее падал на timeout, поэтому live-верификация parser coverage остаётся задачей для среды с доступом к РФ-ресурсам.
- Исторический разрыв `Lot` -> `OpenDataNotice` сохраняется для части старых записей; предыдущий dry-run новых совпадений не нашёл.

**Следующее:**
- Продолжить по плану локально: baseline-оценка по собственной базе торгов (`baseline_price_per_sotka`, `discount_to_baseline`, `valuation_confidence`) без ожидания Циан/НСПД.

---

## 2026-05-06 - Проверка запуска проекта, фикс падения DashboardPage

**Что сделано:**
- Подняты dev-сервера:
  - backend: `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`;
  - frontend: `npm run dev` (Vite на `:5173`).
- Подтвержден `GET /health`: `{\"status\":\"ok\"}`.
- Найдено и исправлено падение фронта при рендере `DashboardPage`: в dev-окружении `recentNotices` мог стать `undefined`, и `.length` падал. Добавлена defensive-нормализация ответа (поддержка объекта `{ items, total, ... }` и fallback на массив) перед установкой `recentNotices/recentLots`.

**Затронутые файлы:**
- frontend/src/pages/DashboardPage.tsx

**Проверки:**
- Ручная проверка запуска: backend отвечает на `/health`, Vite отдаёт SPA.

---

## 2026-05-05 - Добавлен frontend test runner (Vitest) и тесты reset/URL-state

**Что сделано:**
- Frontend: добавлен test runner на Vitest + jsdom + Testing Library.
- Добавлены тесты, фиксирующие критичное поведение:
  - `TradesPage`: reset фильтров действительно отправляет запрос на `/api/opendata-notices` без фильтров и с `offset=0`.
  - `LotsPage`: applied-state читается из URL; reset очищает query string и перезагружает список с дефолтами (в API дефолтный `sort=updated_at_desc` уходит как часть текущей реализации).

**Затронутые файлы:**
- frontend/package.json
- frontend/vite.config.ts
- frontend/src/test/setup.ts
- frontend/src/pages/TradesPage.test.tsx
- frontend/src/pages/LotsPage.test.tsx

**Проверки:**
- `npm run test` в `frontend/`: 2 passed.
- `npx tsc --noEmit` в `frontend/`: прошло.
- `npm run build` в `frontend/`: прошло (есть ожидаемое предупреждение о крупном chunk из-за maplibre).

**Следующее:**
- При расширении URL-синхронизации на страницу извещений добавить аналогичные тесты для query params (если решим синхронизировать `/notices` с URL).

---

## 2026-05-05 - План делегирования для ИИ с доступом к РФ-ресурсам

**Что сделано:**
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) дополнен разделом «0. Делегирование ИИ с прямым доступом к РФ-ресурсам».
- Раздел описывает правила работы внешнего агента, который не зависит от VPN и может ходить на `torgi.gov.ru`, `nspd.gov.ru` и потенциально рыночные сайты.
- Сформированы конкретные задачи для делегирования:
  - обновить свежие OpenData-файлы Торгов через `fetch_latest_opendata.py`;
  - выполнить live-верификацию `detail_parser` на окне 10 дней;
  - проверить live ingest на малом/контролируемом прогоне;
  - провести НСПД discovery по 20-30 кадастровым номерам;
  - предварительно разведать доступность Циан/Авито/Домклик без массового парсинга.
- Для каждой задачи указаны команды, ожидаемые артефакты и что нужно вернуть обратно в этот репозиторий.
- Приоритет следующего рабочего захода в плане разделён на две дорожки: внешний ИИ с российским IP и текущий Codex/VPN-окружение.

**Затронутые файлы:**
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `git diff HEAD --check`: планируется после записи; кодовые проверки не требуются, потому что изменена только документация.

**Известные проблемы / TODO:**
- Нужно получить от внешнего агента свежие `data-*.json`, live coverage report и НСПД samples, чтобы продолжить работу над parser/кадастровым слоем.

**Следующее:**
- Передать внешнему ИИ задачи A/B из `DEVELOPMENT_PLAN.md`, затем импортировать его артефакты в `data/raw/` и обновить WORKLOG фактическими результатами.

---

## 2026-05-05 - Server-side пагинация извещений OpenData

**Что сделано:**
- Backend: `/api/opendata-notices` переведён с массива на страницу `{ items, total, limit, offset }`; добавлен query-параметр `offset`, `limit` оставлен с `ge=1` / `le=1000`.
- Backend schemas: добавлен `OpenDataNoticeListPage`.
- Backend tests: обновлены ожидания фильтров извещений под новый page-ответ, добавлена проверка пагинации по `limit=1` / `offset`.
- Frontend API/types: `fetchNotices` теперь возвращает `NoticeListPage`, добавлен тип `NoticeListPage`.
- Frontend Dashboard: метрика извещений теперь берёт `total` из `/api/opendata-notices`, а список последних извещений — `items`.
- Frontend Notices: добавлена server-side пагинация по 50 записей, отображение общего количества и диапазона записей.
- Документация: обновлены [README.md](README.md), [AGENTS.md](AGENTS.md), [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).
- Сетевые запросы к `torgi.gov.ru` не выполнялись; задача полностью локальная.

**Затронутые файлы:**
- backend/app/api.py
- backend/app/schemas.py
- backend/tests/test_api.py
- frontend/src/api.ts
- frontend/src/types.ts
- frontend/src/pages/DashboardPage.tsx
- frontend/src/pages/TradesPage.tsx
- README.md
- AGENTS.md
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 46 passed, 2 warnings про deprecated FastAPI `on_event`.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло без ошибок.
- `npm.cmd run build` в `frontend/`: прошло, есть ожидаемое предупреждение о крупном chunk из-за maplibre.
- `git diff HEAD --check`: прошло без ошибок, есть только предупреждения Git о будущей CRLF-нормализации изменённых файлов.

**Известные проблемы / TODO:**
- Страница Notices пока не синхронизирует фильтры/offset с URL, в отличие от Lots.
- Frontend test runner всё ещё не добавлен.

**Следующее:**
- Улучшить наблюдаемость ingest: `processed_files`, `failed_files`, последний `source_url` ошибки и более явное различение временной недоступности источника от настоящей ошибки схемы.

---

## 2026-05-05 - Пункт 2 плана: проверка ingest-надежности без доступа к Торгам

**Что сделано:**
- Попытка обновить свежий opendata-указатель через `python scripts/fetch_latest_opendata.py` не удалась: `httpx.ConnectTimeout [WinError 10060]` при обращении к `https://torgi.gov.ru/new/public/opendata/...`.
- Малый live-прогон `verify_detail_parser_window.py --days 1 --limit-per-day 5` также не получил данные: `processed_days=0/1`, внутри daily-прогона `httpx.ConnectError: All connection attempts failed`.
- Чтобы не перезаписывать старые daily-отчёты, live-attempt запускался в отдельный `tmp-dir`: `data/raw/live_attempt_20260505`; итоговый JSON: `data/raw/detail_parser_window_verification_live_attempt_20260505.json`.
- Выполнен офлайн-пересчёт существующих daily-отчётов: `verify_detail_parser_window.py --reanalyze-existing --days 5`, артефакт `data/raw/detail_parser_window_reanalyze_existing_20260505.json`.
- Итог офлайн-пересчёта: 5/5 дней, 295 fetched / 294 successful / 1 failed; field coverage sum: cadastral_number 171, area_sqm 112, land_category 294, permitted_use 164, address 291, lot_name 294, start_price 196.
- Сегмент `is_land_plot=true` (n=160): cadastral_number 112, area_sqm 107, permitted_use 159, start_price 62.
- `link_lots_to_notices.py --dry-run`: новых совпадений нет (`linked_via_href=0`, `linked_via_reg_num=0`), поэтому apply-прогон не запускался. Текущее состояние БД: lots_total 5207, lots_linked 2289, lots_unlinked 2918, notices_total 2419.
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) обновлён фактическими результатами пункта 2.

**Затронутые файлы:**
- DEVELOPMENT_PLAN.md
- WORKLOG.md
- data/raw/detail_parser_window_verification_live_attempt_20260505.json (артефакт, gitignored)
- data/raw/detail_parser_window_reanalyze_existing_20260505.json (артефакт, gitignored)
- data/raw/link_lots_to_notices_dry_run_20260505.json (артефакт, gitignored)

**Проверки:**
- `python scripts/fetch_latest_opendata.py`: не прошло из-за сетевого timeout к `torgi.gov.ru`.
- `python scripts/verify_detail_parser_window.py --days 1 --limit-per-day 5 --tmp-dir ..\data\raw\live_attempt_20260505 --output ..\data\raw\detail_parser_window_verification_live_attempt_20260505.json`: завершилось, но processed_days=0/1 из-за `ConnectError`.
- `python scripts/verify_detail_parser_window.py --reanalyze-existing --days 5 --tmp-dir ..\data\raw --output ..\data\raw\detail_parser_window_reanalyze_existing_20260505.json`: прошло.
- `python scripts/link_lots_to_notices.py --dry-run --output ..\data\raw\link_lots_to_notices_dry_run_20260505.json`: прошло, новых link-кандидатов 0.

**Известные проблемы / TODO:**
- Live-верификация parser coverage невозможна, пока VPN ведёт через иностранный IP или `torgi.gov.ru` недоступен.
- 2918 лотов остаются без `opendata_notice_id`; текущий matching по `href` / `reg_num` новых пар не находит.

**Следующее:**
- Продолжить локальную часть пункта 2: полноценная пагинация `/api/opendata-notices` и улучшение наблюдаемости ingest без обращения к Торгам.

---

## 2026-05-05 - Стабилизация API и UI после ревизии

**Что сделано:**
- Backend: добавлены нижние границы `ge=1` для query-лимитов `/api/lots`, `/api/export/lots.csv`, `/api/ingest-runs`, `/api/opendata-notices`, чтобы нулевые/отрицательные значения не уходили в SQL.
- Backend tests: добавлены проверки 422 для невалидных лимитов, сортировки `/api/lots` по `price_per_sotka` и CSV export с несколькими `category`.
- Frontend: исправлен reset фильтров на странице извещений — таблица перезагружается с явно пустыми фильтрами, без stale state.
- Frontend: страница лотов теперь восстанавливает применённые фильтры/сортировку/offset из URL и обновляет URL при пагинации/смене сортировки; CSV export строится по применённым query-параметрам.
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) обновлён: первый стабилизационный блок отмечен как выполненный, кроме будущего frontend test runner.
- Live-загрузка с `torgi.gov.ru` не запускалась: пользователь предупредил, что из-за VPN доступ к российским государственным сайтам, скорее всего, заблокирован.

**Затронутые файлы:**
- backend/app/api.py
- backend/tests/test_api.py
- frontend/src/pages/TradesPage.tsx
- frontend/src/pages/LotsPage.tsx
- DEVELOPMENT_PLAN.md
- WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 46 passed, 2 warnings про deprecated FastAPI `on_event`.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло без ошибок.
- `npm.cmd run build` в `frontend/`: прошло, есть ожидаемое предупреждение о крупном chunk из-за maplibre.
- `git diff HEAD --check`: прошло без ошибок, есть только предупреждения Git о будущей CRLF-нормализации изменённых файлов.

**Известные проблемы / TODO:**
- Frontend test runner пока не добавлен; reset-фильтры покрыты только ручной логикой и TypeScript/build-проверкой.
- FastAPI startup hooks всё ещё на deprecated `@app.on_event`; перенос на lifespan остаётся техническим TODO.
- Пагинация `/api/opendata-notices` всё ещё только через `limit`; полноценный `{ items, total, limit, offset }` остаётся следующим backend-шагом.

**Следующее:**
- Продолжить план с локальных задач, не требующих доступа к Торгам: server-side пагинация `/api/opendata-notices`, затем улучшение наблюдаемости ingest.

---

## 2026-05-05 - Ревизия кода и план дальнейшего развития

**Что сделано:**
- Проведена ревизия текущего backend/frontend состояния после MVP-итераций с пагинацией лотов, CSV export, расчетом ₽/сотка, startup-ingest по флагу и CI.
- Создан [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) с этапами развития: стабилизация, надежность ingest, НСПД, baseline-оценка, рыночные аналоги, инвестиционный скоринг, smart-алерты, production-подготовка.
- Нормализовано форматирование [frontend/src/api.ts](frontend/src/api.ts): удалены лишние CR/trailing whitespace, текущий diff относительно `HEAD` проходит whitespace-check.
- Зафиксированы найденные риски для ближайшего исправления:
  - API принимает отрицательные `limit` / `max_rows`, потому что задан только верхний предел;
  - сброс фильтров на странице извещений вызывает `load()` до применения нового React state;
  - пагинация и сортировка лотов меняют таблицу, но не всегда синхронизируют URL.

**Затронутые файлы:**
- DEVELOPMENT_PLAN.md (новый)
- frontend/src/api.ts
- WORKLOG.md

**Проверки:**
- `python -m pytest` в `backend/`: 45 passed, 2 warnings про deprecated FastAPI `on_event`.
- `npx.cmd tsc --noEmit` в `frontend/`: прошло без ошибок.
- `npm.cmd run build` в `frontend/`: прошло, есть ожидаемое предупреждение о крупном chunk из-за maplibre.
- `git diff HEAD --check`: прошло без ошибок, есть только предупреждения Git о будущей CRLF-нормализации `WORKLOG.md` и `frontend/src/api.ts`.
- Примечание: прямой `pytest` не увидел пакет `app` в этой оболочке, а `npx tsc --noEmit` через `npx.ps1` заблокирован PowerShell ExecutionPolicy; рабочие команды выше.

**Известные проблемы / TODO:**
- Исправить найденные при ревизии P2/P3-пункты из `DEVELOPMENT_PLAN.md`.
- Перевести FastAPI startup hooks на lifespan при ближайшей технической итерации.

**Следующее:**
- Начать со стабилизации: нижние границы query-лимитов, reset фильтров извещений, URL-sync пагинации/сортировки лотов.

---

## 2026-05-05 - MVP-итерация: пагинация лотов, ₽/сотка, CSV, старт ingest по флагу, CI

**Что сделано:**
- Backend: `GET /api/lots` возвращает `LotListPage` (`items`, `total`, `limit`, `offset`), параметры `offset`, `sort` (`updated_at_desc` | `price_per_sotka_asc` | `price_per_sotka_desc`); в списке и в `LotDetail` — вычисляемые `start_price_per_sotka` / `start_price_per_sqm` (из извещения, 1 сотка = 100 м²).
- `GET /api/export/lots.csv` — выгрузка с теми же фильтрами и сортировкой, UTF-8 BOM, лимит строк `max_rows`.
- `RUN_INGEST_ON_STARTUP` (по умолчанию `false`) и `TELEGRAM_ALERT_ONLY_IZHS` в [backend/app/config.py](backend/app/config.py); стартовый ingest только при флаге [backend/app/main.py](backend/app/main.py); в [.env.example](.env.example) для dev указано `RUN_INGEST_ON_STARTUP=true`.
- Telegram: при `TELEGRAM_ALERT_ONLY_IZHS=true` события для не-ИЖС лотов не отправляются [backend/app/services/alerts/service.py](backend/app/services/alerts/service.py).
- Frontend: `fetchLots` → `LotListPage`, дашборд считает `total` без выборки 1000 строк; страница лотов — пагинация по 50, сортировка, ссылка «Скачать CSV», колонка ₽/сотка; карточка лота — две строки метрик.
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml): pytest (backend) и `tsc --noEmit` (frontend) на push/PR.
- Документация: [README.md](README.md), [AGENTS.md](AGENTS.md).

**Затронутые файлы:**
- backend/app/api.py, backend/app/schemas.py, backend/app/config.py, backend/app/main.py
- backend/app/services/alerts/service.py
- backend/tests/test_api.py
- frontend/src/api.ts, frontend/src/types.ts, frontend/src/pages/LotsPage.tsx, frontend/src/pages/DashboardPage.tsx, frontend/src/pages/LotDetailPage.tsx, frontend/src/components/LotsTable.tsx, frontend/src/styles.css
- .env.example, .github/workflows/ci.yml, README.md, AGENTS.md, WORKLOG.md

**Проверки:**
- `pytest` в `backend/`
- `npx tsc --noEmit` в `frontend/`

**Известные проблемы / TODO:**
- Пагинация `/api/opendata-notices` не делалась.

**Следующее:**
- При первом запуске без записей в `ingest_runs` и с `RUN_INGEST_ON_STARTUP=false` дождаться планового job или запустить ingest вручную.

---

## 2026-05-05 - UI: переносы текста и защита от «вылетов» в таблицах/карточке

**Что сделано:**
- Исправлено отображение длинных сообщений об ошибках в истории ingest: ячейка «Ошибка» больше не обрезается в одну строку, длинные URL переносятся.
- Уплотнение таблицы «Загрузки данных»: даты/числа зафиксированы в `nowrap`, числовые колонки выровнены вправо, колонке ошибки задан бюджет ширины.
- Защита карточки лота от длинных значений (адрес/ВРИ/ссылки): добавлены корректные flex-настройки и переносы.
- В таблице лотов длинные названия больше не «раздвигают» таблицу; бейдж «ИЖС» переносится при дефиците места.
- Для `reg_num` и дат в таблицах извещений добавлены `mono` + `nowrap`, чтобы длинные номера не ломали вёрстку.

**Затронутые файлы:**
- frontend/src/styles.css
- frontend/src/pages/IngestRunsPage.tsx
- frontend/src/components/LotsTable.tsx
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/components/TradesTable.tsx
- frontend/src/pages/DashboardPage.tsx
- WORKLOG.md

**Проверки:**
- —

**Известные проблемы / TODO:**
- —

**Следующее:**
- при необходимости: пройтись по оставшимся таблицам и навесить `cell--nowrap` на даты/идентификаторы при жалобах на переносы.

---

## 2026-05-05 - Чистка ingest_manifest, перезапуск API, ручной ingest, верификация detail_parser

**Что сделано:**
- Расширен [backend/scripts/repair_poisoned_ingest_manifests.py](backend/scripts/repair_poisoned_ingest_manifests.py): кроме error-envelope Торгов удаляются строки `processed` с `records_count=0`, если по URL сейчас отдаётся непустой `listObjects` (несогласованность манифеста с живым ответом).
- Перезапуск uvicorn без `--reload`: при старте закрыто **3** зависших `IngestRun` в `running` (в т.ч. бывший id=15 с сообщением «Interrupted before completion»).
- Запуск repair: удалены **4** манифеста (id 2, 5, 6, 7): живые размеры срезов 1324 / 19 / 26 / 22 объектов.
- Ручной прогон `scheduled_ingest()`: запись **id=16**, статус `partial_failed` (обработано **3** файла, **1** срез `data-20260504…20260505` упал на error-envelope Торгов «файл не подготовлен»), метрики **67 / 67 / 67** (получено / сохранено / изменено под фильтром региона и лимитом detail).
- Лотов в БД: **4114 -> 4171**.
- `verify_detail_parser_window.py --days 5 --limit-per-day 80`: режим live, **213** detail успешно; сумма покрытий полей и сегмент `is_land_plot=true` (n=114): см. вывод ниже; артефакт [data/raw/detail_parser_window_verification.json](data/raw/detail_parser_window_verification.json).

**Сводка verify (поля, сумма по окну):** cadastral_number 136, area_sqm 165, land_category 213, permitted_use 119, address 211, lot_name 213, start_price 141.

**Сегмент is_land_plot=true (n=114):** cadastral 81, area_sqm 114, permitted_use 113, start_price 42.

**Затронутые файлы:**
- backend/scripts/repair_poisoned_ingest_manifests.py
- WORKLOG.md

**Проверки:**
- API: `GET /api/ingest-runs?limit=3`, `GET /api/lots?limit=5`
- `python scripts/verify_detail_parser_window.py --days 5 --limit-per-day 80`

**Следующее:**
- когда Торги опубликуют срез `20260504…20260505`, повторить ingest или дождаться планового job; при необходимости снова `repair_poisoned_ingest_manifests.py`, если манифест снова «залипнет» на error-теле.

---

## 2026-05-05 - Ingest: операционный план без «прогона с 2022», error-JSON Торгов, noop, repair-скрипт

**Что сделано:**
- [backend/app/services/ingest/discovery.py](backend/app/services/ingest/discovery.py): в режиме `operational` план ограничен окном watermark (синтетические суточные URL от шаблата реестра), без слияния со всеми историческими `data-*.json` из `list.json` (раньше сортировка шла с 2022 года и каждый тик тянул лишние запросы).
- [backend/app/services/ingest/service.py](backend/app/services/ingest/service.py): ответ `{"error": "..."}` от Торгов (HTTP 200, срез ещё не готов) больше не считается успешным dataset; статус запуска `noop`, если все файлы уже в манифесте; сообщение для UI при `noop`.
- [backend/app/main.py](backend/app/main.py): при старте закрытие «зависших» `IngestRun` в `running` старше 6 ч (помечаются `failed` с пояснением).
- [backend/scripts/repair_poisoned_ingest_manifests.py](backend/scripts/repair_poisoned_ingest_manifests.py): удаление из `ingest_manifest` строк `processed` + `records_count=0`, если по URL сейчас отдаётся error-envelope Торгов.
- [frontend/src/components/StatusBadge.tsx](frontend/src/components/StatusBadge.tsx): бейдж для статуса `noop`.
- Тесты: `test_ingest_service.py` (error envelope), правки ожиданий в `test_ingest_discovery.py`.

**Затронутые файлы:**
- backend/app/services/ingest/discovery.py, service.py
- backend/app/main.py
- backend/scripts/repair_poisoned_ingest_manifests.py (новый)
- backend/tests/test_ingest_service.py, test_ingest_discovery.py
- frontend/src/components/StatusBadge.tsx
- AGENTS.md, WORKLOG.md

**Проверки:**
- `pytest` в `backend/`: 45 passed
- `npx tsc --noEmit` в `frontend/`

**Следующее:**
- при необходимости вручную удалить остальные подозрительные `ingest_manifest` с `records_count=0`, если срез уже опубликован, а манифест мешает (скрипт удаляет только error-envelope).

---

## 2026-05-05 - Фильтры: мультивыбор во всплывающей панели (чекбоксы + Применить)

**Что сделано:**
- [frontend/src/components/FacetMultiPicker.tsx](frontend/src/components/FacetMultiPicker.tsx): кнопка-сводка, панель с чекбоксами по фасетам, «Очистить» / «Отмена» / «Применить»; черновик до подтверждения; закрытие по клику снаружи и Escape.
- [frontend/src/pages/LotsPage.tsx](frontend/src/pages/LotsPage.tsx), [frontend/src/pages/TradesPage.tsx](frontend/src/pages/TradesPage.tsx): мультивыбор категорий / типа документа / вида торгов через этот компонент вместо `<select multiple>` и сетки чекбоксов.
- [frontend/src/facetFilterUi.ts](frontend/src/facetFilterUi.ts): удалены неиспользуемые порог listbox и `valuesFromMultiSelect`; оставлен `FACET_SINGLE_SELECT_MAX` для регион/статус на лотах.
- [frontend/src/styles.css](frontend/src/styles.css): стили `.facet-picker*`, `.button--compact`; [AGENTS.md](AGENTS.md) — описание UI.

**Затронутые файлы:**
- frontend/src/components/FacetMultiPicker.tsx (новый)
- frontend/src/pages/LotsPage.tsx, frontend/src/pages/TradesPage.tsx, frontend/src/facetFilterUi.ts, frontend/src/styles.css
- AGENTS.md, WORKLOG.md

**Проверки:**
- `npx tsc --noEmit` в `frontend/`

**Следующее:**
- при необходимости — перенос фокуса в панель при открытии (a11y).

---

## 2026-05-05 - Фильтры: выпадающие списки при малом числе значений фасетов

**Что сделано:**
- [frontend/src/facetFilterUi.ts](frontend/src/facetFilterUi.ts): пороги `FACET_SINGLE_SELECT_MAX` (40) и `FACET_MULTI_LISTBOX_MAX` (24), хелпер `valuesFromMultiSelect`.
- [frontend/src/pages/LotsPage.tsx](frontend/src/pages/LotsPage.tsx): при числе значений `region` / `status` в пределах порога — одиночный `<select>` с пунктом «Все»; при числе кодов вида торгов в пределах порога — `<select multiple>` вместо сетки чекбоксов, иначе прежние чекбоксы; свободный ввод региона/статуса, если фасетов много.
- [frontend/src/pages/TradesPage.tsx](frontend/src/pages/TradesPage.tsx): тип документа и вид торгов — listbox или чекбоксы по тому же порогу.
- [frontend/src/styles.css](frontend/src/styles.css): стили `select`, `.filters__select`, `.filters__field`; [AGENTS.md](AGENTS.md) — описание UI.

**Затронутые файлы:**
- frontend/src/facetFilterUi.ts (новый)
- frontend/src/pages/LotsPage.tsx, frontend/src/pages/TradesPage.tsx, frontend/src/styles.css
- AGENTS.md, WORKLOG.md

**Проверки:**
- `npx tsc --noEmit` в `frontend/`

**Следующее:**
- при желании — вынести пороги в env или подобрать по реальной БД.

---

## 2026-05-05 - Фильтры: фасеты, мультивыбор видов торгов, reg_num как текст

**Что сделано:**
- Backend: `GET /api/lots/facets` и `GET /api/opendata-notices/facets` (distinct поля для UI); `/api/lots` — фильтр `category` списком (повторяющийся query); `/api/opendata-notices` — `document_type` и `bidd_type_code` списками; схемы `LotFacets`, `OpenDataNoticeFacets`; тесты в [backend/tests/test_api.py](backend/tests/test_api.py) (44 passed).
- Frontend: `request()` с `append` для массивов query; [frontend/src/pages/LotsPage.tsx](frontend/src/pages/LotsPage.tsx) — чекбоксы вида торгов по фасетам, deep-link `category=` повторяющимся параметром; [frontend/src/pages/TradesPage.tsx](frontend/src/pages/TradesPage.tsx) — мультивыбор типа документа и вида торгов; стили `.filters__facet-*` в [frontend/src/styles.css](frontend/src/styles.css).
- Реестровый номер: не выпадающий список, а **текстовое поле** точного совпадения с API `reg_num` (поле и `fetchNotices.regNum` на странице извещений).

**Затронутые файлы:**
- backend/app/api.py, backend/app/schemas.py, backend/tests/test_api.py
- frontend/src/api.ts, frontend/src/types.ts, frontend/src/pages/LotsPage.tsx, frontend/src/pages/TradesPage.tsx, frontend/src/styles.css
- AGENTS.md
- WORKLOG.md

**Проверки:**
- `pytest` в `backend/` (44 passed)
- `npx tsc --noEmit` в `frontend/`

**Следующее:**
- при необходимости — частичное совпадение `reg_num` на стороне API (сейчас только точное равенство).

---

## 2026-05-04 - Парсер: characteristic площадь/цена, верификация, майнинг пропусков

**Что сделано:**
- Бейзлайн: `pytest` 37 passed; `verify_detail_parser_window.py --reanalyze-existing --days 5` — сумма по `is_land_plot=true` (n=160): cadastral=112, area_sqm=107, permitted_use=159, start_price=62 (старые `parsed` в отчётах, без перефетча detail).
- Майнинг по `detail_parser_verification_202604*.json`: у земельных лотов без `start_price` в JSON нет полей `startPrice`/`priceMin`/аналогов (0 «восстановимых» через новые ключи); низкая доля `start_price` на сегменте земли в основном из-за форм извещений без цены (ИПС и т.п.). Площадь: в выборке встречаются characteristic-коды `SquareZU_project`, `totalAreaRealty` (раньше не участвовали в `_find_characteristic_number`).
- Доработка [backend/app/services/ingest/detail_parser.py](backend/app/services/ingest/detail_parser.py): коды площади `SquareZU_project`, `totalAreaRealty`; извлечение цены — characteristic `StartPrice`/`InitialPrice`/`MinLotPrice`/`MinPrice`/`AuctionStartPrice`, затем fallback по полям `priceMinVAT`, `minPriceVAT`.
- Тесты +5 в [backend/tests/test_detail_parser.py](backend/tests/test_detail_parser.py) (всего 22 в модуле; полный прогон 42).
- Свежие данные: `fetch_latest_opendata.py` -> `data-20260503T0000-20260504T0000-structure-20240401.json`; точечная верификация `verify_detail_parser_real.py --data-file ... --limit 45` -> [data/raw/detail_parser_verification_20260504_refresh.json](data/raw/detail_parser_verification_20260504_refresh.json): `is_land_plot=true` n=10, area_sqm=10/10, start_price=5/10, cadastral=7/10 (малый n, только для smoke после изменений).

**Затронутые файлы:**
- backend/app/services/ingest/detail_parser.py
- backend/tests/test_detail_parser.py
- AGENTS.md (число тестов)
- WORKLOG.md
- data/raw/detail_parser_verification_20260504_refresh.json (новый отчёт)
- data/raw/latest_opendata_meta.json, data/raw/data-20260503T0000-20260504T0000-structure-20240401.json (fetch_latest)

**Проверки:**
- `.venv312\Scripts\python.exe -m pytest -q`: 42 passed
- `verify_detail_parser_window.py --reanalyze-existing --days 5` (бейзлайн сумм)
- `verify_detail_parser_real.py --data-file ... --limit 45` (после правок парсера)

**Следующее:**
- При полном окне: `verify_detail_parser_window.py --days 10 --limit-per-day 80` на свежих днях и сравнение сегмента `is_land_plot=true` с офлайн-сводкой 2026-05-04.
- Текстовый fallback цены по описанию — только после появления реальных counterexamples в выборке (в текущем корпусе 0 совпадений по regex).

---

## 2026-05-04 - Синхронизация с Git: коммит рабочей ветки + игнор data/*.db

**Что сделано:**
- Рабочее дерево закоммичено и отправлено в `origin` (ветка `chore/frontend-vite-security-from-clean`).
- В [.gitignore](.gitignore) правило `data/app.db` заменено на `data/*.db`, чтобы не попадали в репозиторий локальные SQLite-файлы в `data/` (включая `migration_check.db`).

**Затронутые файлы:**
- .gitignore
- WORKLOG.md

**Проверки:**
- только `git add` / `git commit` / `git push` (тесты не гонялись).

**Следующее:**
- при необходимости merge ветки в `main` на GitHub.

---

## 2026-05-04 - Сегментированная coverage-метрика, текстовый fallback парсера, ретрай и связь lots ↔ opendata_notices

**Что сделано:**

Этап 1 - честная сегментированная метрика coverage (офлайн):
- В [backend/scripts/verify_detail_parser_real.py](backend/scripts/verify_detail_parser_real.py) добавлены флаги `--data-file PATH` (читать data-*.json локально, без сети), `--reanalyze REPORT_PATH` (пересчитать coverage из существующего отчёта), `--retries N` (per-href retry). В отчёт добавлена секция `segmented_coverage` с разрезом по `is_land_plot`, по `land_category` и по `lot_name`.
- В [backend/scripts/verify_detail_parser_window.py](backend/scripts/verify_detail_parser_window.py) добавлены флаги `--from-local-files` (брать data-*.json из tmp-dir) и `--reanalyze-existing` (пересобрать сводку из имеющихся detail_parser_verification_*.json без сети). Сводка теперь хранит `segmented_is_land_plot`, `segmented_by_land_category`, `segmented_by_lot_name`.
- Прогон `python scripts/verify_detail_parser_window.py --reanalyze-existing --days 5` дал очень показательный результат: на сегменте `is_land_plot=true` (160 notice) `permitted_use` 99.4%, `area_sqm` 67%, `cadastral_number` 70%; плоские 38%/56%/58% обманывают, потому что в выборке 135 не-земельных лотов (концессии, здания, нежилые, водопользование) - у них этих полей и не должно быть. Отчёт в [data/raw/detail_parser_window_verification_offline.json](data/raw/detail_parser_window_verification_offline.json).

Этап 2 - доработка detail_parser:
- В [backend/app/services/ingest/detail_parser.py](backend/app/services/ingest/detail_parser.py) добавлены: ослабленный `CADASTRAL_RE` (допускает пробелы вокруг `:` и нормализует их в результате), универсальный helper `_parse_area_with_units(text)` с конверсией кв.м/м²/га/гектары/сотки в кв.м, fallback `_find_area_in_text` по полям `lotDescription`/`lotName`/`noticeName`/`description`, fallback `_find_permitted_use_in_text` по списку маркеров (ИЖС, ЛПХ, КФХ, садоводство, огородничество, дачное строительство), и доп. поиск кадастра по characteristic-коду `CadastralNumber`/`cadastralNumber`/`kadastrNumber`/`estateCadastralNumber`.
- В [backend/tests/test_detail_parser.py](backend/tests/test_detail_parser.py) +8 новых кейсов: `_parse_area_with_units` для м²/тысячного разделителя/гектаров/соток/мусора, fallback на текстовую площадь и ВРИ, кадастр с пробелами внутри, кадастр только через characteristic. Итого 17 тестов парсера.

Этап 3 - retry на единичные сетевые сбои:
- В [backend/app/services/ingest/service.py](backend/app/services/ingest/service.py) добавлена функция `_fetch_detail_with_retry(detail_url)` - один retry с backoff 1.5s через `asyncio.sleep` (`Server disconnected without sending a response` лечится). Используется и в `_maybe_enrich_with_detail`, и в [verify_detail_parser_real.py](backend/scripts/verify_detail_parser_real.py) (`_fetch_detail_with_retry` локально).
- В [backend/tests/test_ingest_service.py](backend/tests/test_ingest_service.py) добавлен `test_run_ingest_retries_failed_detail_fetch_once`: первый detail-вызов кидает, второй возвращает payload, лот сохраняется с обогащением, фактически зафиксирован 2-й вызов.

Этап 4 - офлайн-репроцессинг существующих лотов:
- Новый скрипт [backend/scripts/reprocess_lots_offline.py](backend/scripts/reprocess_lots_offline.py): берёт каждый Lot, читает последний LotSnapshot.payload, пересчитывает `is_izhs_candidate` через `match_izhs(...)` с актуальным `IZHS_KEYWORDS`, дополнительно пытается достать кадастровый номер regex'ом из payload для лотов, где `cadastral_number IS NULL`. Поддерживает `--dry-run` и `--limit`. Отчёт пишется в [data/raw/reprocess_lots_offline_report.json](data/raw/reprocess_lots_offline_report.json).
- Прогон на текущей БД: 4114 лотов (в плане спринта стояла устаревшая цифра 1173 - дельта от автостарта ingest при запусках backend между моментом написания плана и реализации, не баг), was_izhs=52 → now_izhs=39 (`flipped_true=38`, `flipped_false=51` - переоценка по уточнённым keywords). Кадастр: уже_задан=109, добавили_сейчас=0, ещё_не_найдено=4005 (ожидаемо - кадастр живёт в notice detail, не в opendata-индексе; будет заполнен на следующем live ingest).
- Скрипт сознательно НЕ обновляет `area_sqm`/`permitted_use`/`land_category` из `LotSnapshot.payload`: это opendata-индекс (карточка списка), там этих полей в подавляющем большинстве случаев физически нет, прогонять `parse_notice_detail` бессмысленно. Реальный backfill этих полей произойдёт через `_maybe_enrich_with_detail` на свежем live-ingest пути после VPN-off.

Этап 5 - объединение `lots` ↔ `opendata_notices`:
- В [backend/app/models.py](backend/app/models.py) у `Lot` добавлено поле `opendata_notice_id: ForeignKey("opendata_notices.id")` (nullable, indexed) + relationship `opendata_notice`.
- Alembic-ревизия [backend/alembic/versions/20260504_05_link_lot_to_opendata_notice.py](backend/alembic/versions/20260504_05_link_lot_to_opendata_notice.py) - добавляет колонку, индекс и FK с `ON DELETE SET NULL`.
- В dev SQLite применён `python scripts/dev_sync_schema.py` - добавлена колонка `opendata_notice_id INTEGER`. Внимание: SQLite не поддерживает `ALTER TABLE ADD CONSTRAINT`, поэтому в текущем `data/app.db` колонка существует **без FK-ограничения**. В Alembic-ревизии FK прописан корректно и применится при первом `alembic upgrade head` на свежем PostgreSQL. Для dev это норма (FK там не используется ORM).
- В [backend/app/services/ingest/service.py](backend/app/services/ingest/service.py) появились `_is_opendata_form(item)`, `_structure_version_from_url(url)`, `_parse_opendata_publish_date`, `_upsert_opendata_notice(db, item, structure_version)`. Внутри `run_ingest()` после region-фильтра вызывается upsert OpenDataNotice (по `href` уникальный) и его id передаётся в `_upsert_lot(..., opendata_notice_id=...)`. Лот теперь живёт в одной транзакции с raw-извещением.
- В [backend/tests/test_ingest_service.py](backend/tests/test_ingest_service.py) добавлен `test_run_ingest_links_lot_to_opendata_notice` (создание notice + лота с FK, повторный run остаётся идемпотентным).

Этап 6 - API и фронт:
- Pydantic-схема `LotDetail` ([backend/app/schemas.py](backend/app/schemas.py)) расширена `opendata_notice_id` и `notice_payload: dict | None`.
- `/api/lots/{id}` ([backend/app/api.py](backend/app/api.py)) при наличии `opendata_notice_id` подгружает `OpenDataNotice.payload` и возвращает в ответе.
- В [backend/tests/test_api.py](backend/tests/test_api.py) добавлены `test_lot_detail_returns_notice_payload_when_linked` и `test_lot_detail_returns_null_notice_payload_when_not_linked`.
- На фронте [frontend/src/types.ts](frontend/src/types.ts) расширен `LotDetail` (новые поля), а в [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx) появился collapsible-блок «Сырое извещение (opendata)» с `<details>/<summary>` и форматированным JSON. Стили `.raw-notice`/`.raw-notice__pre` добавлены в [frontend/src/styles.css](frontend/src/styles.css).
- На текущей dev-БД блок «Сырое извещение» **появляется только у 1173 из 4114 лотов** (28%) - тех, что слинкованы скриптом из Этапа 7. Остальные лоты исторические, у них `opendata_notice_id IS NULL` и блок просто скрывается. После одного-двух live-ingest проходов на свежих данных доля слинкованных будет расти автоматически - `run_ingest()` теперь пишет обе таблицы в одной транзакции.

Этап 7 - линковка существующих лотов:
- Новый скрипт [backend/scripts/link_lots_to_notices.py](backend/scripts/link_lots_to_notices.py): для каждого `Lot.opendata_notice_id IS NULL` ищет `OpenDataNotice` по `Lot.source_url == OpenDataNotice.href` (точно), fallback - по `Lot.source_id == OpenDataNotice.reg_num`. Отчёт в [data/raw/link_lots_to_notices_report.json](data/raw/link_lots_to_notices_report.json).
- Прогон: всего лотов 4114, всего notices 1214, слинковано 1173 (через href 1155 + через reg_num 18), 41 notice без лота (ожидаемо - заливались только через `import_opendata_to_db.py`), 2941 лот без notice (ожидаемо - они от старых ingest-проходов до того, как opendata_notices существовала).

**Затронутые файлы:**
- backend/app/models.py
- backend/app/schemas.py
- backend/app/api.py
- backend/app/services/ingest/service.py
- backend/app/services/ingest/detail_parser.py
- backend/alembic/versions/20260504_05_link_lot_to_opendata_notice.py (новый)
- backend/scripts/verify_detail_parser_real.py
- backend/scripts/verify_detail_parser_window.py
- backend/scripts/reprocess_lots_offline.py (новый)
- backend/scripts/link_lots_to_notices.py (новый)
- backend/tests/test_detail_parser.py
- backend/tests/test_ingest_service.py
- backend/tests/test_api.py
- frontend/src/types.ts
- frontend/src/pages/LotDetailPage.tsx
- frontend/src/styles.css

**Проверки:**
- `python -m pytest -v`: 37 passed (было 24, +13 новых тестов: 8 detail_parser, 2 ingest_service - retry и notice-link, 2 api - notice_payload, 1 косвенный за счёт обновлённого fixture).
- `npx tsc --noEmit`: чисто.
- `npm run build`: проходит за 2.6 с (1.23 МБ бандл, ожидаемо из-за maplibre).
- `python scripts/verify_detail_parser_window.py --reanalyze-existing --days 5`: processed=5/5, на сегменте `is_land_plot=true` (160 notice) coverage `permitted_use` = 99.4%, `area_sqm` = 67%, `cadastral_number` = 70%, `start_price` = 38.8%.
- `python scripts/reprocess_lots_offline.py`: 4114 лотов обработано, IZHS-классификация переоценена.
- `python scripts/link_lots_to_notices.py`: 1173 лота слинкованы с notices.
- `python scripts/dev_sync_schema.py`: добавлена колонка `lots.opendata_notice_id`.

**Известные проблемы / TODO:**
- Сегментированная метрика на `is_land_plot=false` не репрезентативна для нашей цели (мы про землю). Это нормально и by-design.
- Текстовый fallback по `area_sqm` подтверждён только на синтетических кейсах в тестах. Реальный замер выигрыша coverage возможен только при VPN-off (полный реальный verifier window).
- 2941 существующих лота не слинкованы с notices. Это исторические записи до того, как opendata_notices писались в общем потоке. После одного-двух свежих live-ingest проходов разрыв выровняется автоматически, потому что `run_ingest()` теперь пишет обе таблицы вместе.
- В `IZHS_KEYWORDS` есть подстрока `2.1` (классификатор ВРИ): из-за неё `match_izhs` срабатывает на любой токен «2.1» в произвольном тексте payload (например, «п. 2.1 регламента»). Это объясняет высокий `flipped_false=51` в Этапе 4: старая (более снисходительная) классификация ловила больше ложноположительных, и они теперь правильно сняты. Чистка детектора планируется через интеграцию НСПД (точный VRI-код участка), пункт 1 roadmap.
- В dev-SQLite колонка `lots.opendata_notice_id` добавлена через `dev_sync_schema.py` без FK-ограничения (SQLite не поддерживает `ALTER TABLE ADD FOREIGN KEY`). В Alembic-ревизии FK есть, на свежем PostgreSQL он применится корректно. Для текущего dev-режима ORM-целостность достаточна.
- Перед массовыми операциями (Этапы 4 и 7) бэкап `data/app.db` не делался. Откат возможен через `alembic downgrade 20260430_04` или ручной reset колонки + повторный `link_lots_to_notices.py`. Для будущих больших миграций рекомендуется `cp data/app.db data/app.db.bak` перед прогоном.
- Бандл фронта 1.23 МБ - известная проблема (maplibre), code-splitting `MapPage` остаётся в roadmap.

**Следующее (когда VPN выключится):**
1. `python scripts/fetch_latest_opendata.py --output-dir ../data/raw` - свежий day-файл.
2. `python scripts/verify_detail_parser_window.py --days 10 --limit-per-day 80` - честно замерить, что новые fallback'и (текстовая площадь, ВРИ из текста, кадастр через characteristic) подняли coverage `is_land_plot=true` сегмента.
3. Включить `INGEST_FETCH_NOTICE_DETAILS=true`, прогнать backfill - он подтянет cadastral_number / area_sqm / permitted_use на 4005 лотов, у которых их сейчас нет, и одновременно зальёт OpenDataNotice + слинкует через FK.

**Следующее (по бизнес-roadmap):**
1. Скоринг v0 без рынка (₽/сотка по региону, дисконт к медиане, сортировка `/api/lots?sort=score`).
2. НСПД-клиент (требует сети к `nspd.gov.ru`).
3. Циан/Авито/Домклик как источники market comparables.

---

## 2026-04-30 - Расширенная верификация detail_parser (окно 5 дней)

**Что сделано:**
- Расширен [backend/scripts/verify_detail_parser_real.py](backend/scripts/verify_detail_parser_real.py): добавлен параметр `--data-url` для запуска верификации на конкретном дневном dataset без привязки к `latest_opendata_meta.json`.
- Добавлен пакетный скрипт [backend/scripts/verify_detail_parser_window.py](backend/scripts/verify_detail_parser_window.py), который:
  - берёт базовый шаблон из `latest_opendata_meta.json`,
  - строит `data-YYYYMMDDT0000-YYYYMMDDT0000-structure-*.json` для окна дат,
  - запускает `verify_detail_parser_real.py` по каждому дню,
  - агрегирует итоги и сохраняет сводку в `data/raw/detail_parser_window_verification.json`.
- Выполнен прогон по окну 5 дней (`2026-04-25`..`2026-04-29`) с лимитом `80 notice/day`.
- Обновлён [AGENTS.md](AGENTS.md): добавлен новый скрипт пакетной верификации в структуру проекта.

**Затронутые файлы:**
- backend/scripts/verify_detail_parser_real.py
- backend/scripts/verify_detail_parser_window.py (новый)
- AGENTS.md

**Проверки:**
- `python scripts/verify_detail_parser_window.py --days 5 --limit-per-day 80` - успешно.
- Итог окна: `processed_days=5/5`, `fetched=295`, `successful=294`, `failed=1` (один сетевой сбой: `Server disconnected without sending a response`).
- Суммарный coverage по 295 notice:
  - `land_category`: 294/295 (99.7%)
  - `lot_name`: 294/295 (99.7%)
  - `address`: 291/295 (98.6%)
  - `start_price`: 196/295 (66.4%)
  - `cadastral_number`: 171/295 (58.0%)
  - `permitted_use`: 164/295 (55.6%)
  - `area_sqm`: 112/295 (38.0%)

**Известные проблемы / TODO:**
- Неполное покрытие `area_sqm`/`permitted_use`/`cadastral_number` связано с вариативностью заполнения полей в notice, а не только с алиасами.
- Для устойчивой статистики стоит добавить повторный ретрай именно для failed detail-fetch в verifier (сейчас 1 сетевой сбой сразу идёт в failed).

**Следующее:**
1. Прогнать окно 10-14 дней и сравнить стабильность coverage по полям.
2. Добавить в `verify_detail_parser_real.py` опциональный retry для единичных failed detail запросов.

---

## 2026-04-30 - Верификация detail_parser на реальных notice (малый объём)

**Что сделано:**
- Выполнена реальная верификация парсера на `torgi.gov.ru`: скачан свежий `data-*.json` и собрана выборка `documentType=notice` (`/docs/notice_...`), чтобы не смешивать с `clarifications`.
- Добавлен скрипт [backend/scripts/verify_detail_parser_real.py](backend/scripts/verify_detail_parser_real.py): читает `data_url` из `data/raw/latest_opendata_meta.json`, берет N реальных `href`, парсит через `parse_notice_detail`, считает coverage по ключевым полям и пишет отчёт в JSON.
- По результатам реальных payload (schema 5.1) доработан [backend/app/services/ingest/detail_parser.py](backend/app/services/ingest/detail_parser.py):
  - `start_price`: добавлен alias `priceMin`;
  - `area_sqm`: добавлен разбор `characteristics` по коду `SquareZU`;
  - `permitted_use`: добавлен разбор `characteristics` по коду `PermittedUse`;
  - добавлены хелперы для извлечения `characteristicValue` из `str/dict/list`.
- Добавлен тест `test_parse_notice_detail_supports_real_schema_characteristics` в [backend/tests/test_detail_parser.py](backend/tests/test_detail_parser.py) с формой `exportObject -> structuredObject -> notice -> lots`.
- Обновлён [AGENTS.md](AGENTS.md): добавлен новый скрипт в структуру, статус и roadmap скорректированы с учётом закрытия исходного блокера.

**Затронутые файлы:**
- backend/app/services/ingest/detail_parser.py
- backend/tests/test_detail_parser.py
- backend/scripts/verify_detail_parser_real.py (новый)
- AGENTS.md

**Проверки:**
- `python scripts/fetch_latest_opendata.py --output-dir ../data/raw` - успешно.
- `python scripts/verify_detail_parser_real.py --limit 12 --sample-output ../data/raw/detail_parser_sample_notice.json` - успешно.
- Coverage до фикса: `cadastral=10, area=0, land_category=12, permitted_use=0, address=12, lot_name=12, start_price=0` (12/12).
- Coverage после фикса: `cadastral=10, area=5, land_category=12, permitted_use=5, address=12, lot_name=12, start_price=10` (12/12).
- `python -m pytest tests/test_detail_parser.py` - 9 passed.

**Известные проблемы / TODO:**
- На малой выборке `notice` покрытие `area_sqm` и `permitted_use` не 100%: часть извещений не содержит эти поля в явном структурированном виде.
- Для более репрезентативной оценки нужно прогнать verifier на расширенном окне (несколько дней backfill) и сохранить динамику coverage.

**Следующее:**
1. Прогнать `verify_detail_parser_real.py` на расширенной выборке (например, 100-300 notice за несколько дат).
2. При необходимости дополнить алиасы/коды характеристик под редкие схемы.

---

## 2026-04-30 - Тюмень + ИЖС: фильтр, кадастровые поля, defensive detail parser

**Что сделано:**
- Уточнили целевое видение продукта: мониторинг ИЖС-аукционов в Тюмени/области с оценкой и скорингом. Соответствующий раздел в [AGENTS.md](AGENTS.md) обновлён, roadmap пересобран.
- Расширена модель `Lot` ([backend/app/models.py](backend/app/models.py)) семью полями: `cadastral_number`, `area_sqm`, `land_category`, `permitted_use`, `address`, `notice_detail_url`, `is_izhs_candidate`. Индексы на cadastral_number и is_izhs_candidate.
- Alembic-ревизия [backend/alembic/versions/20260430_04_extend_lot_with_land_fields.py](backend/alembic/versions/20260430_04_extend_lot_with_land_fields.py) - для будущего PG.
- Новый dev-скрипт [backend/scripts/dev_sync_schema.py](backend/scripts/dev_sync_schema.py), который через `inspect()` находит недостающие колонки в существующей SQLite и применяет `ALTER TABLE ADD COLUMN`. Выполнен на текущей `data/app.db` - все 7 колонок добавлены без потери данных.
- Конфиг ([backend/app/config.py](backend/app/config.py)) и [.env.example](.env.example) расширены: `TARGET_REGION_CODES`, `IZHS_KEYWORDS`, `INGEST_FETCH_NOTICE_DETAILS`, `INGEST_DETAIL_MAX_PER_RUN`.
- Новый модуль [backend/app/services/ingest/detail_parser.py](backend/app/services/ingest/detail_parser.py): рекурсивный walk JSON-дерева, кадастровый номер по regex `\d{1,2}:\d{1,2}:\d{6,7}:\d+`, поля по списку алиасов (с fallback'ами), `match_izhs()` через case-insensitive substring match по нормализованному NFC.
- `run_ingest()` ([backend/app/services/ingest/service.py](backend/app/services/ingest/service.py)): добавлен `_passes_region_filter`, `_maybe_enrich_with_detail` (один HTTP запрос на лот, лимит per-run, graceful skip при 4xx/5xx), сохранение всех новых полей в `Lot` через `_upsert_lot`.
- API: расширен `/api/lots` фильтрами `is_izhs / min_area / max_area / max_start_price / cadastral_number` ([backend/app/api.py](backend/app/api.py)), схемы `LotListItem`/`LotDetail` дополнены ([backend/app/schemas.py](backend/app/schemas.py)).
- Frontend: типы и `fetchLots` обновлены ([frontend/src/types.ts](frontend/src/types.ts), [frontend/src/api.ts](frontend/src/api.ts)). `LotsPage` ([frontend/src/pages/LotsPage.tsx](frontend/src/pages/LotsPage.tsx)) переписан с расширенными фильтрами и deep-link через `useSearchParams`. `LotsTable` показывает площадь, кадастр, ИЖС-бейдж. `LotDetailPage` получил блок «Кадастр и земля» со ссылкой на Публичную кадастровую карту Росреестра.
- Стили: добавлены `.filters--grid`, `.checkbox`, `.cell--mono` в [frontend/src/styles.css](frontend/src/styles.css).

**Затронутые файлы:**
- backend/app/models.py
- backend/app/config.py
- backend/app/api.py
- backend/app/schemas.py
- backend/app/services/ingest/service.py
- backend/app/services/ingest/detail_parser.py (новый)
- backend/alembic/versions/20260430_04_extend_lot_with_land_fields.py (новый)
- backend/scripts/dev_sync_schema.py (новый)
- backend/tests/test_detail_parser.py (новый)
- backend/tests/test_ingest_service.py (новый кейс с region+detail)
- backend/tests/test_api.py (новый кейс с фильтрами)
- frontend/src/types.ts, api.ts, styles.css
- frontend/src/components/LotsTable.tsx
- frontend/src/pages/LotsPage.tsx, LotDetailPage.tsx
- .env.example
- AGENTS.md (бизнес-цель, источники, архитектура, статус, roadmap)

**Проверки:**
- pytest: 24 passed (8 новых: 7 detail_parser + 1 ingest_service + 1 api).
- npx tsc --noEmit: чисто.
- npm run build: проходит (1.23 MB бандл, ожидаемо из-за maplibre).
- dev_sync_schema на data/app.db: 7 ALTER TABLE применены успешно, существующие 1173 лота сохранены.

**Известные проблемы / TODO:**
- **БЛОКЕР: detail_parser написан без verified sample**. Сеть до torgi.gov.ru недоступна с этой машины (включён VPN). Парсер построен на алиасах поля по публикациям Росреестра/контур.реестро. Когда VPN будет выключен - запустить ingest с реальным `INGEST_FETCH_NOTICE_DETAILS=true`, посмотреть, что попало в `cadastral_number`/`area_sqm`/`permitted_use`. При расхождениях - подправить алиасы в [backend/app/services/ingest/detail_parser.py](backend/app/services/ingest/detail_parser.py).
- ИЖС-детектор по keywords даст ложные срабатывания (например, упоминание «не для ИЖС» в описании). Чистка - после интеграции НСПД через ВРИ-код `2.1`.
- Существующие в БД 1173 лота имеют пустые новые поля. Они заполнятся при следующем ingest-проходе.
- Detail-fetch добавляет 1 HTTP запрос на каждый лот, прошедший region-фильтр. Защита через `INGEST_DETAIL_MAX_PER_RUN=200`.

**Следующее (по roadmap из AGENTS.md):**
1. Верификация парсера на реальном notice (после VPN off).
2. Интеграция НСПД для надёжных кадастровых данных (вместо текстового парсинга).

---

## 2026-04-30 - Контекстные файлы для AI-агентов

**Что сделано:**
- Создан [AGENTS.md](AGENTS.md) - постоянный контекст: описание проекта, стек, структура репозитория, mermaid-архитектура, команды, соглашения, текущий статус, roadmap.
- Создан этот WORKLOG.md - append-only журнал с двумя начальными записями и шаблоном.
- В [README.md](README.md) добавлена строка-ссылка на AGENTS.md и WORKLOG.md.

**Затронутые файлы:**
- AGENTS.md (новый)
- WORKLOG.md (новый)
- README.md (правка хедера)

**Проверки:** -

**Известные проблемы / TODO:** -

**Следующее:** ждём следующей задачи от пользователя.

---

## 2026-04-30 - Расширение фронтенда (Dashboard, Lots, Map, IngestRuns)

**Что сделано:**
- Добавлен роутинг (`react-router-dom@^7.14.2`).
- Создан [frontend/src/App.tsx](frontend/src/App.tsx) с маршрутами `/`, `/notices`, `/lots`, `/lots/:id`, `/map`, `/ingest`.
- Создан [frontend/src/components/Layout.tsx](frontend/src/components/Layout.tsx) - sticky-шапка + навигация + `<Outlet/>`.
- Новые страницы: [DashboardPage](frontend/src/pages/DashboardPage.tsx) (3 метрики + последние извещения и лоты), [LotsPage](frontend/src/pages/LotsPage.tsx) (фильтры region/status/category), [LotDetailPage](frontend/src/pages/LotDetailPage.tsx) (карточка + мини-карта), [MapPage](frontend/src/pages/MapPage.tsx) (полноэкранная карта), [IngestRunsPage](frontend/src/pages/IngestRunsPage.tsx) (история с длительностью).
- Существующая [TradesPage](frontend/src/pages/TradesPage.tsx) переехала на `/notices`, состояния loading/empty.
- Новый компонент [StatusBadge](frontend/src/components/StatusBadge.tsx) - цветной бейдж (success/warn/error) с авто-выбором по тексту статуса.
- Новый [LotsTable](frontend/src/components/LotsTable.tsx).
- [TradesMap](frontend/src/components/TradesMap.tsx) переписан: авто-`fitBounds` для нескольких точек, `flyTo` для одной, настраиваемая высота.
- [api.ts](frontend/src/api.ts) переписан с общим хелпером `request<T>()`, добавлены `fetchLots`, `fetchLot`, `fetchMapPoints`, `fetchIngestRuns`.
- [types.ts](frontend/src/types.ts) расширен типами `Lot`, `LotDetail`, `MapPoint`, `IngestRun`.
- [styles.css](frontend/src/styles.css) переведён на CSS-переменные, добавлены классы для шапки, бейджей, карточек, дашборда, состояний loading/empty.
- Добавлен [frontend/src/vite-env.d.ts](frontend/src/vite-env.d.ts) - чтобы `import.meta.env` типизировался под Vite.

**Чистка:**
- Удалены 4 debug-блока с POST на `127.0.0.1:7470` из `frontend/src/api.ts` (leftover от прошлой debug-сессии).
- Удалён `.cursor/debug-2e5b6d.log` (18 КБ).

**Затронутые файлы:**
- frontend/package.json (+ react-router-dom)
- frontend/src/{App.tsx,main.tsx,api.ts,types.ts,styles.css,vite-env.d.ts}
- frontend/src/components/{Layout,StatusBadge,LotsTable,TradesMap,TradesTable}.tsx
- frontend/src/pages/{Dashboard,Trades,Lots,LotDetail,Map,IngestRuns}Page.tsx

**Проверки:**
- `npx tsc --noEmit` - чисто.
- `npm run build` - проходит за ~2.2 с (предупреждение про чанк maplibre >500 КБ, ожидаемо).

**Известные проблемы / TODO:**
- Бандл крупный из-за maplibre-gl - в roadmap есть code-splitting `MapPage`.
- На фронте нет тестов и error boundary.

**Следующее:** документация для агентов (этот рефакторинг и был следующим шагом).

---

## 2026-04-28 - OpenData notices ingest и идемпотентность (ретроспектива)

> Запись восстановлена из истории файлов и Alembic-миграций - подробного журнала на тот момент не велось.

**Что сделано:**
- Добавлена модель [OpenDataNotice](backend/app/models.py) и Alembic-миграция `20260428_02_add_opendata_notices`.
- Добавлен скрипт ручного импорта [backend/scripts/import_opendata_to_db.py](backend/scripts/import_opendata_to_db.py) с jsonschema-валидацией по `structure-*.json`.
- Появился REST-эндпоинт `GET /api/opendata-notices` с фильтрами `document_type`, `bidd_type_code`, `reg_num`.
- Добавлен модуль [backend/app/services/ingest/discovery.py](backend/app/services/ingest/discovery.py) с 3-уровневым discovery (registry `list.json` -> HTML-карточка -> прямой override через `INGEST_SOURCE_URL`).
- Введён режим `INGEST_MODE=backfill` и watermark по `IngestManifest.data_to`.
- Добавлена модель `IngestManifest` и миграция `20260428_03_add_ingest_manifest` - идемпотентность по `(source_url, sha256)`.
- Поддержка `SUPPORTED_STRUCTURE_VERSIONS` (по умолчанию `20240401`); файлы с другими версиями маркируются `schema_migration_required` и сохраняются в raw без обработки.
- Расширен [backend/app/services/ingest/normalizer.py](backend/app/services/ingest/normalizer.py) - распознаёт две формы payload (opendata-notice vs обычный лот).
- Добавлены тесты: `test_ingest_discovery.py`, `test_ingest_service.py`, `test_normalizer_notices.py`, обновлён `test_ingest_client.py`.

**Затронутые файлы:**
- backend/app/{models.py,api.py,schemas.py,config.py,scheduler.py}
- backend/app/services/ingest/{client.py,discovery.py,normalizer.py,service.py}
- backend/alembic/versions/20260428_02_add_opendata_notices.py
- backend/alembic/versions/20260428_03_add_ingest_manifest.py
- backend/scripts/{import_opendata_to_db.py,run_backfill_ingest.py}
- backend/tests/* (несколько новых)

**Известные проблемы / TODO:**
- Два параллельных пути загрузки: `run_ingest` пишет в `lots/organizers/lot_snapshots`, а `import_opendata_to_db.py` пишет в `opendata_notices`. Их надо объединить.
- В `data/migration_check.db` - пустой артефакт, можно игнорировать.

**Следующее:** работа с фронтом (см. запись от 2026-04-30 про расширение фронтенда).

---

## Шаблон записи (копировать сверху)

```markdown
## YYYY-MM-DD - Краткое название этапа

**Что сделано:**
- ...

**Затронутые файлы:**
- ...

**Проверки:**
- pytest: ...
- npx tsc --noEmit: ...
- vite build: ...

**Известные проблемы / TODO:**
- ...

**Следующее:**
- ...
```
