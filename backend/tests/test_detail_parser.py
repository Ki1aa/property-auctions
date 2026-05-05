from app.services.ingest.detail_parser import (
    _parse_area_with_units,
    match_izhs,
    parse_notice_detail,
    split_keywords,
)


SAMPLE_NOTICE = {
    "noticeNumber": "22000004000000000180",
    "noticeName": "Аукцион на право заключения договора аренды земельного участка",
    "lots": [
        {
            "lotNumber": 1,
            "lotName": "Земельный участок под индивидуальное жилищное строительство",
            "lotDescription": "Свободный земельный участок, ВРИ - для ИЖС",
            "estateAddress": "Тюменская область, г. Тюмень, ул. Тестовая",
            "cadastralNumbers": ["72:23:0123456:789"],
            "estateArea": 1500.5,
            "landCategory": "Земли населённых пунктов",
            "permittedUse": "Для индивидуального жилищного строительства",
            "auction": {
                "startPrice": 1250000,
                "minPrice": 100000,
                "auctionStartDate": "2026-05-15T10:00:00Z",
            },
        }
    ],
}

SAMPLE_NON_IZHS = {
    "noticeNumber": "11111111110000000001",
    "noticeName": "Имущество предприятия-банкрота",
    "lots": [
        {
            "lotName": "Производственное здание",
            "estateAddress": "г. Москва, Кутузовский 1",
            "cadastralNumbers": ["77:01:0001234:567"],
            "estateArea": 850.0,
            "permittedUse": "Деловое управление",
        }
    ],
}


