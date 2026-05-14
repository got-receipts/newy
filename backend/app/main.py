from pathlib import Path

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal
from app.models import VehicleCatalog
from app.models import User
from app.routers import auth, locations, reports, shifts, vehicles
from app.schemas import UserRead
from app.security import get_current_user
from app.vehicle_seed import catalog_rows

DISCLAIMER = (
    "GigOS is an independent shift, mileage, break, and earnings tracker for gig workers. "
    "Not affiliated with Uber, DoorDash, Grubhub, Instacart, Amazon Flex, or any delivery platform."
)

app = FastAPI(
    title="GigOS API",
    version="0.1.0",
    description=DISCLAIMER,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(shifts.router)
app.include_router(reports.router)
app.include_router(locations.router)
app.include_router(vehicles.router)


@app.on_event("startup")
def startup_seed() -> None:
    db = SessionLocal()
    try:
        if not db.query(VehicleCatalog.id).first():
            db.add_all([VehicleCatalog(**row) for row in catalog_rows()])
            db.commit()
        if settings.seed_demo_accounts:
            from app.demo_seed import seed_demo_data

            seed_demo_data(db)
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/disclaimer")
def disclaimer() -> dict[str, str]:
    return {"disclaimer": DISCLAIMER}


@app.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        requested = static_dir / path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(static_dir / "index.html")
