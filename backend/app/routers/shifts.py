from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.calculations import as_utc, break_status, metrics, total_minutes
from app.database import get_db
from app.geo import miles_between
from app.models import Break, Shift, User, UserVehicle
from app.schemas import BreakEnd, BreakRead, BreakStart, ShiftCreate, ShiftEnd, ShiftRead, ShiftStart, ShiftUpdate, TripComplete
from app.security import get_current_user

router = APIRouter(tags=["shifts"])
TRIP_COOLDOWN_SECONDS = 4 * 60
TRIPS_BEFORE_MANDATED_BREAK = 5
MANUAL_OVERRIDE_BREAK_MINUTES = Decimal("7.5")
STANDARD_BREAK_MINUTES = Decimal("15.0")
MANUAL_FOLLOWUP_MINUTES = 45
MANUAL_FOLLOWUP_TRIPS = 3
BREAK_ZONE_RADIUS_FEET = 400
FEET_PER_MILE = 5280


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def shift_or_404(db: Session, user_id: int, shift_id: int) -> Shift:
    shift = db.scalar(
        select(Shift)
        .options(selectinload(Shift.breaks))
        .where(Shift.id == shift_id, Shift.user_id == user_id)
    )
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


def gas_used_gallons(shift: Shift, vehicle: UserVehicle | None = None) -> Decimal | None:
    if not shift.miles or shift.miles <= 0:
        return None
    mpg = vehicle.mpg_combined if vehicle is not None else None
    if mpg is None or mpg <= 0:
        return None
    return (shift.miles / mpg).quantize(Decimal("0.01"))


def manual_followup_is_due(shift: Shift, now: datetime) -> bool:
    due_at = as_utc(shift.manual_break_followup_due_at)
    return (due_at is not None and due_at <= now) or shift.manual_break_followup_trips >= MANUAL_FOLLOWUP_TRIPS


