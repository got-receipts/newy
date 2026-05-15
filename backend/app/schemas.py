from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Platform(StrEnum):
    uber_eats = "Uber Eats"
    doordash = "DoorDash"
    grubhub = "Grubhub"
    instacart = "Instacart"
    amazon_flex = "Amazon Flex"
    other = "Other"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class VehicleCatalogRead(BaseModel):
    id: int
    year: int
    make: str
    model: str
    mpg_city: Decimal
    mpg_highway: Decimal
    mpg_combined: Decimal
    fuel_type: str

    model_config = ConfigDict(from_attributes=True)


class UserVehicleCreate(BaseModel):
    catalog_id: int | None = None
    nickname: str | None = None
    year: int | None = Field(default=None, ge=1980, le=2035)
    make: str | None = None
    model: str | None = None
    mpg_city: Decimal | None = Field(default=None, gt=0)
    mpg_highway: Decimal | None = Field(default=None, gt=0)
    mpg_combined: Decimal | None = Field(default=None, gt=0)
    fuel_type: str = "gasoline"
    fuel_price_per_gallon: Decimal = Field(default=Decimal("3.50"), gt=0)
    is_active: bool = True


class UserVehicleRead(BaseModel):
    id: int
    user_id: int
    catalog_id: int | None
    nickname: str | None
    year: int
    make: str
    model: str
    mpg_city: Decimal
    mpg_highway: Decimal
    mpg_combined: Decimal
    fuel_type: str
    fuel_price_per_gallon: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ShiftStart(BaseModel):
    platform: Platform
    started_at: datetime | None = None
    notes: str | None = None


class ShiftUpdate(BaseModel):
    platform: Platform | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    gross_earnings: Decimal | None = Field(default=None, ge=0)
    tips: Decimal | None = Field(default=None, ge=0)
    trips: int | None = Field(default=None, ge=0)
    miles: Decimal | None = Field(default=None, ge=0)
    gas_cost: Decimal | None = Field(default=None, ge=0)
    other_expenses: Decimal | None = Field(default=None, ge=0)
    active_minutes: int | None = Field(default=None, ge=0)
    notes: str | None = None


class ShiftCreate(ShiftUpdate):
    platform: Platform
    started_at: datetime
    ended_at: datetime | None = None


class ShiftEnd(ShiftUpdate):
    ended_at: datetime | None = None


class BreakStart(BaseModel):
    break_type: str = "rest"
    started_at: datetime | None = None
    notes: str | None = None
    location_name: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    target_latitude: Decimal | None = None
    target_longitude: Decimal | None = None


class BreakEnd(BaseModel):
    ended_at: datetime | None = None
    notes: str | None = None


class BreakRead(BaseModel):
    id: int
    shift_id: int
    started_at: datetime
    ended_at: datetime | None
    break_type: str
    notes: str | None
    location_name: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    confirmed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ShiftMetrics(BaseModel):
    total_minutes: int
    gross_hourly: Decimal
    net_hourly: Decimal
    earnings_per_mile: Decimal
    tax_set_aside: Decimal
    maintenance_reserve: Decimal
    net_profit: Decimal


class BreakStatus(BaseModel):
    level: str
    message: str
    suggested_minutes: int
    next_due_minutes: int | None = None
    break_allowed: bool = False
    break_required: bool = False


class TripComplete(BaseModel):
    count: int = Field(default=1, ge=1, le=10)
    multi_order: bool = False


class ShiftRead(BaseModel):
    id: int
    user_id: int
    vehicle_id: int | None = None
    started_at: datetime
    ended_at: datetime | None
    platform: str
    gross_earnings: Decimal
    tips: Decimal
    trips: int
    trips_since_break: int = 0
    last_trip_at: datetime | None = None
    break_required: bool = False
    miles: Decimal
    gas_cost: Decimal
    other_expenses: Decimal
    active_minutes: int
    notes: str | None
    created_at: datetime
    updated_at: datetime
    breaks: list[BreakRead] = []
    metrics: ShiftMetrics
    break_status: BreakStatus
    estimated_fuel_cost: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class WeeklyReport(BaseModel):
    week_start: datetime
    week_end: datetime
    shifts: int
    online_minutes: int
    active_minutes: int
    gross_earnings: Decimal
    tips: Decimal
    trips: int
    miles: Decimal
    gas_cost: Decimal
    other_expenses: Decimal
    gross_hourly: Decimal
    net_hourly: Decimal
    earnings_per_mile: Decimal
    tax_set_aside: Decimal
    maintenance_reserve: Decimal
    net_profit: Decimal
