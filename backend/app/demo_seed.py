from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserVehicle, VehicleCatalog
from app.security import hash_password
from app.vehicle_seed import catalog_rows

TEST_ACCOUNTS = [
    ("driver@gigos.example.com", "GigOSdemo123!", "Demo Prius", "Toyota", "Prius"),
    ("flex@gigos.example.com", "GigOSdemo123!", "Flex Maverick", "Ford", "Maverick Hybrid"),
]


def seed_demo_data(db: Session) -> None:
    if not db.scalar(select(VehicleCatalog.id).limit(1)):
        db.add_all([VehicleCatalog(**row) for row in catalog_rows()])
        db.commit()

    for email, password, nickname, make, model in TEST_ACCOUNTS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, hashed_password=hash_password(password))
            db.add(user)
            db.commit()
            db.refresh(user)

        if db.scalar(select(UserVehicle.id).where(UserVehicle.user_id == user.id)):
            continue
        catalog = db.scalar(select(VehicleCatalog).where(VehicleCatalog.make == make, VehicleCatalog.model == model))
        if catalog is None:
            catalog = db.scalar(select(VehicleCatalog).limit(1))
        if catalog is None:
            continue
        db.add(
            UserVehicle(
                user_id=user.id,
                catalog_id=catalog.id,
                nickname=nickname,
                year=catalog.year,
                make=catalog.make,
                model=catalog.model,
                mpg_city=catalog.mpg_city,
                mpg_highway=catalog.mpg_highway,
                mpg_combined=catalog.mpg_combined,
                fuel_type=catalog.fuel_type,
                fuel_price_per_gallon=Decimal("3.50"),
                is_active=True,
            )
        )
        db.commit()
