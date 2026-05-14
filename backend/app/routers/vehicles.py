from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserVehicle, VehicleCatalog
from app.schemas import UserVehicleCreate, UserVehicleRead, VehicleCatalogRead
from app.security import get_current_user
from app.vehicle_seed import catalog_rows

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def ensure_catalog(db: Session) -> None:
    if db.scalar(select(VehicleCatalog.id).limit(1)):
        return
    db.add_all([VehicleCatalog(**row) for row in catalog_rows()])
    db.commit()


@router.get("/catalog", response_model=list[VehicleCatalogRead])
def vehicle_catalog(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[VehicleCatalog]:
    ensure_catalog(db)
    return list(db.scalars(select(VehicleCatalog).order_by(VehicleCatalog.make, VehicleCatalog.model, VehicleCatalog.year)))


@router.get("", response_model=list[UserVehicleRead])
def list_user_vehicles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[UserVehicle]:
    return list(db.scalars(select(UserVehicle).where(UserVehicle.user_id == current_user.id).order_by(UserVehicle.is_active.desc(), UserVehicle.created_at.desc())))


@router.get("/active", response_model=UserVehicleRead | None)
def active_vehicle(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> UserVehicle | None:
    return db.scalar(select(UserVehicle).where(UserVehicle.user_id == current_user.id, UserVehicle.is_active.is_(True)))


@router.post("", response_model=UserVehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: UserVehicleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> UserVehicle:
    ensure_catalog(db)
    catalog = db.get(VehicleCatalog, payload.catalog_id) if payload.catalog_id else None
    if payload.catalog_id and catalog is None:
        raise HTTPException(status_code=404, detail="Vehicle catalog entry not found")
    if catalog:
        data = {
            "catalog_id": catalog.id,
            "year": catalog.year,
            "make": catalog.make,
            "model": catalog.model,
            "mpg_city": catalog.mpg_city,
            "mpg_highway": catalog.mpg_highway,
            "mpg_combined": catalog.mpg_combined,
            "fuel_type": catalog.fuel_type,
        }
    else:
        required = [payload.year, payload.make, payload.model, payload.mpg_city, payload.mpg_highway, payload.mpg_combined]
        if any(value is None for value in required):
            raise HTTPException(status_code=422, detail="Custom vehicles require year, make, model, and MPG values")
        data = {
            "year": payload.year,
            "make": payload.make,
            "model": payload.model,
            "mpg_city": payload.mpg_city,
            "mpg_highway": payload.mpg_highway,
            "mpg_combined": payload.mpg_combined,
            "fuel_type": payload.fuel_type,
        }
    if payload.is_active:
        db.query(UserVehicle).filter(UserVehicle.user_id == current_user.id).update({"is_active": False})
    vehicle = UserVehicle(
        user_id=current_user.id,
        nickname=payload.nickname,
        fuel_price_per_gallon=payload.fuel_price_per_gallon or Decimal("3.50"),
        is_active=payload.is_active,
        **data,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.patch("/{vehicle_id}/active", response_model=UserVehicleRead)
def set_active_vehicle(vehicle_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> UserVehicle:
    vehicle = db.scalar(select(UserVehicle).where(and_(UserVehicle.id == vehicle_id, UserVehicle.user_id == current_user.id)))
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    db.query(UserVehicle).filter(UserVehicle.user_id == current_user.id).update({"is_active": False})
    vehicle.is_active = True
    db.commit()
    db.refresh(vehicle)
    return vehicle

