from app.models import Lot
from app.services import external_lot_links as links


def _lot(**kwargs) -> Lot:
    base: dict = {
        "source_id": "0352200004826000101",
        "title": "t",
        "is_izhs_candidate": False,
    }
    base.update(kwargs)
    return Lot(**base)


def test_pkk_map_url_uses_nspd_public_cadastral_map():
    url = links.pkk_map_url("72:23:0123456:7")
    assert url is not None
    assert "nspd.gov.ru/map" in url
    assert "query=72:23:0123456:7" in url


def test_rosreestr_cadastral_map_url_empty_when_no_cadastral():
    assert links.rosreestr_cadastral_map_url(None) is None
    assert links.rosreestr_cadastral_map_url("") is None


def test_nspd_map_url_requires_cadastral_number():
    assert links.nspd_map_url(None) is None
    assert links.nspd_map_url("") is None
    assert links.nspd_map_url("72:23:0123456:7") == (
        "https://nspd.gov.ru/map?thematic=PKK&theme_id=1&baseLayerId=235&"
        "is_copy_url=true&query=72:23:0123456:7"
    )


def test_nspd_map_url_deep_links_when_card_and_centroid_present():
    url = links.nspd_map_url(
        "72:24:0609016:181",
        centroid_latitude=58.160968393508334,
        centroid_longitude=68.27459727823052,
        card_id="291667829",
        card_type="36384",
    )
    assert url is not None
    assert "zoom=20" in url
    assert "coordinate_x=" in url
    assert "coordinate_y=" in url
    assert "selectedCard=291667829,36384,72:24:0609016:181" in url


def test_nspd_map_url_centers_when_only_centroid_present():
    url = links.nspd_map_url(
        "72:24:0609016:181",
        centroid_latitude=58.160968393508334,
        centroid_longitude=68.27459727823052,
    )
    assert url is not None
    assert "zoom=20" in url
    assert "coordinate_x=" in url
    assert "coordinate_y=" in url
    assert "query=72:24:0609016:181" in url
    assert "selectedCard=" not in url


def test_nspd_lot_map_url_uses_lot_enrichment():
    lot = _lot(
        cadastral_number="72:24:0609016:181",
        nspd_centroid_latitude=58.160968393508334,
        nspd_centroid_longitude=68.27459727823052,
        nspd_card_id="291667829",
        nspd_card_type="36384",
    )
    assert "selectedCard=291667829,36384,72:24:0609016:181" in (links.nspd_lot_map_url(lot) or "")


def test_torgi_notice_html_from_payload_regnum():
    lot = _lot(source_id="x")
    payload = {
        "regNum": "72000000000000000123",
        "href": "https://torgi.gov.ru/new/opendata/7710568760-notice/notice_72000000000000000123_702bf5e5-c1fe-43d9-b713-b52e485c6eea.json",
    }
    assert links.torgi_notice_html_url(lot, payload) == (
        "https://torgi.gov.ru/new/public/notices/view/72000000000000000123"
    )


def test_torgi_notice_html_prefers_official_detail_href():
    lot = _lot(source_id="72000000000000000123")
    payload = {
        "exportObject": {
            "structuredObject": {
                "notice": {
                    "commonInfo": {
                        "noticeNumber": "72000000000000000123",
                        "href": "https://torgi.gov.ru/new/public/notices/view/72000000000000000123",
                    }
                }
            }
        }
    }
    assert links.torgi_notice_html_url(lot, payload) == (
        "https://torgi.gov.ru/new/public/notices/view/72000000000000000123"
    )


def test_torgi_lot_html_defaults_to_first_lot_for_single_lot_notice():
    lot = _lot(
        source_id="72000000000000000999",
        source_url="https://torgi.gov.ru/new/opendata/7710568760-notice/notice_72000000000000000999_702bf5e5-c1fe-43d9-b713-b52e485c6eea.json",
        notice_detail_url=None,
    )
    assert links.torgi_public_url(lot, None) == (
        "https://torgi.gov.ru/new/public/lots/lot/72000000000000000999_1"
    )
    assert links.torgi_notice_html_url(lot, None) == (
        "https://torgi.gov.ru/new/public/notices/view/72000000000000000999"
    )


def test_torgi_public_uses_concrete_lot_from_multilot_source_id():
    lot = _lot(
        source_id="72000000000000000999:lot:4",
        source_url="https://torgi.gov.ru/new/opendata/7710568760-notice/notice_72000000000000000999_702bf5e5-c1fe-43d9-b713-b52e485c6eea.json",
        notice_detail_url=None,
    )
    assert links.torgi_public_url(lot, None) == (
        "https://torgi.gov.ru/new/public/lots/lot/72000000000000000999_4"
    )


