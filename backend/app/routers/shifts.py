from datetime import datetime, timezone

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


def serialize_shift(shift: Shift) -> ShiftRead:
    minutes = total_minutes(shift.started_at, shift.ended_at, now_utc())
    calc = metrics(
        started_at=shift.started_at,
        ended_at=shift.ended_at,
        gross_earnings=shift.gross_earnings,
        miles=shift.miles,
        gas_cost=shift.gas_cost,
        other_expenses=shift.other_expenses,
        now=now_utc(),
    )
    status_payload = break_status(minutes)
    status_payload["break_allowed"] = minutes >= 80 or bool(shift.break_required)
    status_payload["break_required"] = bool(shift.break_required)
    if shift.break_required:
        status_payload["level"] = "required"
        status_payload["message"] = "Break required: 5 orders completed since your last break. Go to the closest safe 24-hour fuel stop."
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
        miles=shift.miles,
        gas_cost=shift.gas_cost,
        other_expenses=shift.other_expenses,
        active_minutes=shift.active_minutes,
        notes=shift.notes,
        created_at=shift.created_at,
        updated_at=shift.updated_at,
        breaks=[BreakRead.model_validate(item) for item in shift.breaks],
        metrics=calc,
        break_status=status_payload,
        estimated_fuel_cost=shift.gas_cost,
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


@router.post("/shifts/{shift_id}/trips", response_model=ShiftRead)
def complete_trip(shift_id: int, payload: TripComplete, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ShiftRead:
    shift = shift_or_404(db, current_user.id, shift_id)
    if shift.ended_at is not None:
        raise HTTPException(status_code=409, detail="Cannot add trips to an ended shift")
    if shift.break_required:
        raise HTTPException(status_code=409, detail="Break required before adding more completed trips")
    now = now_utc()
    last_trip_at = as_utc(shift.last_trip_at)
    if not payload.multi_order and last_trip_at is not None:
        seconds_since_last = (now - last_trip_at).total_seconds()
        if seconds_since_last < TRIP_COOLDOWN_SECONDS:
            remaining = int((TRIP_COOLDOWN_SECONDS - seconds_since_last + 59) // 60)
            raise HTTPException(status_code=429, detail=f"Trip cooldown active. Wait about {remaining} minute(s), or use multi-order if you completed multiple orders in one trip.")
    shift.trips += payload.count
    shift.trips_since_break += payload.count
    shift.last_trip_at = now
    if shift.trips_since_break >= TRIPS_BEFORE_MANDATED_BREAK:
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
    minutes = total_minutes(shift.started_at, shift.ended_at, now_utc())
    if payload.break_type != "emergency" and minutes < 80 and not shift.break_required:
        raise HTTPException(status_code=409, detail="Breaks unlock after 80 minutes online or once 5 completed orders require a break")
    active_break = db.scalar(select(Break).where(Break.shift_id == shift_id, Break.ended_at.is_(None)))
    if active_break:
        raise HTTPException(status_code=409, detail="This shift already has an active break")
    if payload.target_latitude is not None and payload.target_longitude is not None:
        if payload.latitude is None or payload.longitude is None:
            raise HTTPException(status_code=400, detail="Current location is required to confirm a break zone")
        distance = miles_between(
            float(payload.latitude),
            float(payload.longitude),
            float(payload.target_latitude),
            float(payload.target_longitude),
        )
        if distance > 0.2:
            raise HTTPException(status_code=409, detail="Arrive within 0.2 miles of the selected break zone to start the timer")
    break_item = Break(
        shift_id=shift_id,
        started_at=now_utc() if payload.target_latitude is not None else payload.started_at or now_utc(),
        break_type=payload.break_type,
        notes=payload.notes,
        location_name=payload.location_name,
        latitude=payload.latitude or payload.target_latitude,
        longitude=payload.longitude or payload.target_longitude,
        confirmed_at=now_utc() if payload.target_latitude is not None else None,
    )
    db.add(break_item)
    shift.break_required = False
    shift.trips_since_break = 0
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
    break_item.ended_at = payload.ended_at or now_utc()
    if payload.notes is not None:
        break_item.notes = payload.notes
    db.commit()
    db.refresh(break_item)
    return break_item
