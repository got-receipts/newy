from collections import defaultdict

import httpx
from fastapi import APIRouter, Depends, Query

from app.geo import miles_between
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


async def overpass(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        return response.json().get("elements", [])


@router.get("/break-zones")
async def break_zones(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    radius_meters: int = Query(default=5000, ge=500, le=12000),
    current_user: User = Depends(get_current_user),
) -> dict:
    query = f"""
    [out:json][timeout:10];
    (
      node["amenity"="fuel"]["opening_hours"~"24/7"](around:{radius_meters},{lat},{lon});
      way["amenity"="fuel"]["opening_hours"~"24/7"](around:{radius_meters},{lat},{lon});
      node["shop"="convenience"]["opening_hours"~"24/7"](around:{radius_meters},{lat},{lon});
      node["amenity"~"cafe|fast_food|restaurant"](around:{int(radius_meters / 2)},{lat},{lon});
    );
    out center tags 30;
    """
    try:
        elements = await overpass(query)
    except Exception:
        elements = []

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
                "open_24_7": tags.get("opening_hours") == "24/7",
                "opening_hours": tags.get("opening_hours"),
            }
        )
    zones.sort(key=lambda item: (not item["open_24_7"], item["distance_miles"]))
    return {"source": "OpenStreetMap Overpass public POI data", "zones": zones[:12]}


@router.get("/activity")
async def activity_hotspots(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    radius_meters: int = Query(default=4500, ge=500, le=12000),
    current_user: User = Depends(get_current_user),
) -> dict:
    query = f"""
    [out:json][timeout:10];
    (
      node["amenity"~"restaurant|fast_food|cafe|food_court"](around:{radius_meters},{lat},{lon});
      node["shop"~"convenience|supermarket|mall"](around:{radius_meters},{lat},{lon});
      way["amenity"~"restaurant|fast_food|cafe|food_court"](around:{radius_meters},{lat},{lon});
      way["shop"~"convenience|supermarket|mall"](around:{radius_meters},{lat},{lon});
    );
    out center tags 100;
    """
    try:
        elements = await overpass(query)
    except Exception:
        elements = []

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
    return {
        "source": "OpenStreetMap POI density proxy, not gig-platform order data",
        "hotspots": hotspots[:12],
    }

