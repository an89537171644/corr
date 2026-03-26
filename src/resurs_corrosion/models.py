from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AssetModel(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500))
    commissioned_year: Mapped[Optional[int]] = mapped_column(Integer)
    purpose: Mapped[Optional[str]] = mapped_column(String(255))
    responsibility_class: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    elements: Mapped[List["ElementModel"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ElementModel(Base):
    __tablename__ = "elements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    element_code: Mapped[str] = mapped_column(String(100), nullable=False)
    element_type: Mapped[str] = mapped_column(String(100), nullable=False)
    steel_grade: Mapped[Optional[str]] = mapped_column(String(100))
    work_scheme: Mapped[Optional[str]] = mapped_column(String(255))
    operating_zone: Mapped[Optional[str]] = mapped_column(String(255))
    environment_category: Mapped[str] = mapped_column(String(10), nullable=False)
    current_service_life_years: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    section_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    material_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    action_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset: Mapped["AssetModel"] = relationship(back_populates="elements")
    section_snapshot: Mapped[Optional["ElementSectionSnapshotModel"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    material_snapshot: Mapped[Optional["ElementMaterialSnapshotModel"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    action_snapshot: Mapped[Optional["ElementActionSnapshotModel"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    zones: Mapped[List["ZoneModel"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ZoneModel.id",
    )
    inspections: Mapped[List["InspectionModel"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="InspectionModel.performed_at.desc(), InspectionModel.id.desc()",
    )
    analysis_runs: Mapped[List["AnalysisRunModel"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AnalysisRunModel.id.desc()",
    )


class ElementSectionSnapshotModel(Base):
    __tablename__ = "element_section_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    element_id: Mapped[int] = mapped_column(ForeignKey("elements.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="section.v2")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="json_shadow")
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    element: Mapped["ElementModel"] = relationship(back_populates="section_snapshot")


class ElementMaterialSnapshotModel(Base):
    __tablename__ = "element_material_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    element_id: Mapped[int] = mapped_column(ForeignKey("elements.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="material.v2")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="json_shadow")
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    element: Mapped["ElementModel"] = relationship(back_populates="material_snapshot")


class ElementActionSnapshotModel(Base):
    __tablename__ = "element_action_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    element_id: Mapped[int] = mapped_column(ForeignKey("elements.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="action.v2")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="json_shadow")
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    element: Mapped["ElementModel"] = relationship(back_populates="action_snapshot")


class ZoneModel(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    element_id: Mapped[int] = mapped_column(ForeignKey("elements.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_code: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    initial_thickness_mm: Mapped[float] = mapped_column(Float, nullable=False)
    exposed_surfaces: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pitting_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pit_loss_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    element: Mapped["ElementModel"] = relationship(back_populates="zones")


class InspectionModel(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    element_id: Mapped[int] = mapped_column(ForeignKey("elements.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_code: Mapped[Optional[str]] = mapped_column(String(100))
    performed_at: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str] = mapped_column(String(255), nullable=False)
    executor: Mapped[Optional[str]] = mapped_column(String(255))
    findings: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    element: Mapped["ElementModel"] = relationship(back_populates="inspections")
    measurements: Mapped[List["MeasurementModel"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MeasurementModel.id",
    )


class MeasurementModel(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_code: Mapped[str] = mapped_column(String(100), nullable=False)
    point_id: Mapped[Optional[str]] = mapped_column(String(100))
    thickness_mm: Mapped[float] = mapped_column(Float, nullable=False)
    error_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    measured_at: Mapped[Optional[date]] = mapped_column(Date)
    quality: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    units: Mapped[str] = mapped_column(String(32), nullable=False, default="mm")
    comment: Mapped[Optional[str]] = mapped_column(Text)

    inspection: Mapped["InspectionModel"] = relationship(back_populates="measurements")


class AnalysisRunModel(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    element_id: Mapped[Optional[int]] = mapped_column(ForeignKey("elements.id", ondelete="CASCADE"), nullable=True, index=True)
    request_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    element: Mapped[Optional["ElementModel"]] = relationship(back_populates="analysis_runs")