def serialize_shift(shift: Shift) -> ShiftRead:
    now = now_utc()
    minutes = total_minutes(shift.started_at, shift.ended_at, now)
    calc = metrics(
        started_at=shift.started_at,
        ended_at=shift.ended_at,
        gross_earnings=shift.gross_earnings,
        miles=shift.miles,
        gas_cost=shift.gas_cost,
        other_expenses=shift.other_expenses,
        now=now,
    )
    status_payload = break_status(minutes)
    manual_due = manual_followup_is_due(shift, now)
    has_required_break = bool(shift.break_required) or manual_due
    status_payload["break_allowed"] = minutes >= 80 or has_required_break
    status_payload["lunch_allowed"] = minutes >= 120 or shift.trips_since_break >= 20
    status_payload["break_required"] = has_required_break
    status_payload["manual_followup_due_at"] = shift.manual_break_followup_due_at
    status_payload["manual_followup_trips"] = shift.manual_break_followup_trips
    status_payload["manual_followup_trips_remaining"] = max(MANUAL_FOLLOWUP_TRIPS - shift.manual_break_followup_trips, 0)
    if manual_due:
        status_payload["level"] = "required"
        status_payload["message"] = "Manual override recovery break required: stop at the closest safe break zone before taking more orders."
    elif shift.break_required:
        status_payload["level"] = "required"
        status_payload["message"] = "Break required: 5 orders completed since your last break. Go to the closest safe 24-hour fuel stop."
    elif shift.manual_break_followup_due_at is not None:
        due_at = as_utc(shift.manual_break_followup_due_at)
        remaining = max(int(((due_at or now) - now).total_seconds() // 60), 0)
        trips_left = max(MANUAL_FOLLOWUP_TRIPS - shift.manual_break_followup_trips, 0)
        status_payload["level"] = "manual recovery"
        status_payload["message"] = f"Manual override recovery: take a real break in {remaining} minute(s) or after {trips_left} more delivery(s)."
    return ShiftRead(
        id=shift.id,
        user_id=shift.user_id,
        vehicle_id=shift.vehicle_id,
        started_at=shift.started_at,
        ended_at=shift.ended_at,
        platform=shift.platform,
        gross_earnings=shift.gross_earnings,
        tips=shift.tips,
        trips=shift.trips,
        trips_since_break=shift.trips_since_break,
        last_trip_at=shift.last_trip_at,
        break_required=shift.break_required,
        manual_break_followup_due_at=shift.manual_break_followup_due_at,
        manual_break_followup_trips=shift.manual_break_followup_trips,
        miles=shift.miles,
        gas_cost=shift.gas_cost,
        other_expenses=shift.other_expenses,
        active_minutes=shift.active_minutes,
        daily_minutes=shift.daily_minutes,
        notes=shift.notes,
        created_at=shift.created_at,
        updated_at=shift.updated_at,
        breaks=[BreakRead.model_validate(item) for item in shift.breaks],
        metrics=calc,
        break_status=status_payload,
        estimated_fuel_cost=shift.gas_cost,
        gas_used_gallons=gas_used_gallons(shift, shift.vehicle),
    )


@router.post("/shifts/start", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def start_shift(payload: ShiftStart, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ShiftRead:
    active = db.scalar(select(Shift).where(Shift.user_id == current_user.id, Shift.ended_at.is_(None)))
    if active:
        raise HTTPException(status_code=409, detail="You already have an active shift")
    shift = Shift(
        user_id=current_user.id,
        vehicle_id=active_vehicle_id(db, current_user.id),
        started_at=payload.started_at or now_utc(),
        platform=payload.platform.value,
        notes=payload.notes,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return serialize_shift(shift)


@router.post("/shifts", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(payload: ShiftCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ShiftRead:
    data = payload.model_dump(exclude_unset=True)
    data["platform"] = payload.platform.value
    shift = Shift(user_id=current_user.id, **data)
    shift.vehicle_id = active_vehicle_id(db, current_user.id)
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return serialize_shift(shift)


@router.patch("/shifts/{shift_id}/end", response_model=ShiftRead)
def end_shift(shift_id: int, payload: ShiftEnd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ShiftRead:
    shift = shift_or_404(db, current_user.id, shift_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "platform" and value is not None:
            value = value.value
        setattr(shift, field, value)
    apply_vehicle_gas_estimate(db, shift)
    if shift.ended_at is None:
        shift.ended_at = now_utc()
    shift.updated_at = now_utc()
    db.commit()
    db.refresh(shift)
    return serialize_shift(shift)


@router.patch("/shifts/{shift_id}", response_model=ShiftRead)
def update_shift(shift_id: int, payload: ShiftUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ShiftRead:
    shift = shift_or_404(db, current_user.id, shift_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "platform" and value is not None:
            value = value.value
        setattr(shift, field, value)
    apply_vehicle_gas_estimate(db, shift)
    shift.updated_at = now_utc()
    db.commit()
    db.refresh(shift)
    return serialize_shift(shift)


@router.get("/shifts", response_model=list[ShiftRead])
def list_shifts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[ShiftRead]:
    shifts = db.scalars(
        select(Shift)
        .options(selectinload(Shift.breaks))
        .where(Shift.user_id == current_user.id)
        .order_by(desc(Shift.started_at))
    ).all()
    return [serialize_shift(shift) for shift in shifts]


@router.get("/shifts/{shift_id}", response_model=ShiftRead)
def get_shift(shift_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ShiftRead:
    return serialize_shift(shift_or_404(db, current_user.id, shift_id))


def carried_session_totals(db: Session, shift: Shift) -> tuple[int, int]:
    window_start = shift.started_at - timedelta(hours=3)
    previous_shifts = db.scalars(
        select(Shift).where(
            Shift.user_id == shift.user_id,
            Shift.id != shift.id,
            Shift.ended_at.is_not(None),
            Shift.ended_at >= window_start,
            Shift.ended_at <= shift.started_at,
        )
    ).all()
    carry_minutes = sum(total_minutes(item.started_at, item.ended_at, now_utc()) for item in previous_shifts)
    carry_orders = sum(item.trips_since_break for item in previous_shifts)
    return carry_minutes, carry_orders


@router.post("/shifts/{shift_id}/trips", response_model=ShiftRead)
def complete_trip(shift_id: int, payload: TripComplete, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ShiftRead:
    shift = shift_or_404(db, current_user.id, shift_id)
    if shift.ended_at is not None:
        raise HTTPException(status_code=409, detail="Cannot add trips to an ended shift")
    now = now_utc()
    if shift.break_required or manual_followup_is_due(shift, now):
        shift.break_required = True
        db.commit()
        raise HTTPException(status_code=409, detail="Break required before adding more completed trips")
    last_trip_at = as_utc(shift.last_trip_at)
    if not payload.multi_order and last_trip_at is not None:
        seconds_since_last = (now - last_trip_at).total_seconds()
        if seconds_since_last < TRIP_COOLDOWN_SECONDS:
            remaining = int((TRIP_COOLDOWN_SECONDS - seconds_since_last + 59) // 60)
            raise HTTPException(status_code=429, detail=f"Trip cooldown active. Wait about {remaining} minute(s), or use multi-order if you completed multiple orders in one trip.")
    shift.trips += payload.count
    shift.trips_since_break += payload.count
    if shift.manual_break_followup_due_at is not None:
        shift.manual_break_followup_trips += payload.count
    shift.last_trip_at = now
    if shift.trips_since_break >= TRIPS_BEFORE_MANDATED_BREAK or manual_followup_is_due(shift, now):
        shift.break_required = True
    shift.updated_at = now
    db.commit()
    db.refresh(shift)
    return serialize_shift(shift)


@router.delete("/shifts/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(shift_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    shift = shift_or_404(db, current_user.id, shift_id)
    db.delete(shift)
    db.commit()


@router.post("/shifts/{shift_id}/breaks/start", response_model=BreakRead, status_code=status.HTTP_201_CREATED)
def start_break(shift_id: int, payload: BreakStart, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Break:
    shift = shift_or_404(db, current_user.id, shift_id)
    if shift.ended_at is not None:
        raise HTTPException(status_code=409, detail="Cannot start a break on an ended shift")
    now = now_utc()
    carry_minutes, carry_orders = carried_session_totals(db, shift)
    minutes = total_minutes(shift.started_at, shift.ended_at, now) + carry_minutes
    orders = shift.trips_since_break + carry_orders
    manual_recovery_due = manual_followup_is_due(shift, now)
    required_break = bool(shift.break_required) or manual_recovery_due
    if payload.break_type == "lunch" and minutes < 120 and orders < 20:
        raise HTTPException(status_code=409, detail="Lunch unlocks after 2 hours online or 20 completed orders in this carried session")
    if payload.break_type not in {"emergency", "lunch"} and minutes < 80 and not required_break:
        raise HTTPException(status_code=409, detail="Breaks unlock after 80 minutes online or once 5 completed orders require a break")
    if manual_recovery_due and (payload.manual_override or payload.target_latitude is None or payload.target_longitude is None):
        raise HTTPException(status_code=409, detail="Manual override recovery requires a confirmed 15 minute break at a break location")
    active_break = db.scalar(select(Break).where(Break.shift_id == shift_id, Break.ended_at.is_(None)))
    if active_break:
        raise HTTPException(status_code=409, detail="This shift already has an active break")
    distance_feet = None
    if payload.target_latitude is not None and payload.target_longitude is not None:
        if payload.latitude is None or payload.longitude is None:
            raise HTTPException(status_code=400, detail="Current location is required to confirm a break zone")
        distance = miles_between(
            float(payload.latitude),
            float(payload.longitude),
            float(payload.target_latitude),
            float(payload.target_longitude),
        )
        distance_feet = int(distance * FEET_PER_MILE)
        if distance_feet > BREAK_ZONE_RADIUS_FEET and not payload.manual_override:
            raise HTTPException(status_code=409, detail="Arrive within 400 feet of the selected break zone to start the timer, or use the manual override if you are out of service area.")
    if payload.manual_override and not payload.override_reason:
        raise HTTPException(status_code=400, detail="Manual override reason is required")
    if payload.manual_override:
        if payload.break_type != "rest":
            raise HTTPException(status_code=409, detail="Manual override is only available for rest breaks")
        payload.notes = f"Manual override: {payload.override_reason}. {payload.notes or ''}".strip()
    if payload.tally_gross_earnings is not None:
        shift.gross_earnings = payload.tally_gross_earnings
    if payload.tally_tips is not None:
        shift.tips = payload.tally_tips
    if payload.tally_trips is not None:
        shift.trips = payload.tally_trips
    if payload.tally_miles is not None:
        shift.miles = payload.tally_miles
    if payload.tally_active_minutes is not None:
        shift.active_minutes = payload.tally_active_minutes
    if payload.tally_daily_minutes is not None:
        shift.daily_minutes = payload.tally_daily_minutes
    break_item = Break(
        shift_id=shift_id,
        started_at=now_utc() if payload.target_latitude is not None else payload.started_at or now_utc(),
        break_type=payload.break_type,
        notes=payload.notes,
        location_name=payload.location_name,
        latitude=payload.latitude if payload.latitude is not None else payload.target_latitude,
        longitude=payload.longitude if payload.longitude is not None else payload.target_longitude,
        confirmed_at=now_utc() if payload.target_latitude is not None else None,
        manual_override=payload.manual_override,
        planned_minutes=MANUAL_OVERRIDE_BREAK_MINUTES if payload.manual_override else STANDARD_BREAK_MINUTES,
        target_distance_feet=distance_feet,
    )
    db.add(break_item)
    shift.break_required = False
    shift.trips_since_break = 0
    if payload.manual_override:
        shift.manual_break_followup_due_at = now_utc() + timedelta(minutes=MANUAL_FOLLOWUP_MINUTES)
        shift.manual_break_followup_trips = 0
    else:
        shift.manual_break_followup_due_at = None
        shift.manual_break_followup_trips = 0
    shift.updated_at = now_utc()
    db.commit()
    db.refresh(break_item)
    return break_item


def active_vehicle_id(db: Session, user_id: int) -> int | None:
    return db.scalar(select(UserVehicle.id).where(UserVehicle.user_id == user_id, UserVehicle.is_active.is_(True)))


def apply_vehicle_gas_estimate(db: Session, shift: Shift) -> None:
    if shift.gas_cost and shift.gas_cost > 0:
        return
    vehicle = db.get(UserVehicle, shift.vehicle_id) if shift.vehicle_id else None
    if vehicle is None or not shift.miles:
        return
    shift.gas_cost = (shift.miles / vehicle.mpg_combined) * vehicle.fuel_price_per_gallon


@router.patch("/breaks/{break_id}/end", response_model=BreakRead)
def end_break(break_id: int, payload: BreakEnd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Break:
    break_item = db.scalar(
        select(Break)
        .join(Shift)
        .where(Break.id == break_id, Shift.user_id == current_user.id)
    )
    if break_item is None:
        raise HTTPException(status_code=404, detail="Break not found")
    planned_seconds = int(float(break_item.planned_minutes or STANDARD_BREAK_MINUTES) * 60)
    elapsed_seconds = (now_utc() - as_utc(break_item.started_at)).total_seconds()
    if break_item.ended_at is None and elapsed_seconds < planned_seconds:
        remaining = int((planned_seconds - elapsed_seconds + 59) // 60)
        raise HTTPException(status_code=409, detail=f"Break is locked for {remaining} more minute(s)")
    break_item.ended_at = payload.ended_at or now_utc()
    if payload.notes is not None:
        break_item.notes = payload.notes
    db.commit()
    db.refresh(break_item)
    return break_item
