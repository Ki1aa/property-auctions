"""MVP GIS schema (parallel tables; legacy `lots` remains for existing API).

Plan logical names map to tables: notices -> mvp_gis_notices, lots -> mvp_gis_lots.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MvpGisNotice(Base):
    __tablename__ = "mvp_gis_notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notice_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lots: Mapped[list["MvpGisLot"]] = relationship(back_populates="notice", cascade="all, delete-orphan")


class MvpGisLot(Base):
    __tablename__ = "mvp_gis_lots"
    __table_args__ = (
        UniqueConstraint("lot_external_id", name="uq_mvp_gis_lot_external_id"),
        UniqueConstraint("notice_number", "lot_number", name="uq_mvp_gis_notice_lot_number"),
        Index("ix_mvp_gis_lots_region", "region_code"),
        Index("ix_mvp_gis_lots_signal", "signal_level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("mvp_gis_notices.id", ondelete="CASCADE"), index=True)
    notice_number: Mapped[str] = mapped_column(String(64), index=True)
    lot_number: Mapped[str] = mapped_column(String(32))
    lot_external_id: Mapped[str] = mapped_column(String(256), index=True)

    region_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cadastral_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    application_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    application_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    permitted_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    land_category: Mapped[str | None] = mapped_column(String(512), nullable=True)
    price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_100sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    coordinates_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    coordinates_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    lot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    nspd_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    domclick_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    is_land: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    is_housing_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    signal_level: Mapped[str] = mapped_column(String(16), default="NONE", server_default="NONE", index=True)
    is_ignored: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    ignored_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    notice: Mapped[MvpGisNotice] = relationship(back_populates="lots")
    versions: Mapped[list["MvpGisLotVersion"]] = relationship(
        back_populates="lot",
        cascade="all, delete-orphan",
    )
    telegram_events: Mapped[list["MvpGisTelegramEvent"]] = relationship(
        back_populates="lot",
        cascade="all, delete-orphan",
    )


class MvpGisLotVersion(Base):
    __tablename__ = "mvp_gis_lot_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("mvp_gis_lots.id", ondelete="CASCADE"), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    changed_fields_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lot: Mapped[MvpGisLot] = relationship(back_populates="versions")


class MvpGisTelegramEvent(Base):
    __tablename__ = "mvp_gis_telegram_events"
    __table_args__ = (UniqueConstraint("lot_id", "event_type", "content_hash", name="uq_mvp_gis_telegram_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("mvp_gis_lots.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending", index=True)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lot: Mapped[MvpGisLot] = relationship(back_populates="telegram_events")
