# План развития ГИС Торги Monitor

Дата ревизии: 2026-05-10.

Цель плана - довести MVP от рабочего мониторинга ГИС Торги до инструмента, который уверенно находит ИЖС-лоты, показывает качество данных, считает первичную привлекательность и отправляет только полезные алерты.

## MVP: Telegram-first продуктовый контракт

**Цель:** рабочий Telegram-first монитор, который при появлении или изменении участка быстро показывает полезную карточку: конкретный внутренний лот из извещения, кадастр, площадь, ВРИ, цену за сотку, baseline/дисконт, ссылки на монитор, ГИС Торги, НСПД-карту и поиски на рыночных площадках.

Актуальный контракт вынесен в [docs/MVP_PRODUCT_CONTRACT.md](docs/MVP_PRODUCT_CONTRACT.md). Для ГИС Торги backend отдаёт две публичные ссылки: конкретный лот `/new/public/lots/lot/{regNum}_{lotNumber}/(lotInfo:info)` и отдельное извещение `/new/public/notices/view/{regNum}`; наш монитор всё равно показывает `regNum + lotNumber`, чтобы пользователь видел привязку к исходному извещению.

**Выполнено 2026-05-10:**
- Стабильная идентичность multi-lot извещений вынесена в поля `lots.notice_reg_num`, `lots.notice_lot_number`, `lots.notice_lot_count`. Список `/api/lots` теперь строит `torgi_url` из сохранённого номера лота и не зависит от подмешивания latest snapshot payload.
- Добавлена миграция `20260510_12_lot_notice_identity_fields`, dev-sync существующей SQLite и скрипт `python scripts/backfill_lot_notice_identity.py` для догонки старых строк.

**Выполнено 2026-05-09:**
- Backend: [backend/app/services/external_lot_links.py](backend/app/services/external_lot_links.py) — генерация URL; настройки `APP_PUBLIC_BASE_URL`, `INCLUDE_MARKETPLACE_MAP_URLS`, `INCLUDE_MARKETPLACE_SEARCH_URLS`, `DOMCLICK_SEARCH_TEMPLATE` в [backend/app/config.py](backend/app/config.py); поля `app_lot_url`, `torgi_url` (конкретный лот), `torgi_notice_url` (извещение), `torgi_json_url`, `pkk_map_url`, `nspd_map_url`, `domclick_map_url`, при включённом флаге — `domclick_search_url` / `domclick_search_url_cadastral` в ответах `/api/lots` и `/api/lots/{id}`.
- Telegram: HTML-сообщения с экранированием, ссылки ГИС Торги на лот и извещение, НСПД-карта при наличии кадастра, маркетплейки с подписями; устойчивость: обрезка до `TELEGRAM_MAX_MESSAGE_LENGTH`, retry при 429, `TELEGRAM_DISABLE_WEB_PAGE_PREVIEW`, `TELEGRAM_PROXY_URL` для HTTP(S)-прокси к Bot API ([backend/app/services/alerts/service.py](backend/app/services/alerts/service.py), [backend/app/services/alerts/telegram.py](backend/app/services/alerts/telegram.py)); smoke: `python scripts/send_telegram_test.py`.
- Frontend: таблица `/lots` — даты со временем, колонка ссылок; карточка — блок «Ссылки» ([frontend/src/components/LotsTable.tsx](frontend/src/components/LotsTable.tsx), [frontend/src/pages/LotDetailPage.tsx](frontend/src/pages/LotDetailPage.tsx)).

**Разведка URL Домклик (шаблонный поиск, без API карточки):** проверять с российского IP после смены вёрстки. Текущий шаблон: `domclick.ru/search?query={q}`; переопределение через `DOMCLICK_SEARCH_TEMPLATE` в `.env`. Карта района: `search/on-map` с bbox вокруг центроида.

**Ограничение:** ссылки Домклик — шаблонный поиск по кадастру и/или адресу/региону или карта в округе, не гарантированная «цена этого участка». НСПД-ссылка ведёт на публичную карту; стабильный deep link прямо в участок не считаем частью контракта. Точная интеграция — после официальных API/скрейпинга по согласованию и/или НСПД.

## 0. Делегирование ИИ с прямым доступом к РФ-ресурсам

Этот раздел предназначен для агента/машины, где `torgi.gov.ru`, `nspd.gov.ru` и, позже, рыночные сайты доступны напрямую с российского IP. В текущей среде Codex работает через VPN, поэтому live-доступ к Торгам падает на timeout.

