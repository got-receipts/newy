from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    shifts: Mapped[list["Shift"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    vehicles: Mapped[list["UserVehicle"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("user_vehicles.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    gross_earnings: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    tips: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    trips: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trips_since_break: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_trip_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    break_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    miles: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    gas_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    other_expenses: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    active_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="shifts")
    vehicle: Mapped["UserVehicle | None"] = relationship(back_populates="shifts")
    breaks: Mapped[list["Break"]] = relationship(back_populates="shift", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="shift", cascade="all, delete-orphan")
    platform_entries: Mapped[list["PlatformEntry"]] = relationship(back_populates="shift", cascade="all, delete-orphan")


class Break(Base):
    __tablename__ = "breaks"

    id: Mapped[int] = mapped_column(primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    break_type: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shift: Mapped[Shift] = relationship(back_populates="breaks")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    shift: Mapped[Shift] = relationship(back_populates="expenses")


class PlatformEntry(Base):
    __tablename__ = "platform_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    gross_earnings: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    tips: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    trips: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    miles: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    shift: Mapped[Shift] = relationship(back_populates="platform_entries")


class VehicleCatalog(Base):
    __tablename__ = "vehicle_catalog"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    make: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    mpg_city: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    mpg_highway: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    mpg_combined: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(40), default="gasoline", nullable=False)

    user_vehicles: Mapped[list["UserVehicle"]] = relationship(back_populates="catalog")


class UserVehicle(Base):
    __tablename__ = "user_vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    catalog_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_catalog.id", ondelete="SET NULL"), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(80), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    make: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    mpg_city: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    mpg_highway: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    mpg_combined: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(40), default="gasoline", nullable=False)
    fuel_price_per_gallon: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("3.50"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="vehicles")
    catalog: Mapped[VehicleCatalog | None] = relationship(back_populates="user_vehicles")
    shifts: Mapped[list[Shift]] = relationship(back_populates="vehicle")
