from app.services.nspd.client import NspdGeoportalClient, parse_geoportal_response


def test_parse_geoportal_response_features():
    payload = {"features": [{"type": "Feature", "id": 1}, {"type": "Feature", "id": 2}]}
    assert len(parse_geoportal_response(payload)) == 2


def test_parse_geoportal_response_data():
    payload = {"data": [{"a": 1}]}
    assert parse_geoportal_response(payload) == [{"a": 1}]


def test_parse_geoportal_response_empty():
    assert parse_geoportal_response({}) == []
    assert parse_geoportal_response([]) == []


def test_search_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr("app.services.nspd.client.settings.nspd_enabled", False)
    client = NspdGeoportalClient(base_url="https://nspd.gov.ru", thematic_search_id=1, timeout_seconds=5.0)
    assert client.search_by_cadastral("72:01:1:1") is None


def test_from_settings_uses_tls_verify_flag(monkeypatch):
    monkeypatch.setattr("app.services.nspd.client.settings.nspd_base_url", "https://nspd.gov.ru/")
    monkeypatch.setattr("app.services.nspd.client.settings.nspd_geoportal_thematic_id", 1)
    monkeypatch.setattr("app.services.nspd.client.settings.nspd_timeout_seconds", 7)
    monkeypatch.setattr("app.services.nspd.client.settings.nspd_verify_tls", False)
    client = NspdGeoportalClient.from_settings()
    assert client.base_url == "https://nspd.gov.ru"
    assert client.timeout_seconds == 7.0
    assert client.verify_tls is False