**Правила для внешнего агента:**
- Не редактировать `.env` с реальными секретами.
- Не делать `git commit` без отдельной команды.
- Все результаты складывать в `data/raw/` или в отдельный отчёт Markdown/JSON.
- После каждого прогона записывать точные команды, дату, число обработанных записей и ошибки.
- Если меняется код, запускать `python -m pytest`, `npx.cmd tsc --noEmit` и `npm.cmd run build`.

**Задача A. Обновить свежие OpenData-файлы Торгов**
- Команды:
  - `cd backend`
  - `python scripts/fetch_latest_opendata.py`
- Ожидаемые артефакты:
  - `data/raw/latest_opendata_meta.json`;
  - свежий `data-YYYYMMDDT0000-YYYYMMDDT0000-structure-20240401.json`;
  - `structure-20240401.json`, если он обновился.
- Вернуть сюда:
  - URL свежего `data_url`;
  - размер файла и число `listObjects`;
  - ошибку, если источник вернул `{"error": ...}` или не подготовил срез.

**Задача B. Live-верификация detail_parser на свежем окне**
- Команды:
  - `cd backend`
  - `python scripts/verify_detail_parser_window.py --days 10 --limit-per-day 80 --output ..\data\raw\detail_parser_window_live_YYYYMMDD.json`
- Ожидаемые метрики:
  - processed days;
  - total fetched / successful / failed;
  - field coverage sum;
  - segment `is_land_plot=true`: `cadastral_number`, `area_sqm`, `permitted_use`, `start_price`.
- Вернуть сюда:
  - JSON-артефакт отчёта;
  - краткую сводку coverage;
  - 5-10 примеров failed detail URL, если есть.

**Задача C. Проверить live ingest на малом лимите**
- Перед запуском убедиться, что БД тестовая/dev, а не production.
- Команды:
  - `cd backend`
  - при необходимости сначала `python scripts/repair_poisoned_ingest_manifests.py`;
  - запустить один operational ingest через существующий scheduler/service или backend UI, если он поднят.
- Вернуть сюда:
  - новый `IngestRun` id/status;
  - fetched/upserted/changed;
  - сколько файлов processed/failed;
  - текст ошибки, если Torgi вернул временную недоступность.

**Задача D. НСПД discovery**
- Цель: не писать большой клиент сразу, а выяснить устойчивый минимальный API-контракт.
- Взять 20-30 кадастровых номеров из локальной БД (`lots.cadastral_number IS NOT NULL`).
- Проверить, какие endpoint НСПД возвращают:
  - геометрию или bbox;
  - площадь;
  - ВРИ;
  - категорию земель;
  - адрес/местоположение.
- Вернуть сюда:
  - список endpoint и пример curl/httpx-запросов;
  - 3-5 обезличенных/несекретных response samples в `data/raw/nspd_samples_YYYYMMDD.json`;
  - предложения по модели `CadastralEnrichment`.

**Задача E. Рыночные аналоги: предварительная разведка**
- Начать только после НСПД discovery.
- Проверить доступность Циан/Авито/Домклик с той же машины.
- Ничего массово не парсить без понимания правил источника.
- Вернуть сюда:
  - какие источники доступны;
  - какие поля можно получить стабильно;
  - есть ли ограничения, captcha, блокировки.

## 1. Ближайшая стабилизация

Срок: 1-2 рабочих дня.

**Выполнено 2026-05-05:**
- Добавлены нижние границы `ge=1` для `limit` / `max_rows` в основных API-эндпоинтах списков и CSV.
- Исправлен reset фильтров на странице извещений: перезагрузка идет с явно пустым фильтром, без stale React state.
- Страница лотов синхронизирует пагинацию и сортировку с URL; примененное состояние восстанавливается из query string.
- Добавлены backend-тесты на невалидные лимиты, сортировку `/api/lots` по `price_per_sotka` и CSV export с несколькими `category`.
- Пройдены `python -m pytest`, `npx.cmd tsc --noEmit`, `npm.cmd run build`, `git diff HEAD --check`.

**Задачи:**
- Добавить frontend test runner и покрыть reset-фильтры на фронте.

**Критерий готовности:**
- API не принимает отрицательные лимиты.
- Фильтры и URL на страницах списков не расходятся с фактической выборкой.
- Проверки проходят локально и в CI.

