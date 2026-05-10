from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Lot, MarketComparable, Organizer
from app.services.lot_baseline import lot_valuation
from app.services.market_median import load_market_median_stats, valuation_with_market


def test_valuation_with_market_median_discount():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = Session()
    org = Organizer(source_id="o", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="l1",
        title="t",
        organizer_id=org.id,
        region="72",
        start_price=1_000_000.0,
        area_sqm=1000.0,
        is_izhs_candidate=True,
        cadastral_number="72:01:1:1",
    )
    db.add(lot)
    db.flush()
    db.add(
        MarketComparable(
            lot_id=None,
            source="cian",
            price_rub=3_000_000.0,
            area_sqm=1000.0,
            region_code="72",
        )
    )
    db.add(
        MarketComparable(
            lot_id=None,
            source="cian",
            price_rub=5_000_000.0,
            area_sqm=1000.0,
            region_code="72",
        )
    )
    db.commit()

    baseline_index = {
        "region_category": {},
        "region": {},
        "category": {},
        "global": None,
    }
    v0 = lot_valuation(lot, baseline_index)
    stats = load_market_median_stats(db)
    merged = valuation_with_market(lot, v0, stats)

    assert merged.market_baseline_price_per_sotka == 400_000.0
    assert merged.discount_to_market is not None and merged.discount_to_market > 0
    assert merged.investment_score is not None
    db.close()
