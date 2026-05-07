"""Generate final source_discovery_<DATE>.md and .json from collected probe artifacts.

Inputs (in data/raw/):
- latest_opendata_meta.json
- structure-20240401.json
- torgi_opendata_tyumen_union.json
- torgi_sample_lots_<DATE>.json
- torgi_sample_lots_full_<DATE>/
- torgi_ui_probe_<DATE>.json
- nspd_samples_<DATE>.json
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DATE_TAG = datetime.now(timezone.utc).strftime("%Y%m%d")

OUT_MD = RAW / f"source_discovery_{DATE_TAG}.md"
OUT_JSON = RAW / f"source_discovery_{DATE_TAG}.json"

IZHS_CODES = {"2.1", "2.2", "2.3", "13.1", "13.2"}


def _load(name: str):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def _epsg3857_to_4326(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator (EPSG:3857) coords to lat/lon (EPSG:4326)."""
    lon = (x / 20037508.34) * 180.0
    lat = (y / 20037508.34) * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return (lat, lon)


def main() -> None:
    meta = _load("latest_opendata_meta.json")
    structure = _load("structure-20240401.json")
    union = _load("torgi_opendata_tyumen_union.json")
    sample = _load(f"torgi_sample_lots_{DATE_TAG}.json")
    ui_probe = _load(f"torgi_ui_probe_{DATE_TAG}.json")
    nspd = _load(f"nspd_samples_{DATE_TAG}.json")

    # ---- Build summary metadata --------------------------------------------------
    summary_json = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "torgi_opendata": {
            "dataset_card_url": meta.get("page_url"),
            "dataset_id": "7710568760-notice",
            "registry_url": "https://torgi.gov.ru/new/opendata/list.json",
            "latest_data_url": meta.get("data_url"),
            "structure_url": meta.get("structure_url"),
            "schema_version": "20240401",
            "structure_title": structure.get("title"),
            "structure_description": structure.get("description"),
            "list_object_required_fields": structure["definitions"]["ListObject"].get("required", []),
            "list_object_all_fields": list(
                structure["definitions"]["ListObject"]["properties"].keys()
            ),
            "documentType_enum": structure["definitions"]["ListObject"]["properties"]["documentType"].get("enum", []),
            "tyumen_union_local_files": union.get("day_files"),
            "tyumen_union_count": union.get("count"),
        },
        "torgi_ui": {
            "html_card_url_pattern": "https://torgi.gov.ru/new/public/notices/view/{noticeNumber}",
            "html_is_spa_shell": True,
            "spa_xhr_search_endpoint": "https://torgi.gov.ru/new/api/public/notices/search",
            "spa_xhr_search_example_params": {"dynSubjRF": "72", "biddType": "ZK", "size": 5},
            "spa_xhr_search_response_shape": "Spring pageable: {content[], pageable, totalPages, totalElements, ...}",
            "spa_xhr_search_per_item_keys": [
                "id", "publishDate", "noticeStatus", "biddForm", "biddType",
                "noticeNumber", "procedureName", "bidderOrg.name",
                "biddStartTime", "biddEndTime", "biddReviewDate", "auctionStartDate",
                "etpCode", "lots[].lotNumber", "lots[].lotStatus", "lots[].lotName",
                "lots[].priceMin", "lots[].priceMinExact", "lots[].attributes[]",
            ],
            "ui_probe_artifact": f"data/raw/torgi_ui_probe_{DATE_TAG}.json",
        },
        "torgi_sample_coverage": {
            "n_fetched": sample["fetched_ok"],
            "n_total": sample["fetched_total"],
            "coverage_counts": sample["coverage_counts"],
            "coverage_percent": sample["coverage_percent"],
            "raw_dir": sample["raw_dir"],
            "summary_artifact": f"data/raw/torgi_sample_lots_{DATE_TAG}.json",
        },
        "nspd": {
            "healthy_endpoint": "https://nspd.gov.ru/api/geoportal/v1/search/geoportal?query={cadnum}&thematicSearchId=1",
            "endpoint_health": nspd.get("endpoint_health"),
            "samples_count": len(nspd.get("samples", [])),
            "response_format": "GeoJSON FeatureCollection (type=FeatureCollection, features[].geometry, features[].properties.options)",
            "geometry_crs": "EPSG:3857",
            "extracted_fields": [
                "options.cad_num",
                "options.specified_area (точная площадь, кв.м)",
                "options.declared_area",
                "options.land_record_category_type (категория земель, текст)",
                "options.permitted_use_established_by_document (ВРИ из документа, текст)",
                "options.readable_address (адрес, текст)",
                "options.cost_value (кадастровая стоимость, руб) — БОНУС, отсутствует в Торгах",
                "options.cost_index (УПКС, руб/кв.м)",
                "options.quarter_cad_number",
                "options.ownership_type",
                "options.status (кадастровый статус)",
                "geometry (Polygon в EPSG:3857)",
            ],
            "samples_artifact": f"data/raw/nspd_samples_{DATE_TAG}.json",
        },
    }

    # ---- Compose lot rows for the markdown table --------------------------------
    rows = []
    izhs_by_code = 0
    izhs_by_keyword = 0  # current detector heuristic
    izhs_codes_seen: Counter = Counter()
    cad_to_nspd: dict[str, dict] = {}

    # index NSPD samples by cadnum
    for s in nspd.get("samples", []):
        if s.get("status") == 200 and s.get("raw_payload"):
            feats = s["raw_payload"].get("features") or []
            if feats and isinstance(feats[0], dict):
                cad_to_nspd[s["cadnum"]] = feats[0]

    for it in sample["items"]:
        od = it["opendata_item"]
        p = it["parsed_by_detail_parser"]
        vri_codes = it.get("permitted_use_codes") or []
        for c in vri_codes:
            izhs_codes_seen[c] += 1
        is_izhs_by_code = any(c.split(".")[0] + "." + c.split(".")[1] in IZHS_CODES if "." in c else False
                              for c in vri_codes if c.count(".") >= 1)
        # broader: prefix match on classifier codes "2.1" / "2.2" / etc.
        is_izhs_by_code = any(any(c == w or c.startswith(w + ".") for w in IZHS_CODES) for c in vri_codes)
        if is_izhs_by_code:
            izhs_by_code += 1
        # current keyword heuristic check
        text_blob = json.dumps([p, vri_codes, od.get("biddTypeCode"), it.get("common_info") or {}], ensure_ascii=False).lower()
        if any(k in text_blob for k in ("ижс", "индивидуальное жилищное", "2.1")):
            izhs_by_keyword += 1

        nspd_feat = cad_to_nspd.get(p.get("cadastral_number") or "")
        nspd_area = (nspd_feat or {}).get("properties", {}).get("options", {}).get("specified_area") if nspd_feat else None
        nspd_kad_cost = (nspd_feat or {}).get("properties", {}).get("options", {}).get("cost_value") if nspd_feat else None
        nspd_addr = (nspd_feat or {}).get("properties", {}).get("options", {}).get("readable_address") if nspd_feat else None
        # convert one geometry centroid to lat/lon (rough mean of coords)
        lat_lon = None
        if nspd_feat and nspd_feat.get("geometry", {}).get("type") == "Polygon":
            ring = nspd_feat["geometry"]["coordinates"][0]
            xs = [pt[0] for pt in ring]
            ys = [pt[1] for pt in ring]
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            lat_lon = _epsg3857_to_4326(cx, cy)

        rows.append({
            "regNum": od["regNum"],
            "biddType": od.get("biddTypeCode"),
            "estate_right": f"{od.get('subjectEstateCode')}/{od.get('subjectRightHolderCode')}",
            "lot_status": it.get("lot_status"),
            "land_category": p.get("land_category"),
            "vri_codes": ",".join(vri_codes) if vri_codes else None,
            "is_izhs_by_code": is_izhs_by_code,
            "area_sqm_torgi": p.get("area_sqm"),
            "area_sqm_nspd": nspd_area,
            "cadastral": p.get("cadastral_number"),
            "start_price": p.get("start_price"),
            "kadastral_cost_nspd": nspd_kad_cost,
            "address_torgi": p.get("address"),
            "address_nspd": nspd_addr,
            "centroid_latlon_4326": lat_lon,
            "ui_href": it.get("ui_href"),
        })

    summary_json["sample_lots"] = rows
    summary_json["sample_izhs_stats"] = {
        "by_code_whitelist": izhs_by_code,
        "by_keyword_heuristic": izhs_by_keyword,
        "vri_codes_distribution": dict(izhs_codes_seen),
    }

    OUT_JSON.write_text(json.dumps(summary_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- Build markdown ---------------------------------------------------------
    md = []
    md.append(f"# Разведка источников ГИС Торги / НСПД для ИЖС-мониторинга в Тюменской области ({DATE_TAG})\n")
    md.append(
        "## Краткий вывод\n\n"
        "- **Текущий проект качает правильный dataset ГИС Торги** "
        "(`7710568760-notice`, schema `structure-20240401`). Discovery через registry/card/direct работает, "
        "watermark и идемпотентность работают, локально уже накоплены 4 day-файла.\n"
        "- **OpenData listObjects недостаточно** для бизнес-логики: это лишь индекс "
        "(regNum / documentType / biddTypeCode / publishDate / region codes / href). "
        "**Все ключевые поля (кадастр, площадь, ВРИ, категория, адрес, цена, даты торгов, организатор) "
        "приходят только из notice detail JSON**, который скачивается вторым шагом по `href`. "
        "Текущий ingest правильно делает этот второй шаг через `INGEST_FETCH_NOTICE_DETAILS=true`.\n"
        f"- **На точечной выборке Тюмени (n={sample['fetched_ok']}): coverage по нужным полям 75-100%.** "
        "Подробности ниже. Это значит, что для MVP мониторинга (новые лоты + ИЖС-кандидаты + ₽/сотка) "
        "достаточно ГИС Торги OpenData + notice detail. **НСПД не блокирует MVP.**\n"
        "- **НСПД (nspd.gov.ru) доступен** через endpoint "
        "`https://nspd.gov.ru/api/geoportal/v1/search/geoportal?query={cadnum}&thematicSearchId=1` "
        "(GET, без авторизации). Отдает GeoJSON Feature с геометрией участка, точной площадью, "
        "категорией, ВРИ из документа, адресом и **кадастровой стоимостью** (бонус, отсутствует в Торгах). "
        "Подключать НСПД стоит для второй итерации (геометрия для карты, кадастровая стоимость как baseline).\n"
        "- **HTML-карточки `torgi.gov.ru/new/public/notices/view/...` — это пустой SPA-shell** (одинаковые 22.7KB для любого id). "
        "Парсить HTML смысла нет. SPA внутри ходит за данными в `/new/api/public/notices/search` "
        "и аналогичные XHR-эндпоинты, которые отдают тот же набор полей, что и notice detail JSON, но фильтруемый на стороне сервера.\n"
    )

    md.append("## Проверенные URL\n")
    md.append(
        "| Назначение | URL | Статус | Что отдаёт |\n"
        "|---|---|---|---|\n"
        f"| OpenData карточка датасета | {meta.get('page_url')} | OK | HTML с ссылками на data-*.json и structure-*.json |\n"
        f"| Реестр open data | https://torgi.gov.ru/new/opendata/list.json | OK | Перечень датасетов (используется в discovery как fallback) |\n"
        f"| Свежий day-файл OpenData | {meta.get('data_url')} | OK ({union.get('count')} записей по Тюмени за 4 дня) | `listObjects[]` с `regNum/href/...` |\n"
        f"| Schema | {meta.get('structure_url')} | OK | JSON Schema OpenDataList v3.1 от 01.04.2024 |\n"
        f"| Notice detail JSON | https://torgi.gov.ru/new/opendata/7710568760-notice/docs/notice_<regNum>_<uuid>.json | OK (16/16 в выборке) | Полная карточка лота: characteristics, FIAS, цены, даты, организатор |\n"
        f"| HTML-карточка лота | https://torgi.gov.ru/new/public/notices/view/<regNum> | 200, но SPA-shell без данных | Пустой HTML, JS грузит данные XHR'ом |\n"
        f"| SPA search XHR | https://torgi.gov.ru/new/api/public/notices/search?dynSubjRF=72&biddType=ZK&size=5 | OK | Spring pageable (content[]+pageable+totalElements). На фильтре отдаёт **те же поля, что notice detail**, но с серверной фильтрацией |\n"
        f"| НСПД геопоиск | https://nspd.gov.ru/api/geoportal/v1/search/geoportal?query=<cadnum>&thematicSearchId=1 | OK (8/8 кадастров) | GeoJSON Feature: геометрия EPSG:3857 + properties.options |\n"
        f"| НСПД v2/aeggis/eggis/rosreestr | (см. nspd_samples) | 403/404 | требуют другие headers/cookies или другой путь |\n"
    )

    md.append("\n## Какой dataset ГИС Торги нужен\n")
    md.append(
        f"- **Dataset ID:** `7710568760-notice`\n"
        f"- **Карточка:** {meta.get('page_url')}\n"
        f"- **Schema version:** `20240401` (v3.1, описание: \"{structure.get('description')}\")\n"
        f"- **Структура data-*.json:** объект с одним полем `listObjects: ListObject[]`. "
        f"Каждый ListObject обязательно содержит: `{', '.join(structure['definitions']['ListObject'].get('required', []))}`. "
        f"Доступные значения `documentType`: `{', '.join(structure['definitions']['ListObject']['properties']['documentType'].get('enum', []))}`.\n"
        f"- **Свежий пример data-URL:** {meta.get('data_url')}\n"
        f"- **Локально сохранено 4 day-файла** ({', '.join(union.get('day_files', []))}), всего "
        f"{union.get('count')} записей по Тюменской области (`subjectEstateCode=72 OR subjectRightHolderCode=72`).\n"
    )

    md.append("\n## Какие поля есть в OpenData (listObjects)\n")
    md.append("Только идентификаторы + ссылка на полный документ:\n\n")
    for k, v in structure["definitions"]["ListObject"]["properties"].items():
        desc = (v.get("description") or "").splitlines()[0]
        md.append(f"- `{k}` — {desc}\n")
    md.append(
        "\n**Что НЕЛЬЗЯ узнать из listObjects:** название лота, кадастровый номер, площадь, ВРИ, категорию, адрес, цены, даты торгов, организатора. "
        "Всё перечисленное живёт в notice detail JSON, который грузится по `href`.\n"
    )

    md.append("\n## Какие поля есть только в notice detail (`href` JSON)\n")
    md.append(
        "Структура: `exportObject.structuredObject.notice` со схемой `schemeVersion: 5.1`.\n\n"
        "Ключевые ветви:\n"
        "- `commonInfo`: `noticeNumber`, `biddType {code,name}`, `biddForm`, `publishDate`, `procedureName`, `etp`, `href` (UI-ссылка).\n"
        "- `bidderOrg.orgInfo`: `code, name, INN, KPP, OGRN, orgType, legalAddress, actualAddress` — организатор.\n"
        "- `rightHolderInfo.rightHolderOrg`: правообладатель (если отличается от организатора).\n"
        "- `lots[]`: массив лотов в рамках одного извещения, каждый с:\n"
        "  - `lotNumber`, `lotStatus` (PUBLISHED/CANCELED/...), `lotName`, `lotDescription`.\n"
        "  - `priceMin`, `priceStep`, `deposit`, `currency`, `priceMinVAT`.\n"
        "  - `biddingObjectInfo.subjectRF.code` — **РЕГИОН НАХОЖДЕНИЯ ОБЪЕКТА** (важно для нашего фильтра).\n"
        "  - `biddingObjectInfo.estateAddress` (текст) + `biddingObjectInfo.estateAddressFIAS.addressByFIAS` "
        "(`name`, `level.code`, `hierarchyObjects[]`) — структурированный ФИАС-адрес с муниципальной иерархией.\n"
        "  - `biddingObjectInfo.category {code,name}` — категория земель.\n"
        "  - `biddingObjectInfo.ownershipForms`.\n"
        "  - `biddingObjectInfo.characteristics[]` — массив с `code`/`name`/`characteristicValue`. Ключевые коды:\n"
        "    - `CadastralNumber` → `characteristicValue: '72:17:2314003:6575'`\n"
        "    - `SquareZU` → `characteristicValue: 1410, OKEI: {code: '055', name: 'Квадратный метр'}`\n"
        "    - `PermittedUse` → `characteristicValue: [{code: '2.1', name: 'ИЖС'}]` — **код классификатора ВРИ**\n"
        "  - `additionalDetails[]` — `DA_*` атрибуты (срок аренды, ограничения, коммуникации, параметры строительства).\n"
        "  - `docs[]`, `imageIds[]`, `attachments[]` (ГПЗУ, форма заявки, проект договора).\n"
        "- `biddConditions`: `biddStartTime, biddEndTime, biddReviewDate, startDate` — даты торгов.\n"
        "- `signedData`: SHA-256 + ЭЦП.\n"
    )

    md.append("\n## Поля, которые есть только в HTML / UI / SPA-XHR\n")
    md.append(
        "- **HTML карточки `/new/public/notices/view/<id>` ничего не дают** — это SPA-shell (22711 байт одинакового содержимого), все данные подгружаются JavaScript'ом. Парсить HTML бессмысленно.\n"
        "- **SPA XHR `/new/api/public/notices/search`** работает (200 OK на `dynSubjRF=72&biddType=ZK&size=5`) и возвращает Spring pageable: `{content[], totalPages, totalElements, ...}`. "
        "Каждый элемент `content[]` имеет ту же структуру, что и notice detail JSON (включая `lots[].attributes[]` и `signedData`). "
        "**Это даёт серверную фильтрацию и сортировку без скачивания всего day-файла.** Альтернативный pipeline.\n"
        "- В выборке зафиксированы UI-параметры: `dynSubjRF=72` (Тюменская область), `biddType=ZK` (земельные торги ЗК), "
        "`size`/`page`. Параметр сортировки `sort=firstVersionPublishDate,desc` отдал 400 — нужен другой ключ. "
        "Полная схема параметров не разведана (роадмап).\n"
        "- Endpoint'ы справочников `/new/api/public/dict/biddType` / `landCategory` / `permittedUse` отвечают 404 — реальные пути в SPA bundle, в этой разведке не извлекались.\n"
    )

    md.append("\n## Какие поля нужно брать из НСПД\n")
    md.append(
        "Endpoint `https://nspd.gov.ru/api/geoportal/v1/search/geoportal?query=<cadnum>&thematicSearchId=1` "
        "отдаёт GeoJSON `FeatureCollection` с одним Feature на участок. Структура:\n\n"
        "```\n"
        "feature.id, feature.type='Feature'\n"
        "feature.geometry: {type:'Polygon', coordinates:[[[x,y],...]], crs: EPSG:3857}  // Web Mercator\n"
        "feature.properties.options:\n"
        "  cad_num                 кадастровый номер\n"
        "  specified_area          точная площадь, кв.м (часто отличается от Торгов на 0-1%)\n"
        "  declared_area           площадь по декларации (часто null)\n"
        "  land_record_category_type   категория земель (текст)\n"
        "  permitted_use_established_by_document  ВРИ из документа (текст; кода классификатора нет)\n"
        "  readable_address        адрес (текст)\n"
        "  cost_value              кадастровая стоимость (руб) - ОТСУТСТВУЕТ В ТОРГАХ\n"
        "  cost_index              УПКС (руб/кв.м) - ОТСУТСТВУЕТ В ТОРГАХ\n"
        "  cost_application_date / cost_approvement_date / cost_determination_date / cost_registration_date\n"
        "  quarter_cad_number      кадастровый квартал\n"
        "  ownership_type          тип собственности\n"
        "  status                  кадастровый статус (Учтено/Архивный/...)\n"
        "feature.properties.label   обычно равен cad_num\n"
        "feature.properties.systemInfo  inserted/updated даты в НСПД\n"
        "```\n\n"
        "**Что добавляет НСПД к Торгам:**\n"
        "1. **Полигональная геометрия** в EPSG:3857 — нужна для отрисовки контура на карте.\n"
        "2. **Кадастровая стоимость** — независимый baseline, лучше нашего рассчитанного по медиане ₽/сотка для ranking.\n"
        "3. **Точная площадь и адрес** — кросс-валидация Торгов (если расходится >5%, помечать аномалию).\n"
        "4. **Категория земель и ВРИ** — кросс-валидация (но тут НСПД даёт текст без кода классификатора, а Торги — код).\n\n"
        "**Что НЕ может НСПД:**\n"
        "- Не знает о торгах (нет цены лота, дат биддинга, организатора, статуса аукциона).\n"
        "- Иногда `specified_area=null` для проблемных/архивных участков.\n"
        "- Endpoint v2 и aeggis/eggis отвечают 403 без правильных headers — для MVP достаточно v1.\n\n"
        f"См. примеры в `data/raw/nspd_samples_{DATE_TAG}.json` ({len(nspd.get('samples', []))} ответов).\n"
    )

    md.append(f"\n## Coverage detail_parser на нашей выборке (n={sample['fetched_ok']})\n\n")
    md.append("| Поле | Coverage | % |\n|---|---:|---:|\n")
    for k in (
        "cadastral_number", "area_sqm", "land_category", "permitted_use_text", "permitted_use_code",
        "address", "start_price", "lot_name", "subjectRF_code", "municipality_fias",
        "lot_status", "bidd_dates", "organizer", "ui_href",
    ):
        cnt = sample["coverage_counts"][k]
        pct = sample["coverage_percent"][k]
        md.append(f"| {k} | {cnt}/{sample['fetched_ok']} | {pct}% |\n")

    md.append(f"\n**ИЖС-статистика выборки** (по PermittedUse.code, белый список {sorted(IZHS_CODES)}): "
              f"{summary_json['sample_izhs_stats']['by_code_whitelist']}/{sample['fetched_ok']} лотов.\n")
    md.append(f"**ИЖС-статистика по текущему keyword-эвристику** (substring 'ижс' / 'индивидуальное жилищное' / '2.1' в JSON): "
              f"{summary_json['sample_izhs_stats']['by_keyword_heuristic']}/{sample['fetched_ok']}.\n")
    md.append(f"**Распределение ВРИ-кодов в выборке**: `{summary_json['sample_izhs_stats']['vri_codes_distribution']}`.\n")

    md.append("\n## Поле → источник → надёжность\n")
    md.append(
        "| Поле | Источник | Надёжность | Комментарий |\n"
        "|---|---|---|---|\n"
        "| идентификатор лота | OpenData `regNum` + Notice detail `commonInfo.noticeNumber` | A | Совпадают, идемпотентный ключ |\n"
        "| номер извещения | OpenData `regNum` | A | |\n"
        "| URL карточки (UI) | Notice detail `commonInfo.href` (`/new/public/notices/view/...`) | A | Доступен для редиректа пользователя |\n"
        "| URL карточки (data) | OpenData `href` | A | Используется для скачивания detail |\n"
        "| дата публикации | OpenData `publishDate` + Notice detail `commonInfo.publishDate` | A | |\n"
        "| дата обновления | Notice detail `signedData` + версия | B | Явного `updateDate` нет; косвенно — по новой версии notice или по noticeStop/Resumption/Cancel |\n"
        "| статус торгов | Notice detail `lots[].lotStatus` (PUBLISHED/BIDDING/CANCELED/COMPLETED), плюс `documentType` из OpenData | A | Cancel/Annulment — документ-событие, обновляющее состояние |\n"
        "| регион (subject) | Notice detail `lots[].biddingObjectInfo.subjectRF.code` | A | **Лучше**, чем `subjectEstateCode/subjectRightHolderCode` из listObjects (последний — про правообладателя) |\n"
        "| муниципалитет / адрес (текст) | Notice detail `lots[].biddingObjectInfo.estateAddress` | A | 93.8% покрытие |\n"
        "| муниципалитет (структурированно) | Notice detail `lots[].biddingObjectInfo.estateAddressFIAS.addressByFIAS.hierarchyObjects[]` | A | ФИАС с уровнями 1/3/4; парсер сейчас НЕ извлекает |\n"
        "| кадастровый номер | Notice detail `characteristics[code=CadastralNumber].characteristicValue` | A | 81% в выборке (нет у noticeCancel и нек. APGU/178FZ) |\n"
        "| площадь (кв.м) | Notice detail `characteristics[code=SquareZU].characteristicValue` (с OKEI=055) | A | 87.5%, кросс-валидация с `НСПД.specified_area` |\n"
        "| категория земель | Notice detail `lots[].biddingObjectInfo.category.{code,name}` | A | 93.8% |\n"
        "| ВРИ (текст) | Notice detail `characteristics[code=PermittedUse].characteristicValue[].name` | A | 75% |\n"
        "| ВРИ (код классификатора) | Notice detail `characteristics[code=PermittedUse].characteristicValue[].code` | A | 75%, **надёжный сигнал ИЖС**, заменяет keyword-эвристик |\n"
        "| стартовая цена | Notice detail `lots[].priceMin` (или `characteristics[code=StartPrice]`) | A | 81% (нет у инф.сообщений типа АПГУ и noticeCancel) |\n"
        "| цена за сотку | Расчёт `start_price / (area_sqm/100)` | A | Уже есть в API |\n"
        "| организатор (имя/ИНН/КПП/ОГРН) | Notice detail `bidderOrg.orgInfo` | A | 93.8% |\n"
        "| координаты / геометрия | НСПД `feature.geometry` (EPSG:3857) | B | Только если есть кадастровый номер; нужно конвертировать в EPSG:4326 для maplibre |\n"
        "| кадастровая стоимость | НСПД `properties.options.cost_value` | B | Бонус, отсутствует в Торгах; полезно как baseline |\n"
        "| признак ИЖС | `permitted_use.code in {2.1, 2.1.*, 2.2, 2.2.*, 2.3, 13.1, 13.2}` | A | Текущий keyword-детектор сильно шумит (substring '2.1') |\n"
    )

    md.append("\n## Примеры лотов (выборка из Тюменской области)\n")
    md.append(
        "| regNum | biddType | estate/right | lotStatus | category | ВРИ-код | площадь | кадастр | стартовая цена | НСПД-стоимость | адрес |\n"
        "|---|---|---|---|---|---|---:|---|---:|---:|---|\n"
    )
    for r in rows:
        md.append(
            f"| `{r['regNum']}` | {r['biddType'] or '-'} | {r['estate_right']} | {r['lot_status'] or '-'} | "
            f"{(r['land_category'] or '-')[:30]} | `{r['vri_codes'] or '-'}` | "
            f"{int(r['area_sqm_torgi']) if r['area_sqm_torgi'] is not None else '-'} | "
            f"`{r['cadastral'] or '-'}` | "
            f"{r['start_price']:.0f} | " if r['start_price'] is not None else f"| `{r['regNum']}` | {r['biddType'] or '-'} | {r['estate_right']} | {r['lot_status'] or '-'} | "
            f"{(r['land_category'] or '-')[:30]} | `{r['vri_codes'] or '-'}` | "
            f"{int(r['area_sqm_torgi']) if r['area_sqm_torgi'] is not None else '-'} | "
            f"`{r['cadastral'] or '-'}` | - | "
        )
        md.append(
            (f"{r['kadastral_cost_nspd']:.0f} | " if r['kadastral_cost_nspd'] is not None else "- | ")
            + ((r['address_torgi'] or '-')[:60] + " |\n")
        )

    md.append("\n## Рекомендации по изменению проекта\n")
    md.append(
        "**Минимальный набор для запуска MVP мониторинга ИЖС в Тюмени** (порядок по приоритету):\n\n"
        "1. **Включить региональный фильтр**: `TARGET_REGION_CODES=72` в `.env`. Сейчас фильтра нет — БД растёт всеми регионами (4171+ лотов из 81 субъекта). Это блокирует адекватную оценку «₽/сотка по Тюмени».\n\n"
        "2. **Поправить семантику регионального фильтра** ([backend/app/services/ingest/normalizer.py](backend/app/services/ingest/normalizer.py) и [backend/app/services/ingest/service.py](backend/app/services/ingest/service.py)):\n"
        "   - Сейчас `normalizer.region` берётся из `subjectRFCode || subjectRightHolderCode`. Поля `subjectRFCode` нет в schema 20240401 → де-факто работает `subjectRightHolderCode` (регион правообладателя).\n"
        "   - Нужно: `region = subjectEstateCode` (регион нахождения земли). В нашей выборке 1/16 лот имеет `estate=86 (ХМАО)` при `right=72 (Тюмень)` — текущая логика поймает его как Тюменский, хотя земля в Югре.\n"
        "   - Дополнительно: после загрузки detail брать каноничный `lots[].biddingObjectInfo.subjectRF.code` для двойного контроля.\n\n"
        "3. **ИЖС-детектор по коду классификатора, а не по keyword'ам**:\n"
        "   - В `detail_parser.py` уже извлекается `permitted_use` (текст). Добавить извлечение **кода**: `characteristics[code=PermittedUse].characteristicValue[].code`.\n"
        "   - Белый список: `{2.1, 2.2, 2.3, 13.1, 13.2}` + prefix-match (`2.1.2001` тоже считается). Это уберёт ложные срабатывания на «п. 2.1 регламента» из текущего substring-матча.\n"
        "   - В нашей выборке: 6/16 ИЖС по коду vs 12/16 по keyword (≥50% ложных срабатываний у keyword-эвристика).\n\n"
        "4. **Фильтр по `documentType`**:\n"
        "   - В day-файле 6-7 мая: 1394 notice / 131 noticeCancel / 30 clarifications / 9 noticeStop / 3 noticeResumption / 1 noticeAnnulment.\n"
        "   - **Только `notice` создаёт новые лоты.** `clarifications` — это разъяснение, лот в нём не повторяется (без `lots[]`); сейчас попадает в normalizer и засоряет.\n"
        "   - `noticeCancel/noticeStop/noticeResumption/noticeAnnulment` — это события на существующем лоте, должны менять `Lot.status`, а не создавать новый.\n"
        "   - Рекомендация: в `run_ingest()` маршрутизировать по `documentType` — `notice` → upsert лота, остальное → обновление статуса существующего лота.\n\n"
        "5. **Фильтр по `biddTypeCode` для земли** (опциональный, по флагу):\n"
        "   - Земельный кодекс (`ZK`) — основной поток земельных торгов. В Тюмени 41/77 (53%) лотов в нашем union — `ZK`.\n"
        "   - Земля также может попадать через `178FZ` (банкротство) и `229FZ` (исполнительное), но реже.\n"
        "   - Не-земельные виды (`67FAS_147FAS` концессии, `1041PP` МУП, `ZHKH` ЖКХ, `APGU` арендная плата — публикация платы) можно отсеивать на стадии нормализации.\n\n"
        "6. **Извлекать ФИАС-иерархию** для нормализации `municipality`:\n"
        "   - Из detail `lots[].biddingObjectInfo.estateAddressFIAS.addressByFIAS.hierarchyObjects[]` собрать кортеж (region, район, поселение, населённый пункт).\n"
        "   - Это позволит фильтровать «только Тюмень» / «только Тюменский район» / «только Заводоуковск» в UI без regex по тексту адреса.\n\n"
        "**Среднеприоритетные (после MVP):**\n\n"
        "7. **Подключить НСПД** клиентом по уже найденному endpoint'у `https://nspd.gov.ru/api/geoportal/v1/search/geoportal`:\n"
        "   - Триггер: после upsert лота с непустым `cadastral_number` — асинхронная задача fetch geometry/кадастровая стоимость.\n"
        "   - Сохранять `geometry_geojson_4326`, `kadastral_cost`, `kadastral_cost_index` в новой таблице `LotCadastralEnrichment` или прямо в `Lot`.\n"
        "   - Карта: использовать полигоны вместо точек.\n"
        "   - НСПД-стоимость как baseline для скоринга (вместо/в дополнение к нашей медиане ₽/сотка).\n\n"
        "8. **Альтернативный pipeline через SPA XHR** (`/new/api/public/notices/search`):\n"
        "   - Для срезов «новое за день в Тюмени по ZK» одним запросом получить страницу обогащённых лотов (10-50 на страницу), без двух стадий (index + detail × N).\n"
        "   - Уменьшит трафик в десятки раз; не отменяет OpenData (он остаётся as-of-record).\n\n"
        "**Что НЕ нужно делать:**\n"
        "- Парсить HTML карточек `/new/public/notices/view/...` — это пустой SPA-shell.\n"
        "- Расширять текстовый ИЖС-fallback — корректный сигнал есть в characteristics.PermittedUse.code.\n"
    )

    md.append("\n## Риски и ограничения\n")
    md.append(
        "- **Notice detail иногда отдаёт частичные данные** для документов-событий (noticeCancel/Stop/Annulment): "
        "у них нет `lots[].biddingObjectInfo`, поэтому `cadastral_number/area/category/...` отсутствуют. "
        "Это нормально, но текущий ingest всё равно пытается их парсить и сохраняет «пустой» Lot.\n"
        "- **schema_version фиксированный** (`20240401`). Если Торги выкатят `20250401`, наш ingest пометит файлы `schema_migration_required`. "
        "Это уже корректно реализовано (отдельный статус, raw сохраняется).\n"
        "- **Структура `notice detail` не публикуется** — реальная схема `schemeVersion 5.1` определяется опытным путём. "
        "Рекомендуется хранить полный raw-JSON у первой ingest'и (уже сохраняется в `OpenDataNotice.payload` после линковки).\n"
        "- **НСПД endpoint v2 / aeggis / eggis отдают 403** — вероятно, защита WAF (требует cookie/CSRF/Referer). "
        "v1 пока работает, но это «тихий» legacy endpoint без официальных гарантий стабильности. "
        "Резервный путь — публичная карта nspd.gov.ru с DevTools-recon при отвале.\n"
        "- **EPSG:3857 в НСПД** — нужно конвертировать в EPSG:4326 (lat/lon) для maplibre. Утилита приведена в `_recon_build_report.py` (`_epsg3857_to_4326`).\n"
        "- **Кадастр иногда отсутствует** в Торгах (характерно для лотов АПГУ/инф.сообщений и cancel/stop). "
        "Без кадастра НСПД-обогащение невозможно — придётся ограничиваться текстовым адресом.\n"
        "- **Throttling**: НСПД и Торги без явных rate-limit, но безопасно держать ≥0.3 сек между запросами и ≤200 detail-fetch на ingest run (как сейчас).\n"
        "- **noticeNumber vs regNum**: в нашей выборке совпадают, но в общем случае могут отличаться при перевыпуске извещения (новая версия). Использовать `regNum` как первичный ключ — корректно.\n"
    )

    md.append("\n## Поток данных (для справки)\n")
    md.append("```mermaid\n")
    md.append("flowchart LR\n"
              "    Card[\"torgi.gov.ru карточка датасета\\n61f2a3bf...\"] --> Day[\"data-YYYYMMDDT0000-...-structure-20240401.json\\n(listObjects: индекс)\"]\n"
              "    Day -->|href| Detail[\"notice detail JSON\\nexportObject.structuredObject.notice\"]\n"
              "    Detail -->|characteristics.CadastralNumber| Cad[\"кадастровый номер\"]\n"
              "    Cad --> NSPD[\"nspd.gov.ru\\n/api/geoportal/v1/search/geoportal\\n?query={cad}&thematicSearchId=1\"]\n"
              "    NSPD --> GeoFeat[\"GeoJSON Feature\\nполигон EPSG:3857 + properties.options\"]\n"
              "    Detail --> Lot[(\"Lot в БД:\\nregNum/title/status/region/cad/area/vri/category/address/price\")]\n"
              "    GeoFeat --> Lot2[(\"Lot enrichment:\\ngeometry/kadastral_cost\")]\n"
              "    Day --> Notice[(\"OpenDataNotice raw\")]\n"
              "    Spa[\"/new/api/public/notices/search?dynSubjRF=72&biddType=ZK\"] -->|alt pipeline| Lot\n"
              "```\n")

    md.append("\n## Артефакты этой разведки\n")
    md.append(
        f"- `data/raw/source_discovery_{DATE_TAG}.md` — этот отчёт.\n"
        f"- `data/raw/source_discovery_{DATE_TAG}.json` — машиночитаемая сводка.\n"
        f"- `data/raw/data-20260506T0000-20260507T0000-structure-20240401.json` — свежий day-файл OpenData.\n"
        f"- `data/raw/torgi_opendata_tyumen_union.json` — union 4 day-файлов, отфильтровано по Тюмени (77 записей).\n"
        f"- `data/raw/torgi_sample_lots_{DATE_TAG}.json` — 16 лотов с opendata-item + parsed_detail + извлечёнными полями.\n"
        f"- `data/raw/torgi_sample_lots_full_{DATE_TAG}/<regNum>.json` — исходные detail-JSON по выборке.\n"
        f"- `data/raw/torgi_ui_probe_{DATE_TAG}.json` — результаты probing HTML и SPA-XHR.\n"
        f"- `data/raw/nspd_samples_{DATE_TAG}.json` — 8 ответов НСПД для кадастров из выборки + endpoint health.\n"
    )

    OUT_MD.write_text("".join(md), encoding="utf-8")
    print(f"Written: {OUT_MD.relative_to(ROOT)}")
    print(f"Written: {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