## 2. Надежность текущего ingest

Срок: 3-5 рабочих дней.

**Проверено 2026-05-05:**
- Live-доступ к `torgi.gov.ru` из текущей сети не работает: `fetch_latest_opendata.py` завершился `httpx.ConnectTimeout [WinError 10060]`, а live-прогон `verify_detail_parser_window.py --days 1 --limit-per-day 5` дал `httpx.ConnectError: All connection attempts failed`.
- Офлайн-пересчёт существующих daily-отчётов выполнен: `verify_detail_parser_window.py --reanalyze-existing --days 5`.
  - processed days: 5/5;
  - total fetched/success/failed: 295 / 294 / 1;
  - field coverage sum: `cadastral_number=171`, `area_sqm=112`, `land_category=294`, `permitted_use=164`, `address=291`, `lot_name=294`, `start_price=196`;
  - segment `is_land_plot=true` (n=160): `cadastral_number=112`, `area_sqm=107`, `permitted_use=159`, `start_price=62`.
- `link_lots_to_notices.py --dry-run` не нашёл новых совпадений: 5207 lots total, 2289 already linked, 2918 still unlinked, `linked_via_href=0`, `linked_via_reg_num=0`; apply-прогон не запускался, потому что он не изменил бы БД.
- Server-side пагинация `/api/opendata-notices` выполнена: backend возвращает `{ items, total, limit, offset }`, frontend-страница Notices показывает total и переключает страницы по 50 записей.

**Выполнено 2026-05-06:**
- Улучшена наблюдаемость ingest:
  - `ingest_runs` хранит `processed_files`, `failed_files`, `last_error_source_url`, `error_kind`;
  - `ingest_manifest` хранит `error_kind` для файловых ошибок;
  - `run_ingest()` классифицирует `source_unavailable`, `schema_migration_required`, `file_processing_error`;
  - `/api/ingest-runs` возвращает новые поля;
  - UI `/ingest` показывает счётчик файлов, тип сбоя и последний URL ошибки.
- Добавлена Alembic-ревизия `20260506_06_add_ingest_observability.py`.
- Выполнен `python scripts/dev_sync_schema.py` для локальной SQLite.

**Выполнено 2026-05-07:**
- Внешняя source discovery подтвердила правильный dataset `7710568760-notice`, schema `20240401`, и достаточность OpenData index + notice detail JSON для MVP.
- Исправлены high-priority проблемы ingest по итогам разведки:
  - регион OpenData нормализуется из `subjectEstateCode`, а после detail-fetch перепроверяется через `lots[].biddingObjectInfo.subjectRF.code`;
  - ИЖС-кандидат определяется по `PermittedUse.code` whitelist `2.1/2.2/2.3/13.1/13.2` с prefix-match, keyword'и оставлены fallback'ом;
  - `clarifications` больше не создаёт пустой Lot, а `noticeCancel/noticeStop/noticeResumption/noticeAnnulment` обновляют статус существующего Lot;
  - локальный default `TARGET_REGION_CODES=72`.
- Добавлены поля `Lot.permitted_use_codes`, `Lot.municipality`, `Lot.settlement` + Alembic-ревизия `20260507_07_add_lot_municipality_fields.py`.
- Добавлен offline demo-loader `scripts/load_demo_tyumen_data.py --reset`, который загружает Тюменскую выборку из `data/raw` без сети.
- Добавлен `/api/lots/quality` для метрик качества данных Dashboard.
- Frontend получил Dashboard-метрики качества, быстрые фильтры `/lots` (`has_cadastral`, `has_price_per_sotka`, `has_positive_discount`) и базовый ErrorBoundary.
- Страница `/ingest` получила понятный статус загрузчика, расписание, следующий запуск и кнопку ручного запуска operational ingest; backend добавил `/api/ingest-status` и `POST /api/ingest-runs/start`.

**Задачи:**
- При необходимости повторить расширенную live-верификацию `detail_parser` на свежем окне данных:
  - `python scripts/verify_detail_parser_window.py --days 10 --limit-per-day 80`;
  - зафиксировать coverage по `is_land_plot=true` для `cadastral_number`, `area_sqm`, `permitted_use`, `start_price`.
