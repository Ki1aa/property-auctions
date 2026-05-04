# WORKLOG - Журнал работ

> **Append-only.** Свежие записи **сверху**.
> Перед началом работы агент читает [AGENTS.md](AGENTS.md) и минимум 1-3 свежих записи отсюда.
> После завершения работы агент **обязательно** добавляет новую запись по шаблону в конце файла.

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
