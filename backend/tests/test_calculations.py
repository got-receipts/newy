from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.calculations import break_status, metrics


def test_shift_metrics() -> None:
    started = datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc)
    ended = started + timedelta(hours=5)

    result = metrics(
        started_at=started,
        ended_at=ended,
        gross_earnings=Decimal("150.00"),
        miles=Decimal("60"),
        gas_cost=Decimal("18.00"),
        other_expenses=Decimal("7.00"),
    )

    assert result["total_minutes"] == 300
    assert result["gross_hourly"] == Decimal("30.00")
    assert result["tax_set_aside"] == Decimal("30.00")
    assert result["maintenance_reserve"] == Decimal("9.00")
    assert result["net_profit"] == Decimal("86.00")
    assert result["net_hourly"] == Decimal("17.20")
    assert result["earnings_per_mile"] == Decimal("2.50")


def test_break_status_thresholds() -> None:
    assert break_status(79)["level"] == "ok"
    assert break_status(80)["suggested_minutes"] == 15
    assert break_status(160)["level"] == "due"
    assert break_status(480)["level"] == "warning"
