from app.models import Lot
from app.services.lot_identity import (
    lot_notice_identity,
    lot_preferred_list_title,
    notice_identity_from_values,
)


def test_notice_identity_prefers_stored_fields():
    lot = Lot(
        source_id="72000000000000000123:lot:2",
        title="t",
        is_izhs_candidate=False,
        notice_reg_num="72000000000000000999",
        notice_lot_number="7",
        notice_lot_count=9,
    )

    identity = lot_notice_identity(lot, {"_notice_lot": {"lotNumber": "2"}, "_notice_lot_count": 3})

    assert identity.reg_num == "72000000000000000999"
    assert identity.lot_number == "7"
    assert identity.lot_count == 9


def test_notice_identity_uses_snapshot_payload_before_source_suffix():
    identity = notice_identity_from_values(
        source_id="72000000000000000123:lot:2",
        latest_payload={"_notice_lot": {"lotNumber": "5"}, "_notice_lot_count": 6},
    )

    assert identity.reg_num == "72000000000000000123"
    assert identity.lot_number == "5"
    assert identity.lot_count == 6


def test_notice_identity_defaults_single_notice_source_to_lot_one():
    identity = notice_identity_from_values(source_id="72000000000000000123")

    assert identity.reg_num == "72000000000000000123"
    assert identity.lot_number == "1"
    assert identity.lot_count is None


def test_preferred_title_uses_lot_name_from_snapshot():
    lot = Lot(
        source_id="72000000000000000123:lot:2",
        title="Извещение о торгах",
        is_izhs_candidate=False,
        cadastral_number="72:01:1:1",
        notice_reg_num="72000000000000000123",
        notice_lot_number="2",
        notice_lot_count=3,
    )
    payload = {"_notice_lot": {"lotName": "Земельный участок под ИЖС"}, "_notice_lot_count": 3}
    assert lot_preferred_list_title(lot, payload) == "Земельный участок под ИЖС"


def test_preferred_title_multilot_falls_back_to_number_and_cadastre():
    lot = Lot(
        source_id="72000000000000000123:lot:2",
        title="Извещение о торгах",
        is_izhs_candidate=False,
        cadastral_number="72:01:1:1",
        notice_reg_num="72000000000000000123",
        notice_lot_number="2",
        notice_lot_count=3,
    )
    payload = {"_notice_lot": {"lotNumber": "2"}, "_notice_lot_count": 3}
    assert lot_preferred_list_title(lot, payload) == "Лот 2: 72:01:1:1"


def test_preferred_title_single_lot_uses_cadastre_over_notice_title():
    lot = Lot(
        source_id="72000000000000000123",
        title="Продажа имущества должника",
        is_izhs_candidate=False,
        cadastral_number="72:01:1:2",
        notice_reg_num="72000000000000000123",
        notice_lot_number="1",
        notice_lot_count=1,
    )
    assert lot_preferred_list_title(lot, None) == "72:01:1:2"


def test_preferred_title_single_lot_no_cadastre_uses_lot_index_and_reg_not_notice_title():
    lot = Lot(
        source_id="72000000000000000123",
        title="Продажа имущества должника",
        is_izhs_candidate=False,
        cadastral_number=None,
        notice_reg_num="72000000000000000123",
        notice_lot_number="1",
        notice_lot_count=1,
    )
    assert lot_preferred_list_title(lot, None) == "Лот 1 · 72000000000000000123"


def test_preferred_title_multilot_no_cadastre_uses_lot_and_reg():
    lot = Lot(
        source_id="72000000000000000123:lot:2",
        title="Извещение о торгах",
        is_izhs_candidate=False,
        cadastral_number=None,
        notice_reg_num="72000000000000000123",
        notice_lot_number="2",
        notice_lot_count=3,
    )
    payload = {"_notice_lot": {"lotNumber": "2"}, "_notice_lot_count": 3}
    assert lot_preferred_list_title(lot, payload) == "Лот 2 · 72000000000000000123"
