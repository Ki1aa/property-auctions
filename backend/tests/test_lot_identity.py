from app.models import Lot
from app.services.lot_identity import lot_notice_identity, notice_identity_from_values


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