def test_torgi_public_uses_lot_number_from_snapshot_payload():
    lot = _lot(
        source_id="72000000000000000999",
        source_url="https://torgi.gov.ru/new/opendata/7710568760-notice/notice_72000000000000000999_702bf5e5-c1fe-43d9-b713-b52e485c6eea.json",
        notice_detail_url=None,
    )
    payload = {"_notice_lot": {"lotNumber": "7"}}
    assert links.torgi_public_url(lot, None, payload) == (
        "https://torgi.gov.ru/new/public/lots/lot/72000000000000000999_7"
    )


def test_torgi_public_uses_stored_notice_identity_without_snapshot_payload():
    lot = _lot(
        source_id="72000000000000000999",
        source_url="https://torgi.gov.ru/new/opendata/7710568760-notice/notice_72000000000000000999_702bf5e5-c1fe-43d9-b713-b52e485c6eea.json",
        notice_detail_url=None,
        notice_reg_num="72000000000000000999",
        notice_lot_number="7",
        notice_lot_count=9,
    )
    assert links.torgi_public_url(lot, None) == (
        "https://torgi.gov.ru/new/public/lots/lot/72000000000000000999_7"
    )


def test_torgi_public_falls_back_to_json_url():
    lot = _lot(source_id="short", source_url="https://torgi.gov.ru/notice.json", notice_detail_url=None)
    assert links.torgi_public_url(lot, None) == "https://torgi.gov.ru/notice.json"


def test_domclick_search_uses_query_from_lot(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_search_urls", True)
    lot = _lot(
        source_id="72000000000000000123",
        cadastral_number="72:01:1:1",
        address="ул. Тестовая",
        municipality="Тюмень",
        region="72",
    )
    d = links.domclick_land_search_url(lot)
    assert d is not None and "domclick.ru" in d and "query=" in d


def test_domclick_map_url_uses_nspd_centroid(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_map_urls", True)
    monkeypatch.setattr(links.settings, "marketplace_map_radius_km", 5.0)
    lot = _lot(
        region="72",
        nspd_centroid_latitude=57.1522,
        nspd_centroid_longitude=65.5272,
    )

    url = links.domclick_land_map_url(lot)

    assert url is not None
    assert url.startswith("https://domclick.ru/search/on-map?")
    assert "offer_type=lot" in url
    assert "sw=57.107284,65.444392" in url
    assert "ne=57.197116,65.610008" in url


def test_domclick_map_url_falls_back_to_lot_coordinates(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_map_urls", True)
    lot = _lot(region="86", latitude=61.0, longitude=69.0)

    url = links.domclick_land_map_url(lot)

    assert url is not None
    assert url.startswith("https://domclick.ru/search/on-map?")


def test_domclick_map_url_disabled_or_without_coordinates(monkeypatch):
    lot = _lot(region="72")
    monkeypatch.setattr(links.settings, "include_marketplace_map_urls", True)
    assert links.domclick_land_map_url(lot) is None

    monkeypatch.setattr(links.settings, "include_marketplace_map_urls", False)
    lot.nspd_centroid_latitude = 57.1522
    lot.nspd_centroid_longitude = 65.5272
    assert links.domclick_land_map_url(lot) is None


def test_marketplace_disabled(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_search_urls", False)
    lot = _lot(cadastral_number="72:01:1:1", region="72")
    assert links.domclick_land_search_url(lot) is None
    assert links.domclick_land_search_url_cadastral_only(lot) is None


def test_torgi_json_link_when_distinct_requires_html_and_differs():
    lot = _lot(
        source_id="72000000000000000123",
        notice_detail_url="https://torgi.gov.ru/new/opendata/7710568760-notice/notice_72000000000000000123_702bf5e5-c1fe-43d9-b713-b52e485c6eea.json",
    )
    payload = {"regNum": "72000000000000000123"}
    assert links.torgi_notice_json_link_when_distinct(lot, payload) == lot.notice_detail_url


def test_torgi_json_link_none_when_only_json():
    lot = _lot(source_id="x", source_url="https://torgi.gov.ru/only.json", notice_detail_url=None)
    assert links.torgi_notice_json_link_when_distinct(lot, None) is None


def test_cadastral_only_search_urls(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_search_urls", True)
    lot = _lot(
        source_id="72000000000000000123",
        cadastral_number="72:01:1:1",
        address="ул. Тестовая",
        municipality="Тюмень",
        region="72",
    )
    d = links.domclick_land_search_url_cadastral_only(lot)
    assert d is not None and "domclick.ru" in d
    assert "Тестовая" not in (d or "")


def test_domclick_disabled_when_template_empty(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_search_urls", True)
    monkeypatch.setattr(links.settings, "domclick_search_template", "")
    lot = _lot(cadastral_number="99:01:1:1", region="99")
    assert links.domclick_land_search_url(lot) is None
