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


def test_pkk_map_url_encodes_cadastral():
    u = links.pkk_map_url("72:23:0123456:7")
    assert u is not None
    assert "pkk.rosreestr.ru" in u
    assert "72" in u


def test_torgi_notice_html_from_payload_regnum():
    lot = _lot(source_id="x")
    payload = {"regNum": "72000000000000000123"}
    assert links.torgi_notice_html_url(lot, payload) == (
        "https://torgi.gov.ru/new/public/notices/view/72000000000000000123"
    )


def test_torgi_public_prefers_html_over_json():
    lot = _lot(source_id="72000000000000000999", source_url="https://torgi.gov.ru/x.json", notice_detail_url=None)
    assert links.torgi_public_url(lot, None) == "https://torgi.gov.ru/new/public/notices/view/72000000000000000999"


def test_torgi_public_falls_back_to_json_url():
    lot = _lot(source_id="short", source_url="https://torgi.gov.ru/notice.json", notice_detail_url=None)
    assert links.torgi_public_url(lot, None) == "https://torgi.gov.ru/notice.json"


def test_domclick_and_avito_use_query_from_lot(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_search_urls", True)
    lot = _lot(
        source_id="72000000000000000123",
        cadastral_number="72:01:1:1",
        address="ул. Тестовая",
        municipality="Тюмень",
        region="72",
    )
    d = links.domclick_land_search_url(lot)
    a = links.avito_search_url(lot)
    assert d is not None and "domclick.ru" in d and "query=" in d
    assert a is not None and "avito.ru" in a and "q=" in a


def test_marketplace_disabled(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_search_urls", False)
    lot = _lot(cadastral_number="72:01:1:1", region="72")
    assert links.domclick_land_search_url(lot) is None
    assert links.avito_search_url(lot) is None


def test_torgi_json_link_when_distinct_requires_html_and_differs():
    lot = _lot(
        source_id="72000000000000000123",
        notice_detail_url="https://torgi.gov.ru/new/api/public/lot/notice.json",
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
    a = links.avito_search_url_cadastral_only(lot)
    c = links.cian_land_search_url_cadastral_only(lot)
    assert d is not None and "domclick.ru" in d
    assert a is not None and "avito.ru" in a
    assert c is not None and "cian.ru" in c
    assert "Тестовая" not in (d or "")
    assert "Тестовая" not in (a or "")
    assert "Тестовая" not in (c or "")


def test_cian_disabled_when_template_empty(monkeypatch):
    monkeypatch.setattr(links.settings, "include_marketplace_search_urls", True)
    monkeypatch.setattr(links.settings, "cian_land_search_template", "")
    lot = _lot(cadastral_number="72:01:1:1", region="72")
    assert links.cian_land_search_url(lot) is None