# Observed on torgi.gov.ru: project / inventory area codes and totalAreaRealty.
REAL_AREA_CODES_NOTICE = {
    "exportObject": {
        "structuredObject": {
            "notice": {
                "lots": [
                    {
                        "lotName": "земельный участок",
                        "biddingObjectInfo": {
                            "category": {"name": "Земли населенных пунктов"},
                            "characteristics": [
                                {
                                    "code": "SquareZU_project",
                                    "name": "Площадь по проекту",
                                    "characteristicValue": 1871,
                                    "OKEI": {"code": "055", "name": "Квадратный метр"},
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}

REAL_TOTAL_AREA_REALTY_NOTICE = {
    "exportObject": {
        "structuredObject": {
            "notice": {
                "lots": [
                    {
                        "lotName": "земельный участок",
                        "biddingObjectInfo": {
                            "category": {"name": "Земли населенных пунктов"},
                            "characteristics": [
                                {
                                    "code": "totalAreaRealty",
                                    "name": "Площадь",
                                    "characteristicValue": 999.5,
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}


REAL_SCHEMA_NOTICE = {
    "exportObject": {
        "structuredObject": {
            "notice": {
                "lots": [
                    {
                        "lotName": "Проведение аукциона на право заключения договора аренды",
                        "priceMin": "213386.58",
                        "biddingObjectInfo": {
                            "estateAddress": "край Хабаровский, м.р-н Николаевский",
                            "category": {"code": "301", "name": "Земли населенных пунктов"},
                            "characteristics": [
                                {
                                    "code": "PermittedUse",
                                    "name": "Основной вид разрешенного использования",
                                    "characteristicValue": [
                                        {"code": "2.7.2002", "name": "Размещение гаражей для собственных нужд"}
                                    ],
                                },
                                {
                                    "code": "CadastralNumber",
                                    "name": "Кадастровый номер земельного участка",
                                    "characteristicValue": "27:20:0010110:376",
                                },
                                {
                                    "code": "SquareZU",
                                    "name": "Площадь земельного участка",
                                    "characteristicValue": 1410,
                                },
                            ],
                        },
                    }
                ]
            }
        }
    }
}


def test_parse_notice_detail_extracts_cadastral_and_area():
    result = parse_notice_detail(SAMPLE_NOTICE)
    assert result["cadastral_number"] == "72:23:0123456:789"
    assert result["area_sqm"] == 1500.5
    assert result["land_category"] == "Земли населённых пунктов"
    assert "индивидуального жилищного" in result["permitted_use"].lower()
    assert "Тюмень" in result["address"]
    assert result["start_price"] == 1250000.0


def test_parse_notice_detail_handles_string_area_with_comma():
    payload = {"lots": [{"area": "1 500,75", "cadastralNumbers": ["72:01:0000001:1"]}]}
    result = parse_notice_detail(payload)
    assert result["area_sqm"] == 1500.75
    assert result["cadastral_number"] == "72:01:0000001:1"


def test_parse_notice_detail_returns_none_when_missing():
    result = parse_notice_detail({"lots": [{"foo": "bar"}]})
    assert result["cadastral_number"] is None
    assert result["area_sqm"] is None
    assert result["land_category"] is None
    assert result["permitted_use"] is None
    assert result["address"] is None


def test_parse_notice_detail_reads_area_from_squarezu_project_characteristic():
    result = parse_notice_detail(REAL_AREA_CODES_NOTICE)
    assert result["area_sqm"] == 1871.0
    assert "земельн" in (result["lot_name"] or "").lower()


def test_parse_notice_detail_reads_area_from_total_area_realty_characteristic():
    result = parse_notice_detail(REAL_TOTAL_AREA_REALTY_NOTICE)
    assert result["area_sqm"] == 999.5


def test_parse_notice_detail_supports_real_schema_characteristics():
    result = parse_notice_detail(REAL_SCHEMA_NOTICE)
    assert result["cadastral_number"] == "27:20:0010110:376"
    assert result["area_sqm"] == 1410.0
    assert result["land_category"] == "Земли населенных пунктов"
    assert result["permitted_use"] == "Размещение гаражей для собственных нужд"
    assert result["address"] == "край Хабаровский, м.р-н Николаевский"
    assert result["start_price"] == 213386.58


def test_match_izhs_positive():
    keywords = split_keywords("ИЖС,индивидуальное жилищное строительство,2.1")
    assert match_izhs(SAMPLE_NOTICE, keywords) is True


def test_match_izhs_negative():
    keywords = split_keywords("ИЖС,индивидуальное жилищное строительство")
    assert match_izhs(SAMPLE_NON_IZHS, keywords) is False


def test_match_izhs_empty_keywords_returns_false():
    assert match_izhs(SAMPLE_NOTICE, []) is False


def test_match_izhs_case_insensitive():
    payload = {"description": "ижс участок"}
    assert match_izhs(payload, ["ИЖС"]) is True


def test_split_keywords_strips_blanks():
    assert split_keywords("a, b ,, c ") == ["a", "b", "c"]


def test_parse_area_with_units_sqm_simple():
    assert _parse_area_with_units("Площадь 1500 кв.м") == 1500.0


def test_parse_area_with_units_sqm_with_thousand_separator():
    assert _parse_area_with_units("Общая площадь 1 500,75 кв. м") == 1500.75


def test_parse_area_with_units_hectares():
    assert _parse_area_with_units("0,12 га") == 1200.0


def test_parse_area_with_units_sotki():
    assert _parse_area_with_units("Дачный участок 8 соток") == 800.0


def test_parse_area_with_units_returns_none_on_garbage():
    assert _parse_area_with_units("без числовых значений") is None
    assert _parse_area_with_units("") is None


def test_parse_notice_detail_falls_back_to_text_area_and_vri():
    payload = {
        "lots": [
            {
                "lotName": "Земельный участок 0,15 га под ИЖС",
                "lotDescription": "Размещение жилого дома, ВРИ - для ИЖС",
                "landCategory": "Земли населённых пунктов",
                "estateAddress": "Тюменская область",
                "cadastralNumbers": ["72:23:0301002:1"],
            }
        ]
    }
    result = parse_notice_detail(payload)
    assert result["area_sqm"] == 1500.0
    assert result["permitted_use"] == "Для индивидуального жилищного строительства"
    assert result["land_category"] == "Земли населённых пунктов"
    assert result["cadastral_number"] == "72:23:0301002:1"


def test_parse_notice_detail_cadastral_with_internal_spaces_normalized():
    payload = {"description": "Участок с кадастровым номером 72 : 23 : 0301002 : 42"}
    result = parse_notice_detail(payload)
    assert result["cadastral_number"] == "72:23:0301002:42"


def test_parse_notice_detail_prefers_price_min_over_price_min_vat():
    payload = {"lots": [{"priceMin": "100", "priceMinVAT": "120"}]}
    assert parse_notice_detail(payload)["start_price"] == 100.0


def test_parse_notice_detail_falls_back_to_price_min_vat():
    payload = {"lots": [{"priceMinVAT": "550000.5"}]}
    assert parse_notice_detail(payload)["start_price"] == 550000.5


def test_parse_notice_detail_start_price_from_start_price_characteristic():
    payload = {
        "lots": [
            {
                "biddingObjectInfo": {
                    "characteristics": [
                        {
                            "code": "StartPrice",
                            "characteristicValue": "1500000",
                        }
                    ]
                }
            }
        ]
    }
    assert parse_notice_detail(payload)["start_price"] == 1500000.0


def test_parse_notice_detail_picks_cadastral_via_characteristic_only():
    payload = {
        "lots": [
            {
                "biddingObjectInfo": {
                    "characteristics": [
                        {
                            "code": "CadastralNumber",
                            "characteristicValue": "72:23:0123456:99",
                        }
                    ]
                }
            }
        ]
    }
    result = parse_notice_detail(payload)
    assert result["cadastral_number"] == "72:23:0123456:99"
