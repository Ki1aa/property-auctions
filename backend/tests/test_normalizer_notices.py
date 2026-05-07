from app.services.ingest.normalizer import normalize_lot


def test_normalize_lot_from_opendata_notice():
    item = {
        "regNum": "21000035130000000340",
        "documentType": "notice",
        "publishDate": "2026-04-22T05:06:01.737Z",
        "href": "https://torgi.gov.ru/new/opendata/7710568760-notice/docs/notice_123.json",
        "bidderOrgCode": "2100003513",
        "rightHolderCode": "2100003513",
        "biddTypeCode": "178FZ",
        "subjectEstateCode": "77",
    }

    normalized = normalize_lot(item)

    assert normalized["source_id"] == "21000035130000000340"
    assert normalized["title"].startswith("Извещение")
    assert normalized["status"] == "notice"
    assert normalized["region"] == "77"
    assert normalized["category"] == "178FZ"
    assert normalized["source_url"] == item["href"]
    assert normalized["organizer"]["source_id"] == "2100003513"
