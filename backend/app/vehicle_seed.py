from datetime import date
from decimal import Decimal

CATALOG_START_YEAR = 2008
CATALOG_END_YEAR = date.today().year

# City/highway/combined values are practical defaults for in-app fuel planning.
# Drivers can override MPG on their personal vehicle profile when they know the exact trim.
COMMON_VEHICLE_SPECS = [
    ("Toyota", "Prius", 2008, None, "57.0", "56.0", "57.0", "hybrid"),
    ("Toyota", "Corolla", 2008, None, "32.0", "41.0", "35.0", "gasoline"),
    ("Toyota", "Corolla Hybrid", 2020, None, "53.0", "46.0", "50.0", "hybrid"),
    ("Toyota", "Camry", 2008, None, "28.0", "39.0", "32.0", "gasoline"),
    ("Toyota", "Camry Hybrid", 2008, None, "51.0", "53.0", "52.0", "hybrid"),
    ("Toyota", "RAV4", 2008, None, "27.0", "35.0", "30.0", "gasoline"),
    ("Toyota", "RAV4 Hybrid", 2016, None, "41.0", "38.0", "40.0", "hybrid"),
    ("Toyota", "Corolla Cross Hybrid", 2023, None, "45.0", "38.0", "42.0", "hybrid"),
    ("Toyota", "Sienna Hybrid", 2021, None, "36.0", "36.0", "36.0", "hybrid"),
    ("Honda", "Civic", 2008, None, "32.0", "41.0", "36.0", "gasoline"),
    ("Honda", "Accord", 2008, None, "29.0", "37.0", "32.0", "gasoline"),
    ("Honda", "Accord Hybrid", 2014, None, "51.0", "44.0", "48.0", "hybrid"),
    ("Honda", "Fit", 2008, 2020, "29.0", "36.0", "32.0", "gasoline"),
    ("Honda", "HR-V", 2016, None, "26.0", "32.0", "28.0", "gasoline"),
    ("Honda", "CR-V", 2008, None, "28.0", "34.0", "30.0", "gasoline"),
    ("Honda", "CR-V Hybrid", 2020, None, "43.0", "36.0", "40.0", "hybrid"),
    ("Hyundai", "Elantra", 2008, None, "32.0", "41.0", "36.0", "gasoline"),
    ("Hyundai", "Elantra Hybrid", 2021, None, "53.0", "56.0", "54.0", "hybrid"),
    ("Hyundai", "Sonata", 2008, None, "28.0", "38.0", "32.0", "gasoline"),
    ("Hyundai", "Sonata Hybrid", 2011, None, "44.0", "51.0", "47.0", "hybrid"),
    ("Hyundai", "Kona", 2018, None, "29.0", "34.0", "31.0", "gasoline"),
    ("Hyundai", "Ioniq Hybrid", 2017, 2022, "57.0", "59.0", "58.0", "hybrid"),
    ("Hyundai", "Ioniq 5", 2022, None, "132.0", "98.0", "114.0", "electric-mpge"),
    ("Kia", "Forte", 2010, None, "30.0", "41.0", "34.0", "gasoline"),
    ("Kia", "Optima", 2008, 2020, "27.0", "37.0", "31.0", "gasoline"),
    ("Kia", "K5", 2021, None, "27.0", "37.0", "31.0", "gasoline"),
    ("Kia", "Niro Hybrid", 2017, None, "53.0", "54.0", "53.0", "hybrid"),
    ("Kia", "Soul", 2010, None, "29.0", "35.0", "31.0", "gasoline"),
    ("Kia", "EV6", 2022, None, "136.0", "100.0", "117.0", "electric-mpge"),
    ("Nissan", "Sentra", 2008, None, "30.0", "40.0", "34.0", "gasoline"),
    ("Nissan", "Versa", 2008, None, "32.0", "40.0", "35.0", "gasoline"),
    ("Nissan", "Altima", 2008, None, "27.0", "39.0", "32.0", "gasoline"),
    ("Nissan", "Rogue", 2008, None, "30.0", "37.0", "33.0", "gasoline"),
    ("Subaru", "Impreza", 2008, None, "27.0", "34.0", "30.0", "gasoline"),
    ("Subaru", "Crosstrek", 2013, None, "27.0", "34.0", "29.0", "gasoline"),
    ("Subaru", "Forester", 2008, None, "26.0", "33.0", "29.0", "gasoline"),
    ("Chevrolet", "Malibu", 2008, 2025, "28.0", "36.0", "31.0", "gasoline"),
    ("Chevrolet", "Cruze", 2011, 2019, "29.0", "40.0", "33.0", "gasoline"),
    ("Chevrolet", "Trax", 2015, None, "28.0", "32.0", "30.0", "gasoline"),
    ("Chevrolet", "Bolt EV", 2017, 2023, "131.0", "109.0", "120.0", "electric-mpge"),
    ("Ford", "Focus", 2008, 2018, "26.0", "38.0", "31.0", "gasoline"),
    ("Ford", "Fusion", 2008, 2020, "23.0", "34.0", "27.0", "gasoline"),
    ("Ford", "Fusion Hybrid", 2010, 2020, "43.0", "41.0", "42.0", "hybrid"),
    ("Ford", "Escape", 2008, None, "27.0", "34.0", "30.0", "gasoline"),
    ("Ford", "Escape Hybrid", 2008, None, "42.0", "36.0", "39.0", "hybrid"),
    ("Ford", "Maverick Hybrid", 2022, None, "42.0", "33.0", "37.0", "hybrid"),
    ("Mazda", "Mazda3", 2008, None, "27.0", "37.0", "31.0", "gasoline"),
    ("Mazda", "CX-5", 2013, None, "26.0", "31.0", "28.0", "gasoline"),
    ("Volkswagen", "Jetta", 2008, None, "30.0", "41.0", "34.0", "gasoline"),
    ("Volkswagen", "Golf", 2008, 2021, "29.0", "37.0", "32.0", "gasoline"),
    ("Mitsubishi", "Mirage", 2014, None, "36.0", "43.0", "39.0", "gasoline"),
    ("Lexus", "CT Hybrid", 2011, 2017, "43.0", "40.0", "42.0", "hybrid"),
    ("Lexus", "UX Hybrid", 2019, None, "43.0", "41.0", "42.0", "hybrid"),
    ("Tesla", "Model 3", 2017, None, "132.0", "126.0", "129.0", "electric-mpge"),
    ("Tesla", "Model Y", 2020, None, "129.0", "116.0", "123.0", "electric-mpge"),
]


