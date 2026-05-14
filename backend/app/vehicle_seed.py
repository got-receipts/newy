from decimal import Decimal

COMMON_VEHICLES = [
    (2024, "Toyota", "Prius", "57.0", "56.0", "57.0", "hybrid"),
    (2024, "Toyota", "Corolla Hybrid", "53.0", "46.0", "50.0", "hybrid"),
    (2024, "Toyota", "Camry", "28.0", "39.0", "32.0", "gasoline"),
    (2024, "Honda", "Civic", "32.0", "41.0", "36.0", "gasoline"),
    (2024, "Honda", "Accord Hybrid", "51.0", "44.0", "48.0", "hybrid"),
    (2024, "Hyundai", "Elantra", "32.0", "41.0", "36.0", "gasoline"),
    (2024, "Hyundai", "Sonata Hybrid", "44.0", "51.0", "47.0", "hybrid"),
    (2024, "Kia", "Niro Hybrid", "53.0", "54.0", "53.0", "hybrid"),
    (2024, "Nissan", "Sentra", "30.0", "40.0", "34.0", "gasoline"),
    (2024, "Subaru", "Impreza", "27.0", "34.0", "30.0", "gasoline"),
    (2024, "Chevrolet", "Malibu", "28.0", "36.0", "31.0", "gasoline"),
    (2024, "Ford", "Maverick Hybrid", "42.0", "33.0", "37.0", "hybrid"),
    (2024, "Mazda", "Mazda3", "27.0", "37.0", "31.0", "gasoline"),
    (2024, "Volkswagen", "Jetta", "30.0", "41.0", "34.0", "gasoline"),
    (2024, "Mitsubishi", "Mirage", "36.0", "43.0", "39.0", "gasoline"),
    (2024, "Nissan", "Versa", "32.0", "40.0", "35.0", "gasoline"),
    (2024, "Kia", "Forte", "30.0", "41.0", "34.0", "gasoline"),
    (2024, "Hyundai", "Kona", "29.0", "34.0", "31.0", "gasoline"),
    (2024, "Toyota", "Corolla Cross Hybrid", "45.0", "38.0", "42.0", "hybrid"),
    (2024, "Toyota", "Sienna Hybrid", "36.0", "36.0", "36.0", "hybrid"),
    (2024, "Honda", "HR-V", "26.0", "32.0", "28.0", "gasoline"),
    (2024, "Subaru", "Crosstrek", "27.0", "34.0", "29.0", "gasoline"),
    (2024, "Ford", "Escape Hybrid", "42.0", "36.0", "39.0", "hybrid"),
    (2024, "Lexus", "UX Hybrid", "43.0", "41.0", "42.0", "hybrid"),
    (2024, "Chevrolet", "Bolt EV", "131.0", "109.0", "120.0", "electric-mpge"),
    (2024, "Hyundai", "Ioniq 5", "132.0", "98.0", "114.0", "electric-mpge"),
    (2024, "Kia", "EV6", "136.0", "100.0", "117.0", "electric-mpge"),
    (2023, "Toyota", "RAV4 Hybrid", "41.0", "38.0", "40.0", "hybrid"),
    (2023, "Honda", "CR-V Hybrid", "43.0", "36.0", "40.0", "hybrid"),
    (2023, "Tesla", "Model 3", "132.0", "126.0", "129.0", "electric-mpge"),
]


def catalog_rows() -> list[dict]:
    return [
        {
            "year": year,
            "make": make,
            "model": model,
            "mpg_city": Decimal(city),
            "mpg_highway": Decimal(highway),
            "mpg_combined": Decimal(combined),
            "fuel_type": fuel_type,
        }
        for year, make, model, city, highway, combined, fuel_type in COMMON_VEHICLES
    ]
