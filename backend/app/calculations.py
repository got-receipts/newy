from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

TAX_RATE = Decimal("0.20")
MAINTENANCE_PER_MILE = Decimal("0.15")
BREAK_INTERVAL_MINUTES = 80


def money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def total_minutes(started_at: datetime, ended_at: datetime | None, now: datetime | None = None) -> int:
    end = ended_at or now
    if end is None:
        return 0
    return max(int((end - started_at).total_seconds() // 60), 0)


def metrics(
    *,
    started_at: datetime,
    ended_at: datetime | None,
    gross_earnings: Decimal,
    miles: Decimal,
    gas_cost: Decimal,
    other_expenses: Decimal,
    now: datetime | None = None,
) -> dict[str, Decimal | int]:
    minutes = total_minutes(started_at, ended_at, now)
    hours = Decimal(minutes) / Decimal(60) if minutes else Decimal("0")
    tax_set_aside = money(gross_earnings * TAX_RATE)
    maintenance_reserve = money(miles * MAINTENANCE_PER_MILE)
    net_profit = money(gross_earnings - gas_cost - other_expenses - tax_set_aside - maintenance_reserve)
    gross_hourly = money(gross_earnings / hours) if hours else Decimal("0.00")
    net_hourly = money(net_profit / hours) if hours else Decimal("0.00")
    earnings_per_mile = money(gross_earnings / miles) if miles else Decimal("0.00")

    return {
        "total_minutes": minutes,
        "gross_hourly": gross_hourly,
        "net_hourly": net_hourly,
        "earnings_per_mile": earnings_per_mile,
        "tax_set_aside": tax_set_aside,
        "maintenance_reserve": maintenance_reserve,
        "net_profit": net_profit,
    }


def break_status(minutes: int) -> dict[str, str | int]:
    if minutes >= 8 * 60:
        return {"level": "warning", "message": "Fatigue warning: consider ending your shift or taking a recovery break.", "suggested_minutes": 30}
    if minutes >= BREAK_INTERVAL_MINUTES:
        intervals = minutes // BREAK_INTERVAL_MINUTES
        next_due = (intervals + 1) * BREAK_INTERVAL_MINUTES
        return {
            "level": "due",
            "message": "Break companion: take a break now and confirm arrival at a nearby safe break location.",
            "suggested_minutes": 15,
            "next_due_minutes": next_due,
        }
    return {"level": "ok", "message": f"Next break check at {BREAK_INTERVAL_MINUTES} minutes online.", "suggested_minutes": 0, "next_due_minutes": BREAK_INTERVAL_MINUTES}
