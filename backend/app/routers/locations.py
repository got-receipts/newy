from collections import defaultdict

import httpx
from fastapi import APIRouter, Depends, Query

from app.geo import miles_between
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
METERS_PER_MILE = 1609.344
GENERAL_BREAK_RADIUS_METERS = int(20 * METERS_PER_MILE)
MANDATED_BREAK_RADII_METERS = [int(3 * METERS_PER_MILE), int(8 * METERS_PER_MILE)]
SEARCH_RADII_METERS = [5000, 12000, 25000, GENERAL_BREAK_RADIUS_METERS]


async def overpass(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        return response.json().get("elements", [])


def fallback_zone(lat: float, lon: float) -> dict:
    return {
        "name": "Closest 24-hour fuel stop search area",
        "kind": "estimated",
        "latitude": lat,
        "longitude": lon,
        "distance_miles": 0.0,
        "open_24_7": False,
        "opening_hours": "Unknown",
        "note": "Live public 24-hour fuel data was unavailable here; use this as a search anchor and refresh near a commercial road.",
    }


def fallback_hotspots(lat: float, lon: float) -> list[dict]:
    offsets = [
        ("Nearby restaurant cluster search", 0.01, 0.0, 3),
        ("Nearby retail corridor search", 0.0, 0.012, 2),
        ("Nearby convenience/gas search", -0.01, -0.01, 2),
    ]
    return [
        {
            "latitude": round(lat + lat_offset, 5),
            "longitude": round(lon + lon_offset, 5),
            "score": score,
            "distance_miles": round(miles_between(lat, lon, lat + lat_offset, lon + lon_offset), 2),
            "label": label,
            "estimated": True,
        }
        for label, lat_offset, lon_offset, score in offsets
    ]


@router.get("/break-zones")
async def break_zones(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    radius_meters: int = Query(default=GENERAL_BREAK_RADIUS_METERS, ge=500, le=50000),
    mandated: bool = False,
    include_fallback: bool = True,
    current_user: User = Depends(get_current_user),
) -> dict:
    elements = []
    search_radius = radius_meters
    radii = MANDATED_BREAK_RADII_METERS if mandated else sorted({radius_meters, *SEARCH_RADII_METERS})
    for search_radius in radii:
        query = f"""
        [out:json][timeout:10];
        (
          node["amenity"="fuel"](around:{search_radius},{lat},{lon});
          way["amenity"="fuel"](around:{search_radius},{lat},{lon});
        );
        out center tags 80;
        """
        try:
            elements = await overpass(query)
        except Exception:
            elements = []
        if elements:
            break

    zones = []
    for item in elements:
        tags = item.get("tags", {})
        item_lat = item.get("lat") or item.get("center", {}).get("lat")
        item_lon = item.get("lon") or item.get("center", {}).get("lon")
        if item_lat is None or item_lon is None:
            continue
        distance = miles_between(lat, lon, float(item_lat), float(item_lon))
        zones.append(
            {
                "name": tags.get("name") or tags.get("brand") or "Break location",
                "kind": tags.get("amenity") or tags.get("shop") or "poi",
                "latitude": float(item_lat),
                "longitude": float(item_lon),
                "distance_miles": round(distance, 2),
                "open_24_7": "24/7" in (tags.get("opening_hours") or ""),
                "opening_hours": tags.get("opening_hours"),
            }
        )
    zones.sort(key=lambda item: (not item["open_24_7"], item["distance_miles"]))
    if not zones and not mandated:
        query = f"""
        [out:json][timeout:10];
        (
          node["shop"="convenience"]["opening_hours"~"24/7"](around:{radius_meters},{lat},{lon});
          way["shop"="convenience"]["opening_hours"~"24/7"](around:{radius_meters},{lat},{lon});
        );
        out center tags 60;
        """
        try:
            elements = await overpass(query)
        except Exception:
            elements = []
        for item in elements:
            tags = item.get("tags", {})
            item_lat = item.get("lat") or item.get("center", {}).get("lat")
            item_lon = item.get("lon") or item.get("center", {}).get("lon")
            if item_lat is None or item_lon is None:
                continue
            zones.append(
                {
                    "name": tags.get("name") or tags.get("brand") or "24-hour convenience stop",
                    "kind": tags.get("shop") or "convenience",
                    "latitude": float(item_lat),
                    "longitude": float(item_lon),
                    "distance_miles": round(miles_between(lat, lon, float(item_lat), float(item_lon)), 2),
                    "open_24_7": "24/7" in (tags.get("opening_hours") or ""),
                    "opening_hours": tags.get("opening_hours"),
                }
            )
        zones.sort(key=lambda item: item["distance_miles"])
    if not zones and include_fallback:
        zones = [fallback_zone(lat, lon)]
    return {"source": "OpenStreetMap Overpass public POI data", "radius_meters": search_radius, "zones": zones[:12]}


@router.get("/activity")
async def activity_hotspots(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    radius_meters: int = Query(default=4500, ge=500, le=12000),
    current_user: User = Depends(get_current_user),
) -> dict:
    elements = []
    search_radius = radius_meters
    for search_radius in sorted({radius_meters, *SEARCH_RADII_METERS}):
        query = f"""
        [out:json][timeout:10];
        (
          node["amenity"~"restaurant|fast_food|cafe|food_court"](around:{search_radius},{lat},{lon});
          node["shop"~"convenience|supermarket|mall"](around:{search_radius},{lat},{lon});
          way["amenity"~"restaurant|fast_food|cafe|food_court"](around:{search_radius},{lat},{lon});
          way["shop"~"convenience|supermarket|mall"](around:{search_radius},{lat},{lon});
        );
        out center tags 150;
        """
        try:
            elements = await overpass(query)
        except Exception:
            elements = []
        if elements:
            break

    buckets: dict[tuple[float, float], dict] = defaultdict(lambda: {"score": 0, "sample_names": []})
    for item in elements:
        tags = item.get("tags", {})
        item_lat = item.get("lat") or item.get("center", {}).get("lat")
        item_lon = item.get("lon") or item.get("center", {}).get("lon")
        if item_lat is None or item_lon is None:
            continue
        key = (round(float(item_lat), 3), round(float(item_lon), 3))
        weight = 3 if tags.get("amenity") in {"restaurant", "fast_food"} else 2
        buckets[key]["score"] += weight
        if len(buckets[key]["sample_names"]) < 3:
            buckets[key]["sample_names"].append(tags.get("name") or tags.get("brand") or "POI")

    hotspots = []
    for (bucket_lat, bucket_lon), data in buckets.items():
        hotspots.append(
            {
                "latitude": bucket_lat,
                "longitude": bucket_lon,
                "score": data["score"],
                "distance_miles": round(miles_between(lat, lon, bucket_lat, bucket_lon), 2),
                "label": ", ".join(data["sample_names"]),
            }
        )
    hotspots.sort(key=lambda item: (-item["score"], item["distance_miles"]))
    if not hotspots:
        hotspots = fallback_hotspots(lat, lon)
    return {
        "source": "OpenStreetMap POI density proxy, not gig-platform order data",
        "radius_meters": search_radius,
        "hotspots": hotspots[:12],
    }