def _adjust_mpg(value: str, year: int, fuel_type: str) -> Decimal:
    mpg = Decimal(value)
    if fuel_type == "electric-mpge":
        return mpg
    years_old = max(CATALOG_END_YEAR - year, 0)
    adjustment = Decimal(min(years_old, 12)) * Decimal("0.35")
    return max(Decimal("10.0"), mpg - adjustment).quantize(Decimal("0.1"))


def catalog_rows() -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[int, str, str]] = set()
    for make, model, start_year, end_year, city, highway, combined, fuel_type in COMMON_VEHICLE_SPECS:
        first_year = max(CATALOG_START_YEAR, start_year)
        last_year = min(CATALOG_END_YEAR, end_year or CATALOG_END_YEAR)
        for year in range(first_year, last_year + 1):
            key = (year, make, model)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "year": year,
                    "make": make,
                    "model": model,
                    "mpg_city": _adjust_mpg(city, year, fuel_type),
                    "mpg_highway": _adjust_mpg(highway, year, fuel_type),
                    "mpg_combined": _adjust_mpg(combined, year, fuel_type),
                    "fuel_type": fuel_type,
                }
            )
    return sorted(rows, key=lambda row: (row["make"], row["model"], row["year"]))


def catalog_key(row: dict) -> tuple[int, str, str]:
    return (int(row["year"]), str(row["make"]), str(row["model"]))