- Закрыть исторический разрыв `Lot` -> `OpenDataNotice`:
  - прогнать `backend/scripts/link_lots_to_notices.py`;
  - добавить в WORKLOG фактическое число слинкованных записей.
- Расширить ФИАС-слой при необходимости до отдельного справочника муниципалитетов/населённых пунктов.

**Критерий готовности:**
- Есть измеренный baseline качества парсера на свежем окне.
- Исторические лоты максимально слинкованы с raw notices.
- Страница ingest объясняет сбои без чтения логов сервера. Выполнено локально 2026-05-06.

## 3. НСПД как надежный кадастровый слой

Срок: 1-2 недели после подтверждения сетевого доступа.

**Сделано 2026-05-09 (каркас + ingest):**
- Модуль [backend/app/services/nspd/client.py](backend/app/services/nspd/client.py): разбор ответа geoportal (`data` / `features` / …), `NspdGeoportalClient.search_by_cadastral` при `NSPD_ENABLED=true`.
- [backend/app/services/nspd/enrich.py](backend/app/services/nspd/enrich.py): поля `properties.options` (площадь, адрес, стоимость), центроид полигона EPSG:3857; после upsert лота в [ingest/service.py](backend/app/services/ingest/service.py) при наличии кадастра (лимит `NSPD_MAX_PER_RUN`, кеш `NSPD_REFRESH_AFTER_DAYS`).
- Колонки `lots.nspd_*`, Alembic `20260509_09_add_lot_nspd_fields.py`; карточка лота в UI — блок «НСПД».
- Настройки в [backend/app/config.py](backend/app/config.py) и [.env.example](.env.example).
- Политика слияния НСПД в `Lot.area_sqm` / `Lot.address`: `NSPD_MERGE_AREA_POLICY`, `NSPD_MERGE_ADDRESS_POLICY` (`notice_only` по умолчанию).
- Ручной догон существующих лотов: `python scripts/enrich_lots_nspd.py --region 72 --limit 50 --force`, отчёт `data/raw/nspd_enrich_report.json`.
- Dev-флаг `NSPD_VERIFY_TLS=false` для локальной split-tunnel среды, где `nspd.gov.ru` отдаёт self-signed chain; production default остаётся `true`.

**Задачи:**
- Исследовать доступные endpoints НСПД и ограничения запросов.
- Спроектировать минимальную модель кадастрового обогащения:
  - кадастровый номер;
  - геометрия или bbox;
  - точная площадь;
  - ВРИ;
  - категория земель;
  - адрес или местоположение;
  - дата последней проверки.
- Добавить сервис `nspd` с кешированием и retry/backoff.
- Подключить обогащение к ingest и офлайн-репроцессингу.
- Показать на карточке лота источник каждого кадастрового поля: detail JSON, НСПД, fallback text.

**Критерий готовности:**
- Для лотов с кадастровым номером можно восстановить точную площадь и ВРИ из НСПД или явно показать, почему это не удалось.
- Текстовый `detail_parser` остается fallback, а не единственным источником истины.

## 4. Первичная оценка без внешних маркетплейсов

Срок: 1 неделя.

**Выполнено 2026-05-06:**
- Добавлен внутренний baseline по уже загруженным торгам без новой таблицы:
  - медиана `start_price_per_sotka` считается на лету по каскаду `region+category -> region -> category -> global`;
  - для каждого лота возвращаются `baseline_price_per_sotka`, `discount_to_baseline`, `valuation_confidence`, `valuation_baseline_scope`, `valuation_baseline_sample_size`, `valuation_reason`;
  - добавлена сортировка `/api/lots?sort=discount_to_baseline_desc`;
  - CSV export получил baseline-колонки;
  - Dashboard показывает shortlist ИЖС-кандидатов по дисконту.

**Задачи:**
- Уточнить baseline после появления НСПД/геометрии и большего числа качественных данных по целевым регионам.
- Позже, если расчёт станет тяжелым, заменить on-the-fly baseline на таблицу или материализуемый расчёт `ValuationBaseline`.
- Добавить фильтр по минимальному дисконту, если он понадобится для рабочих сценариев.

**Критерий готовности:**
- Даже без Циан/Авито система умеет ранжировать лоты относительно собственной базы торгов. Выполнено 2026-05-06.
- Пользователь видит, что это baseline по торгам, а не рыночная оценка. Выполнено 2026-05-06.

## 5. Рыночные аналоги

Срок: 2-4 недели, зависит от доступности источников и правил использования.

