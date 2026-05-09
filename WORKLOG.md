# WORKLOG - Журнал работ

> **Append-only.** Свежие записи **сверху**.
> Перед началом работы агент читает [AGENTS.md](AGENTS.md) и минимум 1-3 свежих записи отсюда.
> После завершения работы агент **обязательно** добавляет новую запись по шаблону в конце файла.

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
