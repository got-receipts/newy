import csv
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.calculations import money, metrics, total_minutes
from app.database import get_db
from app.models import Shift, User
from app.schemas import WeeklyReport
from app.security import get_current_user

router = APIRouter(tags=["reports"])


def current_week() -> tuple[datetime, datetime]:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=today.weekday())
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return start, end


def weekly_shifts(db: Session, user_id: int, start: datetime, end: datetime) -> list[Shift]:
    return list(
        db.scalars(
            select(Shift).where(
                Shift.user_id == user_id,
                Shift.started_at >= start,
                Shift.started_at < end,
            ).options(selectinload(Shift.vehicle))
        )
    )


@router.get("/reports/weekly", response_model=WeeklyReport)
def weekly_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> WeeklyReport:
    start, end = current_week()
    shifts = weekly_shifts(db, current_user.id, start, end)
    online_minutes = sum(total_minutes(shift.started_at, shift.ended_at, datetime.now(timezone.utc)) for shift in shifts)
    gross = sum((shift.gross_earnings for shift in shifts), Decimal("0.00"))
    miles = sum((shift.miles for shift in shifts), Decimal("0.00"))
    gas = sum((shift.gas_cost for shift in shifts), Decimal("0.00"))
    gas_used = sum(((shift.miles / shift.vehicle.mpg_combined) for shift in shifts if shift.vehicle and shift.vehicle.mpg_combined and shift.miles), Decimal("0.00"))
    other = sum((shift.other_expenses for shift in shifts), Decimal("0.00"))
    aggregate = metrics(
        started_at=start,
        ended_at=start + timedelta(minutes=online_minutes),
        gross_earnings=gross,
        miles=miles,
        gas_cost=gas,
        other_expenses=other,
    )
    return WeeklyReport(
        week_start=start,
        week_end=end,
        shifts=len(shifts),
        online_minutes=online_minutes,
        active_minutes=sum(shift.active_minutes for shift in shifts),
        daily_minutes=sum(shift.daily_minutes for shift in shifts),
        gross_earnings=money(gross),
        tips=money(sum((shift.tips for shift in shifts), Decimal("0.00"))),
        trips=sum(shift.trips for shift in shifts),
        miles=money(miles),
        gas_cost=money(gas),
        gas_used_gallons=money(gas_used),
        other_expenses=money(other),
        gross_hourly=aggregate["gross_hourly"],
        net_hourly=aggregate["net_hourly"],
        earnings_per_mile=aggregate["earnings_per_mile"],
        tax_set_aside=aggregate["tax_set_aside"],
        maintenance_reserve=aggregate["maintenance_reserve"],
        net_profit=aggregate["net_profit"],
    )


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> StreamingResponse:
    shifts = list(db.scalars(select(Shift).options(selectinload(Shift.vehicle)).where(Shift.user_id == current_user.id).order_by(Shift.started_at.desc())))
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "started_at",
            "ended_at",
            "platform",
            "online_minutes",
            "active_minutes",
            "daily_minutes",
            "gross_earnings",
            "tips",
            "trips",
            "miles",
            "gas_cost",
            "gas_used_gallons",
            "other_expenses",
            "tax_set_aside",
            "maintenance_reserve",
            "net_profit",
            "gross_hourly",
            "net_hourly",
            "earnings_per_mile",
            "notes",
        ]
    )
    for shift in shifts:
        calc = metrics(
            started_at=shift.started_at,
            ended_at=shift.ended_at,
            gross_earnings=shift.gross_earnings,
            miles=shift.miles,
            gas_cost=shift.gas_cost,
            other_expenses=shift.other_expenses,
            now=datetime.now(timezone.utc),
        )
        writer.writerow(
            [
                shift.id,
                shift.started_at.isoformat(),
                shift.ended_at.isoformat() if shift.ended_at else "",
                shift.platform,
                calc["total_minutes"],
                shift.active_minutes,
                shift.daily_minutes,
                shift.gross_earnings,
                shift.tips,
                shift.trips,
                shift.miles,
                shift.gas_cost,
                money((shift.miles / shift.vehicle.mpg_combined) if shift.vehicle and shift.vehicle.mpg_combined and shift.miles else Decimal("0.00")),
                shift.other_expenses,
                calc["tax_set_aside"],
                calc["maintenance_reserve"],
                calc["net_profit"],
                calc["gross_hourly"],
                calc["net_hourly"],
                calc["earnings_per_mile"],
                shift.notes or "",
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gigos-shifts.csv"},
    )