**Каркас 2026-05-09:**
- Таблица ORM `MarketComparable` ([backend/app/models.py](backend/app/models.py)), Alembic `20260509_10_add_market_comparables.py`; ingest пока не пишет строки.
- Заглушка [backend/app/services/market/cian.py](backend/app/services/market/cian.py) до разведки задачи E (§0).

**Задачи:**
- Начать с одного источника, предпочтительно Циан.
- Доработать модель `MarketComparable` при необходимости:
  - источник;
  - URL;
  - цена;
  - площадь;
  - цена за сотку;
  - координаты или адрес;
  - ВРИ/тип участка;
  - дата сбора;
  - признаки качества совпадения.
- Реализовать подбор аналогов по кадастровой/географической близости, площади и назначению.
- Добавить расчет `Valuation`:
  - медиана и диапазон рынка;
  - число аналогов;
  - скидка/премия к рынку;
  - confidence.

**Критерий готовности:**
- Для ИЖС-кандидатов в целевых регионах есть объяснимая оценка по аналогам или честное сообщение, что аналогов недостаточно.

## 6. Инвестиционный скоринг и smart-алерты

Срок: 1-2 недели после появления valuation.

**Задачи:**
- Ввести `investment_score` v0:
  - discount score;
  - data confidence;
  - liquidity proxy;
  - risk penalty за неполные данные, подозрительные ВРИ, отсутствие кадастра.
- Добавить фильтр и сортировку по `investment_score`.
- Перевести Telegram на smart-алерты:
  - частично сделано 2026-05-09/10: `TELEGRAM_ALERT_SKIP_LOW_SIGNAL`, `TELEGRAM_ALERT_MIN_DISCOUNT_TO_BASELINE`, `TELEGRAM_ALERT_REQUIRE_BASELINE_FOR_DISCOUNT`, `TELEGRAM_ALERT_REQUIRE_CADASTRAL`, `TELEGRAM_ALERT_ONLY_IZHS`, `TELEGRAM_ALERTS_ENABLED`, компактная Telegram-карточка с сигналами;
  - далее: отправлять только при `score >= threshold` и явная причина попадания в алерт.

**Критерий готовности:**
- Telegram перестает быть шумным журналом изменений и становится каналом реально интересных лотов.

## 7. Подготовка к production

Срок: параллельно после стабилизации MVP.

**Выполнено 2026-05-06:**
- Frontend CI расширен: кроме `npx tsc --noEmit` теперь запускаются `npm run test` и `npm run build`.
- FastAPI startup переведён с deprecated `@app.on_event` на lifespan; APScheduler останавливается на shutdown.
- `TradesMap` больше не использует `setHTML`; popup собирается через DOM/textContent.
- `dev_sync_schema.py` теперь добавляет недостающие индексы для существующей SQLite и предупреждает про FK, которые SQLite нельзя добавить без rebuild таблицы.
- `MapPage` и `TradesMap` вынесены в lazy chunks; основной Vite bundle стал меньше, MapLibre остаётся отдельным крупным async chunk.

**Задачи:**
- Перейти на PostgreSQL:
  - проверить `alembic upgrade head`;
  - отключить или ограничить `Base.metadata.create_all()` вне dev;
  - описать миграционный путь SQLite -> PostgreSQL.
- Расширить CI:
  - `ruff`;
  - frontend lint;
  - backend migration smoke-test.
- Улучшить frontend-надежность:
  - error boundary;
  - минимальные component/integration tests для фильтров.

**Критерий готовности:**
- Проект можно поднять на чистой машине с PostgreSQL, прогнать миграции и получить зеленый CI.

## Приоритет на следующий рабочий заход

1. Smoke-test `/lots`, `/lots/:id`, ingest. Telegram опционально: завести бота и задать `TELEGRAM_*` позже; при деплое SPA — `APP_PUBLIC_BASE_URL`.
2. НСПД: каркас клиента в `backend/app/services/nspd/` (выключен `NSPD_ENABLED=false`). Дальше — `CadastralEnrichment`, кеш, подключение к ingest/репроцессингу.
3. После НСПД-слоя уточнить baseline; разведка Циан/Домклик/Авито (задача E) для осмысленных ссылок на рынок, не только поисковый query.
4. `investment_score` и Telegram smart-алерты (порог по score) — после появления внешней оценки или отдельным решением.
