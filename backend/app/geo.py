from math import asin, cos, radians, sin, sqrt


def miles_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 3958.8
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * radius * asin(sqrt(a))

