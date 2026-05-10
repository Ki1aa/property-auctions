from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organizer(Base):
    __tablename__ = "organizers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    inn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    kpp: Mapped[str | None] = mapped_column(String(20), nullable=True)

    lots: Mapped[list["Lot"]] = relationship(back_populates="organizer")


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    start_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    organizer_id: Mapped[int | None] = mapped_column(ForeignKey("organizers.id"), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Land-plot enrichment (filled from ГИС Торги notice detail JSON).
    cadastral_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    permitted_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    permitted_use_codes: Mapped[str | None] = mapped_column(String(256), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    settlement: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    notice_detail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notice_reg_num: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    notice_lot_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    notice_lot_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_izhs_candidate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)

    # Link to the raw OpenDataNotice record (when the lot came from opendata).
    opendata_notice_id: Mapped[int | None] = mapped_column(
        ForeignKey("opendata_notices.id"), nullable=True, index=True
    )

    # NSPD geoportal (optional; filled when NSPD_ENABLED and cadastral_number present).
    nspd_specified_area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    nspd_readable_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    nspd_cost_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    nspd_centroid_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    nspd_centroid_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    nspd_card_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nspd_card_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nspd_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    map_anchor_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    map_anchor_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    map_anchor_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    map_anchor_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organizer: Mapped[Organizer | None] = relationship(back_populates="lots")
    snapshots: Mapped[list["LotSnapshot"]] = relationship(back_populates="lot")
    opendata_notice: Mapped["OpenDataNotice | None"] = relationship(foreign_keys=[opendata_notice_id])
    market_comparables: Mapped[list["MarketComparable"]] = relationship(back_populates="lot")
    notice_attributes: Mapped[list["LotNoticeAttribute"]] = relationship(
        back_populates="lot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class LotNoticeAttribute(Base):
    __tablename__ = "lot_notice_attributes"
    __table_args__ = (
        Index("ix_lot_notice_attributes_lot_code", "lot_id", "code"),
        Index("ix_lot_notice_attributes_code_value_text", "code", "value_text"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="notice_detail", server_default="notice_detail")
    ordinal: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lot: Mapped["Lot"] = relationship(back_populates="notice_attributes")


class LotSnapshot(Base):
    __tablename__ = "lot_snapshots"
    __table_args__ = (UniqueConstraint("lot_id", "payload_hash", name="uq_lot_snapshot_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lot: Mapped[Lot] = relationship(back_populates="snapshots")


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    upserted_count: Mapped[int] = mapped_column(Integer, default=0)
    changed_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_files: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_kind: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestManifest(Base):
    __tablename__ = "ingest_manifest"
    __table_args__ = (UniqueConstraint("source_url", "sha256", name="uq_ingest_manifest_source_sha256"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    dataset_id: Mapped[str] = mapped_column(String(128), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    structure_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    data_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    records_count: Mapped[int] = mapped_column(Integer, default=0)
    error_kind: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (UniqueConstraint("lot_id", "event_type", "event_hash", name="uq_alert_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    event_hash: Mapped[str] = mapped_column(String(64), index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TelegramDigestItem(Base):
    """Queued Telegram alert rows; flushed periodically when TELEGRAM_DIGEST_ENABLED=true."""

    __tablename__ = "telegram_digest_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    event_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketComparable(Base):
    """Stored marketplace listing snapshots for future valuation (Cian/Avito/Domclick); not filled by ingest yet."""

    __tablename__ = "market_comparables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("lots.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    external_listing_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    listing_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    price_rub: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    region_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lot: Mapped["Lot | None"] = relationship(back_populates="market_comparables")


class OpenDataNotice(Base):
    __tablename__ = "opendata_notices"
    __table_args__ = (
        Index("ix_opendata_notices_reg_num_id", "reg_num", "id"),
        Index("ix_opendata_notices_document_type_id", "document_type", "id"),
        Index("ix_opendata_notices_bidd_type_code_id", "bidd_type_code", "id"),
        Index("ix_opendata_notices_publish_date_id", "publish_date", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reg_num: Mapped[str] = mapped_column(String(64), index=True)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    href: Mapped[str] = mapped_column(Text, unique=True, index=True)
    bidder_org_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    right_holder_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bidd_type_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ownership_forms_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_estate_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_right_holder_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    structure_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
